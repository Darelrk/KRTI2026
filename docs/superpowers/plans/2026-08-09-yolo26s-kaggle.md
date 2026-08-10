# YOLO26s Fine-Tune (Kaggle) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fine-tune YOLO26s pada dataset `aerial human detection v4` (3.479 gambar, kelas `person`, view UAV) di Kaggle GPU T4, dan menghasilkan `best.pt` + `best.onnx` + `best.engine` siap pakai di Jetson/laptop untuk deadline Selasa.

**Architecture:** Notebook Kaggle satu-pass: download dataset via Roboflow API (atau upload zip manual) → train YOLO26s (MuSGD otomatis, 100 epochs, early stop) → validasi → export ONNX + TensorRT fp16.

**Tech Stack:** Kaggle (2×T4 16 GB, ~30 jam/minggu), ultralytics (YOLO26s), roboflow SDK, inference-sdk (untuk cek model hosted sebagai pembanding).

**Konteks keputusan:**
- Dataset sudah di-resize 640×640 → `imgsz=640` (upscaling tidak menambah info).
- Format download Roboflow dipakai `yolov11` (TXT+YAML) — struktur identik dengan format yolo26, dan nama format-nya dijamin didukung SDK roboflow. YOLO26 membaca data.yaml yang sama.
- YOLO26 di ultralytics versi terbaru otomatis memakai optimizer MuSGD.
- Val set resmi cuma 53 gambar → metrik ber-noise; bandingkan juga dengan model hosted (opsional, butuh key).

---

## File Structure

- Buat: `kaggle/yolo26s_train.ipynb` — notebook lengkap, deliverable utama (isi sel-sel di bawah).
- Buat: `model/` — output `best.pt` akan ditaruh di sini setelah download dari Kaggle.
- Tidak ada file lain yang perlu dibuat.

## Task 0: Persiapan Kaggle (dilakukan manual, sekali)

- [ ] Login https://www.kaggle.com → Create → New Notebook.
- [ ] Settings → Accelerator = **GPU T4x2** (ada di kuota harian 30 jam, gratis).
- [ ] Settings → Add-ons → masukkan **ROBOFLOW_API_KEY** via *Secrets* (tombol `+ Add` di bagian "Secrets"):
  1. Buka https://app.roboflow.com → Settings → API Keys → copy key (format `xxxxxxxxxxxx`).
  2. Kaggle: `Add-ons` → `Secrets` → `+ Add New Secret` → nama `ROBOFLOW_API_KEY`, value = key.
- [ ] **Alternatif tanpa key** (kalau tidak mau simpan key di Kaggle): download zip dataset manual di https://universe.roboflow.com/mukuntha-rgwdi/aerial-human-detection-lwqjh/dataset/4/download (format YOLOv11, "download code" via browser), upload ke Kaggle sebagai Dataset sendiri, lalu pada Cell 3 file zip otomatis terbaca — sesuaikan `DATA_PATH` di Cell 2 ke `/kaggle/input/<nama-dataset>/`.
- Expected: notebook baru bernama `yolo26s-train`, GPU aktif (cek `!nvidia-smi` di Cell 1).

## Task 1: Sel Setup & Cek GPU

- [ ] **Step 1:** Jalankan Cell 1 (`!nvidia-smi`). Expected: 1–2× T4 16 GB.

```python
!nvidia-smi --query-gpu=name,memory.total --format=csv
```

- [ ] **Step 2:** Jalankan Cell 2 (konfigurasi + secret). Expected: `DATA_PATH` menunjuk dataset, `ROBOFLOW_API_KEY` terbaca (atau None → jalur upload manual).

```python
import os
from pathlib import Path

try:
    from kaggle_secrets import UserSecretsClient
    secret = UserSecretsClient()
    api_key = secret.get_secret("ROBOFLOW_API_KEY")
except ImportError:
    api_key = None

DATA_DIR = Path("/kaggle/working/aerial-human-detection-4")
INPUT_ZIP = next(Path("/kaggle/input").glob("*/aerial*.zip"), None)
print("API key tersedia:", bool(api_key))
print("Zip di input:", INPUT_ZIP)
```

- [ ] **Step 3:** Jalankan Cell 3 (install). Expected: ultralytics ≥ 8.4 & roboflow terpasang.

```python
!pip install -q --upgrade ultralytics roboflow
import ultralytics, roboflow
print("ultralytics", ultralytics.__version__)
```

## Task 2: Download Dataset

- [ ] **Step 1:** Jalankan Cell 4. Expected: folder `.../aerial-human-detection-4/` berisi `train/`, `valid/`, `test/`, `data.yaml`.

```python
if not DATA_DIR.exists():
    if api_key:
        from roboflow import Roboflow
        rf = Roboflow(api_key=api_key)
        project = rf.workspace("mukuntha-rgwdi").project("aerial-human-detection-lwqjh")
        project.version(4).download("yolov11", location=str(DATA_DIR))
    elif INPUT_ZIP:
        import zipfile
        with zipfile.ZipFile(INPUT_ZIP) as z:
            z.extractall(DATA_DIR)
    else:
        raise SystemExit("Tidak ada API key maupun zip — upload dataset dulu (Task 0)")
print("dataset siap:", DATA_DIR.exists())
```

