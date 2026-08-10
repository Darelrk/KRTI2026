"""Deteksi person dari frame UAV — model lokal, tanpa env/config.

Model: yolov8n.pt (COCO, sudah dilatih; person termasuk). Tinggal jalankan:

    python detect_person.py path/gambar.jpg [conf] [output_dir]

Contoh: python detect_person.py D:/KRTI/test_frame.jpg 0.25
"""
import sys
from pathlib import Path

from ultralytics import YOLO

MODEL = Path(__file__).resolve().parent.parent / "models" / "yolov8n.pt"


def main() -> None:
    if len(sys.argv) < 2:
        print("pemakaian: python detect_person.py <gambar> [conf] [output_dir]")
        sys.exit(1)
    conf = float(sys.argv[2]) if len(sys.argv) > 2 else 0.25
    out_dir = sys.argv[3] if len(sys.argv) > 3 else "out"

    model = YOLO(MODEL)
    results = model.predict(
        sys.argv[1], conf=conf, save=True, project=out_dir, name="detect", exist_ok=True
    )
    boxes = results[0].boxes
    print(f"{len(boxes)} deteksi person (conf>={conf}):")
    for b in boxes:
        if model.names[int(b.cls.item())] == "person":
            print(
                f"  person {float(b.conf):.3f} "
                f"x={b.xyxy[0][0].item():.0f} y={b.xyxy[0][1].item():.0f} "
                f"x2={b.xyxy[0][2].item():.0f} y2={b.xyxy[0][3].item():.0f}"
            )
    print(f"hasil anotasi: {out_dir}/detect/")


if __name__ == "__main__":
    main()