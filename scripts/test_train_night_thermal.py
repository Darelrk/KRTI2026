from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from train_night_thermal import (
    MODEL_FILES,
    build_runtime_data_yaml,
    count_split_images,
    resolve_model_path,
)


class ThermalPipelineTests(unittest.TestCase):
    def test_resolves_s_and_x_weights_from_repo_model_directory(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(resolve_model_path("s", root), root / "model" / "yolo26s.pt")
        with tempfile.TemporaryDirectory() as directory:
            model_root = Path(directory)
            (model_root / "model").mkdir()
            x_weight = model_root / "model" / "yolo26x.pt"
            x_weight.touch()
            self.assertEqual(resolve_model_path("x", model_root), x_weight)

    def test_rejects_missing_requested_weight(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                resolve_model_path("x", Path(directory))

    def test_normalizes_roboflow_relative_paths_and_counts_splits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset"
            for split, count in (("train", 3), ("valid", 2), ("test", 1)):
                image_dir = dataset / split / "images"
                label_dir = dataset / split / "labels"
                image_dir.mkdir(parents=True)
                label_dir.mkdir(parents=True)
                for index in range(count):
                    (image_dir / f"{index}.jpg").touch()
                    (label_dir / f"{index}.txt").write_text("0 0.5 0.5 0.2 0.2\n")

            source = dataset / "data.yaml"
            source.write_text(
                yaml.safe_dump(
                    {
                        "train": "../train/images",
                        "val": "../valid/images",
                        "test": "../test/images",
                        "nc": 1,
                        "names": ["Human"],
                    }
                )
            )
            runtime = build_runtime_data_yaml(dataset, root / "runtime.yaml")
            config = yaml.safe_load(runtime.read_text())

            self.assertEqual(config["names"], ["Human"])
            self.assertEqual(
                Path(config["train"]).resolve(), (dataset / "train" / "images").resolve()
            )
            self.assertEqual(
                Path(config["val"]).resolve(), (dataset / "valid" / "images").resolve()
            )
            self.assertEqual(count_split_images(dataset, "train"), 3)
            self.assertEqual(count_split_images(dataset, "valid"), 2)
            self.assertEqual(count_split_images(dataset, "test"), 1)


if __name__ == "__main__":
    unittest.main()