- [ ] **Step 2:** Jalankan Cell 5. Expected: yaml menampilkan `names: ['person']`, hitungan gambar per split ≈ train 3422, valid 53, test 4.

```python
import yaml
cfg = yaml.safe_load((DATA_DIR / "data.yaml").read_text())
print(cfg["names"])
for split in ["train", "valid", "test"]:
    d = DATA_DIR / split
    n = len(list(d.glob("*.jpg"))) + len(list(d.glob("*.png")))
    print(split, n)
```

## Task 3: Training YOLO26s

- [ ] **Step 1:** Jalankan Cell 6 (training). Expected: progress bar 100 epochs, early stop bila val stagnan ≥15 epochs, log mAP tiap epoch. Estimasi: ~60–120 menit di T4.

```python
from ultralytics import YOLO

model = YOLO("yolo26s.pt")
model.train(
    data=str(DATA_DIR / "data.yaml"),
    epochs=100,
    imgsz=640,
batch=64,           # total utk 2 GPU (32/GPU); auto-turun bila OOM
    patience=15,
    cache=True,
    device="0,1",       # kedua T4 (batch dibagi otomatis per GPU)
    project="/kaggle/working/run26s",
    name="train",
    exist_ok=True,
)
```

- [ ] **Step 2:** Jika error CUDA OOM → ganti `batch=32` jadi `batch=16`, ulangi Cell 6. Expected: training jalan tanpa OOM.

## Task 4: Validasi & Simpan Metrik

- [ ] **Step 1:** Jalankan Cell 7. Expected: tabel mAP — `mAP50-95`, `mAP50`, `precision`, `recall` untuk kelas `person`; metrik tersimpan ke `/kaggle/working/metrics.json`.

```python
import json
m = model.val(data=str(DATA_DIR / "data.yaml"), device=0)
metrics = {
    "mAP50-95": float(m.box.map),
    "mAP50": float(m.box.map50),
    "precision": float(m.box.mp),
    "recall": float(m.box.mr),
}
print(metrics)
Path("/kaggle/working/metrics.json").write_text(json.dumps(metrics, indent=2))
```

## Task 5: Export ONNX + TensorRT

- [ ] **Step 1:** Jalankan Cell 8. Expected: `best.onnx` dan `best.engine` di `/kaggle/working/run26s/train/weights/` (TRT butuh ~5–10 menit build).

```python
best = "/kaggle/working/run26s/train/weights/best.pt"
model = YOLO(best)
model.export(format="onnx", imgsz=640, dynamic=True)         # CPU/Jetson
try:
    model.export(format="engine", imgsz=640, half=True)      # TensorRT fp16, butuh GPU
except Exception as e:
    print("engine export gagal (opsional):", e)
```

## Task 6: Kumpulkan Artefak

- [ ] **Step 1:** Jalankan Cell 9. Expected: ketiga file terlihat di output.

```python
import shutil
out = Path("/kaggle/working/artifacts")
out.mkdir(exist_ok=True)
for f in ["best.pt", "best.onnx", "best.engine"]:
    src = Path("/kaggle/working/run26s/train/weights") / f
    if src.exists():
        shutil.copy(src, out / f)
    for f in out.iterdir():
        print(f.name, f.stat().st_size // 1024, "KB")
```

- [ ] **Step 2:** Kaggle: Run All → setelah selesai, **Commit & Run** (tombol kanan atas) → buka tab *Output* → download folder `artifacts/` ke `D:/KRTI/model/`.
- Expected: `best.pt` (±20 MB), `best.onnx` (±40 MB), `best.engine` (±40 MB) ada di `D:/KRTI/model/`.

## Task 7: Verifikasi Model di Laptop (setelah download)

- [ ] **Step 1:** Jalankan di `D:/KRTI`:

```bash
.venv\Scripts\python -c "from ultralytics import YOLO; m = YOLO('D:/KRTI/model/best.pt'); r = m.predict('D:/KRTI/test_frame.jpg', conf=0.25, save=True, project='D:/KRTI/out', name='verify26s', exist_ok=True); print(len(r[0].boxes), 'deteksi')"
```

- Expected: prediksi ≥ jumlah person yang terlihat di frame, dan mAP di `metrics.json` > mAP yolov8n COCO (37.3) — bandingkan.

## Self-Review

- **Spec coverage:** Backup v8 selesai (bertindak sebagai baseline pembanding di Task 7). Notebook mencakup setup → download → train → val → export → artifact. ✔
- **Placeholder scan:** Tidak ada TBD — semua sel berisi kode lengkap; hanya nilai konfigurasi (batch, imgsz) yang bisa disesuaikan dan disebutkan eksplisit. ✔
- **Type consistency:** `DATA_DIR`, `api_key`, `INPUT_ZIP` didefinisikan sekali di Cell 2 dan dipakai konsisten; nama file artefak konsisten antar sel. ✔