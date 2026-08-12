"""Train and export a YOLO26 thermal person detector locally.

Usage:
    python scripts/train_night_thermal.py --model s --epochs 100
    python scripts/train_night_thermal.py --model x --epochs 100

The default is YOLO26s because the current laptop is CPU-only. YOLO26x is
accepted when its local weight file is available, but is not a practical CPU
training choice.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import yaml

MODEL_FILES = {"s": "yolo26s.pt", "x": "yolo26x.pt"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def resolve_model_path(variant: str, repo_root: Path) -> Path:
    """Return an existing local YOLO26 weight file for ``variant``."""
    try:
        filename = MODEL_FILES[variant]
    except KeyError as error:
        raise ValueError(f"model harus s atau x, bukan {variant!r}") from error
    path = repo_root / "model" / filename
    if not path.is_file():
        raise FileNotFoundError(
            f"Bobot {filename} tidak ditemukan di {path}. "
            "Tambahkan bobot YOLO26 tersebut ke model/ terlebih dahulu."
        )
    return path


def _split_image_dir(dataset_dir: Path, split: str, raw_path: str | None) -> Path:
    """Resolve a split, preferring the normal Roboflow directory layout."""
    direct = dataset_dir / split / "images"
    if direct.is_dir():
        return direct.resolve()
    if raw_path:
        candidate = (dataset_dir / raw_path).resolve()
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"Folder gambar split {split!r} tidak ditemukan")


def build_runtime_data_yaml(dataset_dir: Path, destination: Path) -> Path:
    """Write an Ultralytics YAML with absolute paths and validated class names."""
    dataset_dir = dataset_dir.resolve()
    source = dataset_dir / "data.yaml"
    if not source.is_file():
        raise FileNotFoundError(f"data.yaml tidak ditemukan: {source}")
    config: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))
    names = config.get("names")
    if not isinstance(names, list) or names != ["Human"]:
        raise ValueError(f"Dataset harus satu kelas Human, mendapat: {names!r}")

    runtime = {
        "path": str(dataset_dir),
        "train": str(_split_image_dir(dataset_dir, "train", config.get("train"))),
        "val": str(_split_image_dir(dataset_dir, "valid", config.get("val"))),
        "test": str(_split_image_dir(dataset_dir, "test", config.get("test"))),
        "nc": 1,
        "names": names,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(yaml.safe_dump(runtime, sort_keys=False), encoding="utf-8")
    return destination


def count_split_images(dataset_dir: Path, split: str) -> int:
    """Count image files in a dataset split."""
    image_dir = dataset_dir / split / "images"
    return sum(path.suffix.lower() in IMAGE_EXTENSIONS for path in image_dir.iterdir())


def choose_device(requested: str) -> str:
    """Choose CPU unless the caller explicitly requests a device."""
    if requested != "auto":
        return requested
    try:
        import torch
    except ImportError:
        return "cpu"
    return "0" if torch.cuda.is_available() else "cpu"


def _copy_if_exists(source: Path, destination: Path) -> Path | None:
    if not source.is_file():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def train(args: argparse.Namespace) -> dict[str, Any]:
    from ultralytics import YOLO

    repo_root = Path(__file__).resolve().parents[1]
    dataset_dir = Path(args.dataset).resolve()
    run_dir = Path(args.run_dir).resolve()
    runtime_yaml = build_runtime_data_yaml(dataset_dir, run_dir / "data.yaml")
    device = choose_device(args.device)
    weights = resolve_model_path(args.model, repo_root)

    counts = {
        split: count_split_images(dataset_dir, split)
        for split in ("train", "valid", "test")
    }
    print(f"model={weights.name} device={device} dataset={dataset_dir}")
    print(f"split={counts}")
    if device == "cpu" and args.model == "x":
        print("PERINGATAN: YOLO26x di CPU sangat lambat; YOLO26s lebih realistis.")

    model = YOLO(str(weights))
    model.train(
        data=str(runtime_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        device=device,
        workers=args.workers,
        cache=False,
        project=str(run_dir),
        name="train",
        exist_ok=True,
        pretrained=True,
        degrees=5,
        translate=0.1,
        scale=0.4,
        fliplr=0.5,
        mosaic=0.5,
    )

    best = run_dir / "train" / "weights" / "best.pt"
    if not best.is_file():
        raise FileNotFoundError(f"best.pt tidak dihasilkan: {best}")
    best_model = YOLO(str(best))
    metrics_result = best_model.val(data=str(runtime_yaml), device=device)
    metrics = {
        "model": args.model,
        "device": device,
        "dataset": str(dataset_dir),
        "images": counts,
        "mAP50-95": float(metrics_result.box.map),
        "mAP50": float(metrics_result.box.map50),
        "precision": float(metrics_result.box.mp),
        "recall": float(metrics_result.box.mr),
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    artifact_dir = repo_root / "model"
    artifact_base = artifact_dir / "best-night-thermal"
    outputs = {
        "pt": _copy_if_exists(best, artifact_base.with_suffix(".pt")),
    }
    try:
        exported = Path(best_model.export(format="onnx", imgsz=args.imgsz, dynamic=True))
        outputs["onnx"] = _copy_if_exists(exported, artifact_base.with_suffix(".onnx"))
    except Exception as error:
        print(f"ONNX export gagal: {error}")
    try:
        exported = Path(best_model.export(format="engine", imgsz=args.imgsz, half=True))
        outputs["engine"] = _copy_if_exists(exported, artifact_base.with_suffix(".engine"))
    except Exception as error:
        print(f"TensorRT export dilewati: {error}")
    print(json.dumps({"metrics": metrics, "artifacts": {k: str(v) for k, v in outputs.items()}}, indent=2))
    return metrics


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=tuple(MODEL_FILES), default="s")
    parser.add_argument("--dataset", default=str(root / "model" / "data" / "night-vision"))
    parser.add_argument("--run-dir", default=str(root / "runs" / "night-thermal"))
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--device", default="auto")
    return parser.parse_args(argv)


def main() -> None:
    train(parse_args())


if __name__ == "__main__":
    main()
