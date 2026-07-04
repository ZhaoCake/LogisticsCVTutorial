# train

训练目标检测模型。

## 文件结构

```
train/
├── datasets/
│   ├── circle/              # 圆形数据集 (2类: shape_A, shape_B)
│   │   ├── train/images/    # 942 张 .npz 灰度图 (480×640)
│   │   ├── train/labels/    # YOLO 格式标签
│   │   ├── val/images/      # 81 张
│   │   └── val/labels/
│   └── color/               # 颜色数据集 (1类: color_obj)
│       ├── train/images/    # 901 张 .npz 灰度图 (480×640)
│       ├── train/labels/
│       ├── val/images/      # 189 张
│       └── val/labels/
├── model.py                 # 模型定义
├── dataset.py               # 数据加载
├── loss.py                  # 损失函数
├── metrics.py               # mAP 计算
├── train.py                 # 训练入口
└── runs/                    # 模型输出目录
    ├── circle/best.pt       # circle 数据集最佳模型
    └── color/best.pt        # color 数据集最佳模型
```

## 模型架构

轻量全卷积检测网络 (~25K 参数)，4 层下采样。

```
输入: 224×224×1 (灰度图，resize 自 480×640)

Block1: Conv(1→8,  3×3) + BN + ReLU + MaxPool(2)  → 112×112×8
Block2: Conv(8→16, 3×3) + BN + ReLU + MaxPool(2)  → 56×56×16
Block3: Conv(16→32, 3×3) + BN + ReLU + MaxPool(2)  → 28×28×32
Block4: Conv(32→64, 3×3) + BN + ReLU + MaxPool(2)  → 14×14×64
Head:   Conv(64→5+C, 1×1)                          → 14×14×(5+C)

输出: 14×14 网格，每个格子预测 (tx, ty, tw, th, obj_conf) + C 个类别概率
```

> 结果加了第四个block之后60多个epoch时map50就达到0.96了。

仅包含 4 种标准算子 (Conv2D, BatchNorm, ReLU, MaxPool2d)，易于移植到 ONNX / TensorRT / OpenVINO / 移动端推理框架。

## 环境准备

```bash
# 安装依赖 (CPU-only PyTorch，清华镜像加速)
uv sync

# 验证安装
.venv/bin/python -c "import torch; print('torch', torch.__version__, 'CUDA:', torch.cuda.is_available())"
```

## 训练

```bash
# 训练 circle 数据集 (2 类)
.venv/bin/python train/train.py --dataset circle --epochs 150 --batch 16

# 训练 color 数据集 (1 类)
.venv/bin/python train/train.py --dataset color --epochs 150 --batch 16

# 自定义参数
.venv/bin/python train/train.py \
    --dataset circle \
    --epochs 200 \
    --batch 8 \
    --lr 0.0005
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--dataset` | (必填) | 数据集名称: `circle` 或 `color` |
| `--epochs` | 150 | 训练轮数 |
| `--batch` | 16 | 批次大小 |
| `--lr` | 1e-3 | 初始学习率 (余弦退火衰减) |
| `--device` | 自动检测 | 训练设备: `cpu` 或 `cuda` |

### 训练输出

```bash
Epoch   1/150 | LR 1.00e-03 | T loss 12.3456 | V loss 11.2345 | V mAP 0.1234
        | T coord 1.2345 obj 5.6789 cls 5.4321 | V coord 1.1111 obj 5.2222 cls 4.9012
        | *** Saved best checkpoint (loss=11.2345, mAP=0.1234)
```

每轮输出:
- `T loss`: 训练集总损失
- `V loss`: 验证集总损失
- `V mAP`: 验证集 mAP@0.5
- `T/V coord`: 坐标回归损失
- `T/V obj`: 目标置信度损失
- `T/V cls`: 分类损失

模型保存在 `train/runs/{dataset}/best.pt`，按验证损失取最优。

## 推理

```python
import torch
import cv2
import numpy as np
from pathlib import Path
from train.model import DetectionModel
from train.metrics import decode_predictions

# 加载模型
checkpoint = torch.load("train/runs/circle/best.pt", map_location="cpu")
model = DetectionModel(num_classes=checkpoint["num_classes"])
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

# 加载图像 (npz 格式或任意灰度图)
# 方式 1: 从 npz 加载
img = np.load("path/to/image.npz")["image"]

# 方式 2: 从 jpg/png 加载
# img = cv2.imread("path/to/image.jpg", cv2.IMREAD_GRAYSCALE)

# 预处理
img = cv2.resize(img, (224, 224)).astype(np.float32) / 255.0
tensor = torch.from_numpy(img).unsqueeze(0).unsqueeze(0)  # (1, 1, 224, 224)

# 推理
with torch.no_grad():
    pred = model(tensor)  # (1, 5+C, 20, 20)

# 解码
boxes = decode_predictions(pred, num_classes=checkpoint["num_classes"], conf_threshold=0.5)
# boxes: List[List[x1, y1, x2, y2, score, class_id]], 按图片索引分组

for img_id, img_boxes in enumerate(boxes):
    for box in img_boxes:
        x1, y1, x2, y2, score, cls_id = box
        print(f"  类别 {cls_id}: ({x1:.3f},{y1:.3f})-({x2:.3f},{y2:.3f}), 置信度 {score:.3f}")
```

### 坐标说明

预测输出均为归一化坐标 [0, 1]，转换到原始图像坐标:

```python
h_orig, w_orig = 480, 640  # 原图尺寸
x1_abs = x1 * w_orig
y1_abs = y1 * h_orig
x2_abs = x2 * w_orig
y2_abs = y2 * h_orig
```

### 模型导出 (可选)

```python
import torch
from train.model import DetectionModel

checkpoint = torch.load("train/runs/circle/best.pt", map_location="cpu")
model = DetectionModel(num_classes=checkpoint["num_classes"])
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

# 导出 ONNX
dummy = torch.randn(1, 1, 224, 224)
torch.onnx.export(model, dummy, "train/runs/circle/best.onnx",
    input_names=["input"],
    output_names=["output"],
    opset_version=17,
)

# 导出 TorchScript
scripted = torch.jit.script(model)
scripted.save("train/runs/circle/best_scripted.pt")
```

## 类别定义

| 数据集 | 类别 | 含义 |
|--------|------|------|
| circle | 0 | shape_A (原始类别 1,3,5) |
| circle | 1 | shape_B (原始类别 0,2,4) |
| color | 0 | color_obj (所有颜色) |
