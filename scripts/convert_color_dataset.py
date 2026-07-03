import cv2
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "resources" / "color_datasets"
DST = PROJECT_ROOT / "train" / "datasets" / "color"

MAPPING = {0: 0, 1: 0, 2: 0, 3: 0}

def main():
    print(f"Source: {SRC}")
    print(f"Destination: {DST}")
    print(f"Class mapping: {MAPPING}\n")

    for split in ["train", "val"]:
        img_dir = SRC / split / "images"
        lbl_dir = SRC / split / "labels"
        dst_img_dir = DST / split / "images"
        dst_lbl_dir = DST / split / "labels"

        dst_img_dir.mkdir(parents=True, exist_ok=True)
        dst_lbl_dir.mkdir(parents=True, exist_ok=True)

        jpg_files = sorted(img_dir.glob("*.jpg"))
        print(f"[{split}] Processing {len(jpg_files)} images...")

        for i, img_path in enumerate(jpg_files):
            name = img_path.stem

            img = cv2.imread(str(img_path))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            np.savez_compressed(dst_img_dir / f"{name}.npz", image=gray)

            lbl_path = lbl_dir / f"{name}.txt"
            if lbl_path.exists():
                lines = lbl_path.read_text().strip().splitlines()
                new_lines = []
                for line in lines:
                    parts = line.strip().split()
                    if parts:
                        old_id = int(parts[0])
                        new_id = MAPPING[old_id]
                        new_lines.append(f"{new_id} " + " ".join(parts[1:]))
                (dst_lbl_dir / f"{name}.txt").write_text("\n".join(new_lines))

            if (i + 1) % 200 == 0:
                print(f"  [{split}] {i + 1}/{len(jpg_files)} done")

        print(f"  [{split}] Complete: {len(jpg_files)} images, {len(jpg_files)} labels\n")

    print("Done.")

if __name__ == "__main__":
    main()
