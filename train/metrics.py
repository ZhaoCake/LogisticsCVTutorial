import torch
import torch.nn.functional as F


def decode_predictions(
    pred: torch.Tensor, num_classes: int, input_size: int = 320, conf_threshold: float = 0.1
):
    B, _, S, _ = pred.shape
    C = num_classes

    tx = torch.sigmoid(pred[:, 0, :, :])
    ty = torch.sigmoid(pred[:, 1, :, :])
    tw = torch.sigmoid(pred[:, 2, :, :])
    th = torch.sigmoid(pred[:, 3, :, :])
    obj = torch.sigmoid(pred[:, 4, :, :])
    cls_probs = F.softmax(pred[:, 5:, :, :], dim=1)

    all_boxes = []

    for b in range(B):
        boxes = []
        for i in range(S):
            for j in range(S):
                conf = obj[b, i, j].item()
                if conf < conf_threshold:
                    continue
                cls_conf, cls_id = cls_probs[b, :, i, j].max(dim=0)
                cls_conf = cls_conf.item()

                xc = (j + tx[b, i, j].item()) / S
                yc = (i + ty[b, i, j].item()) / S
                w = tw[b, i, j].item()
                h = th[b, i, j].item()

                score = conf * cls_conf
                if score < conf_threshold:
                    continue

                x1 = xc - w / 2
                y1 = yc - h / 2
                x2 = xc + w / 2
                y2 = yc + h / 2

                boxes.append([x1, y1, x2, y2, score, cls_id.item()])

        all_boxes.append(boxes)

    return all_boxes


def decode_targets(target: torch.Tensor, num_classes: int, input_size: int = 320):
    B, S, _, _ = target.shape
    all_boxes = []

    for b in range(B):
        boxes = []
        for i in range(S):
            for j in range(S):
                obj = target[b, i, j, 4].item()
                if obj < 0.5:
                    continue

                tx = target[b, i, j, 0].item()
                ty = target[b, i, j, 1].item()
                tw = target[b, i, j, 2].item()
                th = target[b, i, j, 3].item()

                xc = (j + tx) / S
                yc = (i + ty) / S
                w = tw
                h = th

                x1 = xc - w / 2
                y1 = yc - h / 2
                x2 = xc + w / 2
                y2 = yc + h / 2

                cls_id = target[b, i, j, 5:].argmax().item()
                boxes.append([x1, y1, x2, y2, cls_id])

        all_boxes.append(boxes)

    return all_boxes


def box_iou(box_a, box_b):
    xa1, ya1, xa2, ya2 = box_a
    xb1, yb1, xb2, yb2 = box_b

    inter_x1 = max(xa1, xb1)
    inter_y1 = max(ya1, yb1)
    inter_x2 = min(xa2, xb2)
    inter_y2 = min(ya2, yb2)

    if inter_x1 >= inter_x2 or inter_y1 >= inter_y2:
        return 0.0

    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    area_a = (xa2 - xa1) * (ya2 - ya1)
    area_b = (xb2 - xb1) * (yb2 - yb1)
    union = area_a + area_b - inter_area

    return inter_area / union if union > 0 else 0.0


def compute_map(predictions, targets, num_classes, iou_threshold=0.5):
    pred_boxes = decode_predictions(predictions, num_classes)
    gt_boxes = decode_targets(targets, num_classes)

    average_precisions = []

    for cls_id in range(num_classes):
        sorted_preds = []
        for img_id, boxes in enumerate(pred_boxes):
            for box in boxes:
                if box[5] == cls_id:
                    sorted_preds.append((img_id, box[4], box[:4], box[5]))

        if not sorted_preds:
            average_precisions.append(0.0)
            continue

        sorted_preds.sort(key=lambda x: x[1], reverse=True)

        tp = [0] * len(sorted_preds)
        fp = [0] * len(sorted_preds)

        matched = {img_id: [False] * len(gt_boxes[img_id]) for img_id in range(len(gt_boxes))}

        for idx, (img_id, _, pred_box, _) in enumerate(sorted_preds):
            best_iou = 0.0
            best_gt_idx = -1
            for gt_idx, gt_box in enumerate(gt_boxes[img_id]):
                if gt_box[4] != cls_id:
                    continue
                iou = box_iou(pred_box, gt_box[:4])
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = gt_idx

            if best_iou >= iou_threshold and best_gt_idx >= 0 and not matched[img_id][best_gt_idx]:
                tp[idx] = 1
                matched[img_id][best_gt_idx] = True
            else:
                fp[idx] = 1

        cum_tp = []
        cum_fp = []
        sum_tp = sum_fp = 0
        for t, f in zip(tp, fp):
            sum_tp += t
            sum_fp += f
            cum_tp.append(sum_tp)
            cum_fp.append(sum_fp)

        recalls = [t / max(sum_tp, 1) for t in cum_tp]
        precisions = [t / max(t + f, 1) for t, f in zip(cum_tp, cum_fp)]

        ap = 0.0
        for r in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
            max_p = 0.0
            for rec, prec in zip(recalls, precisions):
                if rec >= r:
                    max_p = max(max_p, prec)
            ap += max_p / 11.0

        average_precisions.append(ap)

    return sum(average_precisions) / len(average_precisions) if average_precisions else 0.0
