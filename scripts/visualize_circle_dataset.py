import argparse
import random
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "outputs"

DATASETS = {
    "circle": {
        "path": PROJECT_ROOT / "train" / "datasets" / "circle",
        "class_names": {0: "shape_A", 1: "shape_B"},
        "class_colors": {0: (0, 255, 0), 1: (0, 0, 255)},
    },
    "color": {
        "path": PROJECT_ROOT / "train" / "datasets" / "color",
        "class_names": {0: "color_obj"},
        "class_colors": {0: (0, 255, 0)},
    },
}

GRID_COLS = 3
GRID_ROWS = 2
SAMPLE_COUNT = GRID_COLS * GRID_ROWS
DISPLAY_H = 360
DISPLAY_W = 480
PADDING = 20


def load_sample(img_path: Path, lbl_path: Path, class_names: dict, class_colors: dict):
    gray = np.load(str(img_path))["image"]
    h, w = gray.shape
    img_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    lines = lbl_path.read_text().strip().splitlines()
    for line in lines:
        parts = line.strip().split()
        if not parts:
            continue
        cls_id = int(parts[0])
        xc, yc, bw, bh = map(float, parts[1:5])
        x1 = int((xc - bw / 2) * w)
        y1 = int((yc - bh / 2) * h)
        x2 = int((xc + bw / 2) * w)
        y2 = int((yc + bh / 2) * h)
        color = class_colors.get(cls_id, (255, 255, 255))
        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), color, 2)
        label = class_names.get(cls_id, f"cls_{cls_id}")
        cv2.putText(img_bgr, label, (x1, max(y1 - 5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    return img_bgr


def main():
    parser = argparse.ArgumentParser(description="Visualize dataset samples")
    parser.add_argument("--dataset", choices=list(DATASETS.keys()), default="circle",
                        help="Dataset name (default: circle)")
    parser.add_argument("--split", choices=["train", "val"], default="val",
                        help="Dataset split (default: val)")
    parser.add_argument("--show", action="store_true",
                        help="Display interactively instead of saving to file")
    parser.add_argument("--out", type=str, default=None,
                        help=f"Output image path (default: outputs/<dataset>_grid_<timestamp>.png)")
    args = parser.parse_args()

    cfg = DATASETS[args.dataset]
    img_dir = cfg["path"] / args.split / "images"
    lbl_dir = cfg["path"] / args.split / "labels"

    all_files = sorted(img_dir.glob("*.npz"))
    if len(all_files) < SAMPLE_COUNT:
        print(f"Only {len(all_files)} samples in {args.split}, need {SAMPLE_COUNT}")
        return
    samples = random.sample(all_files, SAMPLE_COUNT)

    canvas = np.zeros(
        (GRID_ROWS * DISPLAY_H + (GRID_ROWS + 1) * PADDING,
         GRID_COLS * DISPLAY_W + (GRID_COLS + 1) * PADDING, 3),
        dtype=np.uint8,
    )

    for idx, npz_path in enumerate(samples):
        name = npz_path.stem
        lbl_path = lbl_dir / f"{name}.txt"
        img_bgr = load_sample(npz_path, lbl_path, cfg["class_names"], cfg["class_colors"])

        row = idx // GRID_COLS
        col = idx % GRID_COLS
        y_start = PADDING + row * (DISPLAY_H + PADDING)
        x_start = PADDING + col * (DISPLAY_W + PADDING)
        img_bgr = cv2.resize(img_bgr, (DISPLAY_W, DISPLAY_H))
        canvas[y_start:y_start + DISPLAY_H, x_start:x_start + DISPLAY_W] = img_bgr

    if args.show:
        cv2.imshow(f"{args.dataset.title()} Dataset ({args.split} split)", canvas)
        print("Press any key to close...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if args.out:
            out_path = Path(args.out)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = OUTPUT_DIR / f"{args.dataset}_grid_{args.split}_{timestamp}.png"
        cv2.imwrite(str(out_path), canvas)
        print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
