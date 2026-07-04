import random
from pathlib import Path

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset


class DetectionDataset(Dataset):
    def __init__(
        self,
        root: Path,
        num_classes: int,
        input_size: int = 224,
        grid_size: int = 28,
        augment: bool = False,
    ):
        self.root = Path(root)
        self.num_classes = num_classes
        self.input_size = input_size
        self.grid_size = grid_size
        self.augment = augment

        self.image_files = sorted((self.root / "images").glob("*.npz"))

    def __len__(self) -> int:
        return len(self.image_files)

    def __getitem__(self, idx: int):
        npz_path = self.image_files[idx]
        label_path = self.root / "labels" / f"{npz_path.stem}.txt"

        img = np.load(str(npz_path))["image"]
        img = cv2.resize(img, (self.input_size, self.input_size))
        img = img.astype(np.float32) / 255.0

        if self.augment:
            img = self._apply_augment(img)

        img = torch.from_numpy(img).unsqueeze(0)

        target = self._build_target(label_path)

        if self.augment:
            target = self._augment_target(target)

        return img, target

    def _apply_augment(self, img: np.ndarray) -> np.ndarray:
        if random.random() < 0.5:
            img = np.fliplr(img)
            self._flipped = True
        else:
            self._flipped = False

        brightness = random.uniform(0.8, 1.2)
        img = np.clip(img * brightness, 0, 1)

        return img

    def _augment_target(self, target: torch.Tensor) -> torch.Tensor:
        if getattr(self, "_flipped", False):
            target = torch.flip(target, [1])
            target[:, :, 0] = 1.0 - target[:, :, 0]
        return target

    def _build_target(self, label_path: Path) -> torch.Tensor:
        S = self.grid_size
        C = self.num_classes
        target = torch.zeros(S, S, 5 + C)
        input_size = self.input_size

        if not label_path.exists():
            return target

        for line in label_path.read_text().strip().splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            cls_id = int(parts[0])
            xc, yc, bw, bh = map(float, parts[1:5])

            xc *= input_size
            yc *= input_size
            bw *= input_size
            bh *= input_size

            gx = int(xc * S / input_size)
            gy = int(yc * S / input_size)

            if gx < 0 or gx >= S or gy < 0 or gy >= S:
                continue

            if target[gy, gx, 4] > 0:
                continue

            cell_w = input_size / S
            cell_h = input_size / S
            tx = (xc - gx * cell_w) / cell_w
            ty = (yc - gy * cell_h) / cell_h
            tw = bw / input_size
            th = bh / input_size

            target[gy, gx, 0] = tx
            target[gy, gx, 1] = ty
            target[gy, gx, 2] = tw
            target[gy, gx, 3] = th
            target[gy, gx, 4] = 1.0
            target[gy, gx, 5 + cls_id] = 1.0

        return target
