import torch
import torch.nn as nn
import torch.nn.functional as F


class DetectionLoss(nn.Module):
    def __init__(
        self,
        num_classes: int,
        lambda_coord: float = 5.0,
        lambda_noobj: float = 0.5,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.lambda_coord = lambda_coord
        self.lambda_noobj = lambda_noobj

    def forward(self, pred: torch.Tensor, target: torch.Tensor):
        B = pred.shape[0]

        pred_tx = pred[:, 0, :, :]
        pred_ty = pred[:, 1, :, :]
        pred_tw = pred[:, 2, :, :]
        pred_th = pred[:, 3, :, :]
        pred_obj = pred[:, 4, :, :]
        pred_cls = pred[:, 5:, :, :]

        target_tx = target[:, :, :, 0]
        target_ty = target[:, :, :, 1]
        target_tw = target[:, :, :, 2]
        target_th = target[:, :, :, 3]
        target_obj = target[:, :, :, 4]
        target_cls = target[:, :, :, 5:]

        obj_mask = target_obj > 0.5
        noobj_mask = ~obj_mask

        coord_loss = (
            F.mse_loss(torch.sigmoid(pred_tx[obj_mask]), target_tx[obj_mask], reduction="sum")
            + F.mse_loss(torch.sigmoid(pred_ty[obj_mask]), target_ty[obj_mask], reduction="sum")
            + F.mse_loss(torch.sigmoid(pred_tw[obj_mask]), target_tw[obj_mask], reduction="sum")
            + F.mse_loss(torch.sigmoid(pred_th[obj_mask]), target_th[obj_mask], reduction="sum")
        )
        coord_loss *= self.lambda_coord / B

        obj_loss = F.binary_cross_entropy_with_logits(
            pred_obj[obj_mask], target_obj[obj_mask], reduction="sum"
        )
        noobj_loss = F.binary_cross_entropy_with_logits(
            pred_obj[noobj_mask], target_obj[noobj_mask], reduction="sum"
        )
        obj_loss = (obj_loss + self.lambda_noobj * noobj_loss) / B

        cls_loss = torch.tensor(0.0, device=pred.device)
        n_obj = obj_mask.sum().item()
        if n_obj > 0:
            pred_cls_obj = pred_cls.permute(0, 2, 3, 1)[obj_mask]
            target_cls_idx = target_cls[obj_mask].argmax(dim=1)
            cls_loss = F.cross_entropy(pred_cls_obj, target_cls_idx, reduction="sum") / B

        total = coord_loss + obj_loss + cls_loss
        return total, coord_loss.detach(), obj_loss.detach(), cls_loss.detach()
