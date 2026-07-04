import argparse
import sys
from pathlib import Path

import torch
import torch.optim as optim
from torch.utils.data import DataLoader

from model import DetectionModel
from dataset import DetectionDataset
from loss import DetectionLoss
from metrics import compute_map

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = PROJECT_ROOT / "train" / "datasets"
RUNS_ROOT = Path(__file__).resolve().parent / "runs"


def train_one_epoch(
    model, loader, loss_fn, optimizer, device
):
    model.train()
    total_loss = 0.0
    total_coord = 0.0
    total_obj = 0.0
    total_cls = 0.0

    for images, targets in loader:
        images = images.to(device)
        targets = targets.to(device)

        optimizer.zero_grad()
        pred = model(images)
        loss, coord, obj, cls_ = loss_fn(pred, targets)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        total_coord += coord.item()
        total_obj += obj.item()
        total_cls += cls_.item()

    n = len(loader)
    return total_loss / n, total_coord / n, total_obj / n, total_cls / n


@torch.no_grad()
def validate(model, loader, loss_fn, device):
    model.eval()
    total_loss = 0.0
    total_coord = 0.0
    total_obj = 0.0
    total_cls = 0.0

    all_predictions = []
    all_targets = []

    for images, targets in loader:
        images = images.to(device)
        targets = targets.to(device)

        pred = model(images)
        loss, coord, obj, cls_ = loss_fn(pred, targets)

        total_loss += loss.item()
        total_coord += coord.item()
        total_obj += obj.item()
        total_cls += cls_.item()

        all_predictions.append(pred.cpu())
        all_targets.append(targets.cpu())

    n = len(loader)
    avg_loss = total_loss / n, total_coord / n, total_obj / n, total_cls / n

    all_predictions = torch.cat(all_predictions, dim=0)
    all_targets = torch.cat(all_targets, dim=0)
    mAP = compute_map(all_predictions, all_targets, model.num_classes)

    return avg_loss, mAP


def main():
    parser = argparse.ArgumentParser(description="Train object detection model")
    parser.add_argument(
        "--dataset", choices=["circle", "color"], required=True,
        help="Dataset name"
    )
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    num_classes = {"circle": 2, "color": 1}[args.dataset]
    device = torch.device(args.device)

    print(f"Dataset: {args.dataset}  |  Classes: {num_classes}  |  Device: {device}")
    print(f"Epochs: {args.epochs}  |  Batch: {args.batch}  |  LR: {args.lr}\n")

    model = DetectionModel(num_classes=num_classes).to(device)
    input_size = 224
    grid_size = input_size // (2 ** model.num_pools)

    train_dataset = DetectionDataset(
        root=DATA_ROOT / args.dataset / "train",
        num_classes=num_classes,
        input_size=input_size,
        grid_size=grid_size,
        augment=True,
    )
    val_dataset = DetectionDataset(
        root=DATA_ROOT / args.dataset / "val",
        num_classes=num_classes,
        input_size=input_size,
        grid_size=grid_size,
        augment=False,
    )

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch, shuffle=True, num_workers=0, pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch, shuffle=False, num_workers=0, pin_memory=True
    )

    print(f"Train: {len(train_dataset)}  |  Val: {len(val_dataset)}\n")

    model = DetectionModel(num_classes=num_classes).to(device)
    loss_fn = DetectionLoss(num_classes=num_classes)
    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_loss = float("inf")
    run_dir = RUNS_ROOT / args.dataset
    run_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        train_loss, train_coord, train_obj, train_cls = train_one_epoch(
            model, train_loader, loss_fn, optimizer, device
        )
        scheduler.step()

        (val_loss, val_coord, val_obj, val_cls), val_map = validate(
            model, val_loader, loss_fn, device
        )

        lr = scheduler.get_last_lr()[0]

        print(
            f"Epoch {epoch:3d}/{args.epochs} | "
            f"LR {lr:.2e} | "
            f"T loss {train_loss:.4f} | "
            f"V loss {val_loss:.4f} | "
            f"V mAP {val_map:.4f}"
        )
        print(
            f"        | "
            f"T coord {train_coord:.4f} obj {train_obj:.4f} cls {train_cls:.4f} | "
            f"V coord {val_coord:.4f} obj {val_obj:.4f} cls {val_cls:.4f}"
        )

        if val_loss < best_loss:
            best_loss = val_loss
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "loss": val_loss,
                "mAP": val_map,
                "num_classes": num_classes,
            }
            torch.save(checkpoint, run_dir / "best.pt")
            print(f"        | *** Saved best checkpoint (loss={val_loss:.4f}, mAP={val_map:.4f})")

        print()

    print(f"Training complete. Best model saved to {run_dir / 'best.pt'}")


if __name__ == "__main__":
    main()
