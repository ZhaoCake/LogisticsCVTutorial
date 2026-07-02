"""
二维码扫描任务

使用 OpenCV 内置 QRCodeDetector 实时解码摄像头画面中的二维码。
检测结果格式: "XXX+YYY"，其中 X/Y 是 {1,2,3} 的全排列。

在任务状态下持续:
  1. 获取当前帧
  2. 用 QRCodeDetector 解码二维码
  3. 匹配 "123+321" 型格式
  4. 向下位机发送 AA 检测结果 55
"""

import re
import time

import cv2

# 匹配 "123+321" 型格式: 两组三位数，每组是 1,2,3 的全排列
_QR_PATTERN = re.compile(r"^[123]{3}\+[123]{3}$")


def _decode_qr(frame):
    """解码帧中的二维码，返回第一个匹配 "123+321" 型的数据

    使用 OpenCV 的 QRCodeDetector，不需要额外系统库。

    参数:
        frame: OpenCV BGR 图像 (numpy.ndarray)

    返回:
        str 或 None - 匹配的二维码数据
    """
    try:
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(frame)
    except Exception:
        return None

    if not data:
        return None

    # QRCodeDetector 可能返回空字符串
    if _QR_PATTERN.match(data):
        return data

    return None


def run(camera, serial_comm):
    """二维码扫描任务主循环

    参数:
        camera:      Camera 实例，用于获取图像帧
        serial_comm: SerialComm 实例，用于收发数据

    返回:
        True - 表示此轮循环正常执行（状态机继续在当前状态循环）
    """
    frame = camera.get_frame()
    if frame is None:
        return True

    result = _decode_qr(frame)
    if result is not None:
        serial_comm.send_data_frame(result)

    time.sleep(0.05)
    return True
