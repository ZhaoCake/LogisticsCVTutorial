"""
协议层 - 定义通信协议的常量、帧解析与组帧功能

通信协议格式:
  下位机 -> 视觉:  AA CMD 55
  视觉 -> 下位机:  CC (应答，无帧头帧尾)
  视觉 -> 下位机:  AA DATA_STRING 55 (任务数据，带帧头帧尾)

命令码:
  0xC0  IDLE       空闲/停止当前任务
  0xC1  SCAN_QR    扫描二维码任务
  0xC2  DETECT_COLOR  颜色检测任务
  0xC3  DETECT_CIRCLE 圆环检测任务
"""

# ── 协议常量 ──────────────────────────────────────────────
FRAME_HEADER = 0xAA   # 帧头
FRAME_TAIL  = 0x55   # 帧尾
ACK         = 0xCC   # 应答字节

# 命令码
CMD_IDLE    = 0xC0   # 空闲命令
CMD_QR      = 0xC1   # 二维码扫描命令
CMD_COLOR   = 0xC2   # 颜色检测命令
CMD_CIRCLE  = 0xC3   # 圆环检测命令

# 命令码 → 名称映射，用于日志和调试
CMD_NAMES = {
    CMD_IDLE:    "IDLE",
    CMD_QR:      "SCAN_QR",
    CMD_COLOR:   "DETECT_COLOR",
    CMD_CIRCLE:  "DETECT_CIRCLE",
}


def parse_frame(buffer: bytearray):
    """从字节缓冲区中提取一帧数据

    从缓冲区头部开始搜索 AA ... 55 模式:
      1. 找到第一个 AA
      2. 继续读取直到遇到 55
      3. 返回 (命令码, 负载数据字节) 并移除已消耗的字节
      4. 如果 AA 后面紧跟的字节就是 55 则表示空数据帧
      5. 如果找不到完整帧则返回 None

    参数:
        buffer: 字节缓冲区（会原地修改，移除已处理的字节）

    返回:
        (cmd, payload) 元组，或 None（帧不完整或无效）
    """
    while len(buffer) >= 2:
        # 查找帧头
        header_idx = -1
        for i, b in enumerate(buffer):
            if b == FRAME_HEADER:
                header_idx = i
                break

        # 没找到帧头，清空缓冲区
        if header_idx == -1:
            buffer.clear()
            return None

        # 丢弃帧头前面的无效字节
        if header_idx > 0:
            del buffer[:header_idx]
            header_idx = 0

        # 需要至少 3 个字节: AA CMD 55
        if len(buffer) < 3:
            return None

        # 帧头后面至少有一个命令字节，查找帧尾 55
        tail_idx = -1
        for i in range(1, len(buffer)):
            if buffer[i] == FRAME_TAIL:
                tail_idx = i
                break

        # 没找到帧尾，等待更多数据
        if tail_idx == -1:
            return None

        # 帧头后面第一个字节是命令码
        cmd = buffer[1]

        # 命令码和数据之间的字节是负载
        payload = bytes(buffer[2:tail_idx])

        # 移除已处理的帧（包括帧头帧尾之间的所有字节 + 帧尾本身）
        del buffer[:tail_idx + 1]

        return cmd, payload

    return None


def build_data_frame(data_str: str):
    """构建数据帧

    将字符串数据包装为: AA + data.encode() + 55

    参数:
        data_str: 要发送的字符串数据

    返回:
        bytes: 完整的帧数据
    """
    return bytes([FRAME_HEADER]) + data_str.encode("ascii") + bytes([FRAME_TAIL])
