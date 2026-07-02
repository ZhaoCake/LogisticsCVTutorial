# 视觉系统架构文档

## 项目概述

工训赛智能物流赛道小车视觉部分。基于 OpenCV 进行图像处理，通过串口与下位机（电控）通信，接收命令并返回检测结果。

---

## 通信协议

### 帧格式

| 方向 | 格式 | 说明 |
|------|------|------|
| 下位机 → 视觉 | `AA CMD 55` | 带帧头帧尾的命令帧 |
| 视觉 → 下位机 | `CC` | 收到命令后的立即应答（裸字节） |
| 视觉 → 下位机 | `AA DATA 55` | 任务状态的检测结果帧 |

- 帧头 `0xAA`，帧尾 `0x55`
- 数据域为 ASCII 编码字符串

### 命令码

| 命令 | 字节 | 行为 |
|------|------|------|
| `C0` | `0xC0` | 空闲(IDLE)，回复 CC 后持续处理视频流 |
| `C1` | `0xC1` | 扫描二维码，持续发 `AA 123456 55` |
| `C2` | `0xC2` | 颜色检测，持续发 `AA 123 55` |
| `C3` | `0xC3` | 圆环检测，持续发 `AA (123,123) 55` |

### 通信流程示例

```
下位机                          视觉
  │                              │
  ├── AA C1 55 ────────────────→ │  (发送二维码命令)
  │                              ├── CC (应答)
  │                              │  ┌ 切换到 SCAN_QR 状态
  │                              │  │
  │                              ├── AA 123456 55 ──→ (持续发送)
  │                              ├── AA 123456 55 ──→
  │                              ├── AA 123456 55 ──→
  │                              │
  ├── AA C0 55 ────────────────→ │  (发送空闲命令)
  │                              ├── CC (应答)
  │                              │  └ 回到 IDLE 状态
```

---

## 软件架构

```
main.py
  ├─ Camera             (src/camera.py)
  ├─ SerialComm         (src/serial_comm.py)
  ├─ StateMachine       (src/state_machine.py)
  │    ├─ IDLE          (阻塞等待命令)
  │    ├─ SCAN_QR       (qr_task.py)
  │    ├─ DETECT_COLOR  (color_task.py)
  │    └─ DETECT_CIRCLE (circle_task.py)
  └─ Protocol Consts    (src/protocol.py)
```

### 模块职责

| 模块 | 文件 | 职责 |
|------|------|------|
| `protocol.py` | `src/protocol.py` | 协议常量、帧解析 `parse_frame()`、组帧 `build_data_frame()` |
| `serial_comm.py` | `src/serial_comm.py` | pyserial 封装、读写缓冲区管理、阻塞/非阻塞读帧 |
| `camera.py` | `src/camera.py` | OpenCV VideoCapture 封装、提供最新帧 |
| `state_machine.py` | `src/state_machine.py` | 四状态状态机，内部自循环，命令驱动切换 |
| `tasks/qr_task.py` | `src/tasks/qr_task.py` | 二维码任务（当前数据写死） |
| `tasks/color_task.py` | `src/tasks/color_task.py` | 颜色检测任务（当前数据写死） |
| `tasks/circle_task.py` | `src/tasks/circle_task.py` | 圆环检测任务（当前数据写死） |
| `main.py` | `main.py` | 入口，初始化各模块，启动状态机 |

---

## 状态机

### 状态流转

```
                ┌──────────────────────┐
                │       IDLE           │
                │  阻塞等待命令到达     │
                └───────┬──────────────┘
                        │
            ┌───────────┼───────────┐
            │           │           │
        C1/C2/C3    C1/C2/C3    C1/C2/C3
            │           │           │
            ▼           ▼           ▼
    ┌───────────┐ ┌───────────┐ ┌───────────┐
    │  SCAN_QR  │ │DETECT_COL │ │DETECT_CRC │
    │ 持续发数据  │ │ 持续发数据 │ │ 持续发数据 │
    └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
          │             │             │
          └──────C0─────┴─────C0──────┘
                        │
                        ▼
                ┌──────────────┐
                │     IDLE     │
                └──────────────┘
```

### 设计要点

- **IDLE**: `read_frame(blocking=True)` 阻塞等待，收到命令回复 CC 后切换
- **任务状态**: `read_frame(blocking=False)` 非阻塞检查，无命令则执行任务逻辑
- **可中断**: 任何状态下收到任何命令（C0~C3）立即切换，无需回到 IDLE 再转跳
- **任务模块接口**: `task_module.run(camera, serial_comm) → bool`

---

## 串口通信层

`SerialComm` 内部维护一个 `bytearray` 接收缓冲区：

1. 每次读帧前先从串口读取所有可用字节追加到缓冲区
2. 调用 `protocol.parse_frame()` 从缓冲区头部尝试解析一帧
3. 解析成功则移除已消耗的字节并返回结果
4. 解析失败（帧不完整）则保留缓冲区，等待更多数据

### 关键方法

```python
comm.read_frame(blocking=True)    # 阻塞直到读到完整帧
comm.read_frame(blocking=False)   # 非阻塞，读不到返回 None
comm.send_ack()                   # 发送 0xCC
comm.send_data_frame("123456")    # 发送 AA 313233343536 55
```

---

## 调试方法

### 依赖

```bash
sudo apt install socat xxd
```

### 调试步骤

```bash
# 终端1：创建虚拟串口对
./scripts/setup_virtual_serial.sh

# 终端2：启动视觉程序（连接 /tmp/ttyV1）
python main.py

# 终端3：模拟下位机发送命令
./scripts/send_cmd.sh C1    # 切换到二维码任务
./scripts/send_cmd.sh C0    # 回到空闲

# 终端4：查看视觉回复
./scripts/monitor_reply.sh
```

> `/tmp/ttyV0` = 下位机端（用 `send_cmd.sh` 写）
> `/tmp/ttyV1` = 视觉端（程序连接这个口）

### 手动调试命令

```bash
# 发命令: printf '\xAA\xC1\x55' > /tmp/ttyV0
# 读回复: cat /tmp/ttyV1 | xxd
```

---

## 扩展：接入实际检测逻辑

当前任务数据全部写死在模块级变量中，后续替换为真实检测逻辑即可：

```python
# qr_task.py 改造示例
import cv2
from pyzbar.pyzbar import decode

def run(camera, serial_comm):
    frame = camera.get_frame()
    if frame is None:
        return True

    # 实际 QR 解码
    barcodes = decode(frame)
    data = barcodes[0].data.decode("utf-8") if barcodes else "None"

    serial_comm.send_data_frame(data)
    return True
```
