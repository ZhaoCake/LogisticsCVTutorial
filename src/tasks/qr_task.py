"""
二维码扫描任务

当前阶段：数据写死为 "123456"。
后续接入 pyzbar 实现实际的二维码解码。

在任务状态下持续:
  1. 获取当前帧（供后续解码使用）
  2. 向下位机发送 AA 123456 55
"""

import time


# ── 占位数据，后续替换为真实解码逻辑 ──────────────────────
_QR_DATA = "123456"


def run(camera, serial_comm):
    """二维码扫描任务主循环

    参数:
        camera:      Camera 实例，用于获取图像帧
        serial_comm: SerialComm 实例，用于收发数据

    返回:
        True - 表示此轮循环正常执行（状态机继续在当前状态循环）
    """
    # 获取最新帧（供后续实际解码使用）
    frame = camera.get_frame()
    if frame is not None:
        _ = frame  # 占位，后续替换为实际二维码解码逻辑

    # 向下位机发送检测结果
    serial_comm.send_data_frame(_QR_DATA)

    # 控制发送频率，避免串口拥堵
    time.sleep(0.05)

    return True
