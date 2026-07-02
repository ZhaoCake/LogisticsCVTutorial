#!/bin/bash
# ─────────────────────────────────────────────────────────
# 向下位机端虚拟串口发送命令，模拟电控发来的协议帧
#
# 协议格式: AA <CMD> 55
#
# 命令码:
#   C0  →  AA C0 55  →  空闲
#   C1  →  AA C1 55  →  扫描二维码
#   C2  →  AA C2 55  →  颜色检测
#   C3  →  AA C3 55  →  圆环检测
#
# 用法:
#   ./send_cmd.sh C1          # 发送扫描二维码命令
#   TTY=/tmp/ttyV0 ./send_cmd.sh C2   # 指定串口路径
#
# 环境变量:
#   TTY: 串口路径，默认为 /tmp/ttyV0（下位机端）
# ─────────────────────────────────────────────────────────

TTY="${TTY:-/tmp/ttyV0}"

# 检查串口是否存在
if [ ! -e "$TTY" ]; then
    echo "错误: 串口 $TTY 不存在!"
    echo "请先运行: ./scripts/setup_virtual_serial.sh"
    exit 1
fi

case "$1" in
    C0)
        echo "发送命令: C0 (空闲)"
        printf '\xAA\xC0\x55' > "$TTY"
        ;;
    C1)
        echo "发送命令: C1 (扫描二维码)"
        printf '\xAA\xC1\x55' > "$TTY"
        ;;
    C2)
        echo "发送命令: C2 (颜色检测)"
        printf '\xAA\xC2\x55' > "$TTY"
        ;;
    C3)
        echo "发送命令: C3 (圆环检测)"
        printf '\xAA\xC3\x55' > "$TTY"
        ;;
    *)
        echo "用法: $0 {C0|C1|C2|C3}"
        echo ""
        echo "命令说明:"
        echo "  C0  空闲"
        echo "  C1  扫描二维码"
        echo "  C2  颜色检测"
        echo "  C3  圆环检测"
        exit 1
        ;;
esac

echo "    串口: $TTY"
echo "    字节: AA $1 55"
