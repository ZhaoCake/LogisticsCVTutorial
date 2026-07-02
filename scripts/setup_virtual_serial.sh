#!/bin/bash
# ─────────────────────────────────────────────────────────
# 创建虚拟串口对，用于调试视觉与下位机通信
#
# 创建一对通过 socat 连接的虚拟串口:
#   /tmp/ttyV0  ←→  /tmp/ttyV1
#
# 使用方式:
#   ttyV0 当作"下位机端": 用 send_cmd.sh 往这里写
#   ttyV1 当作"视觉端":   视觉程序连接这个口
#
# 用法:
#   ./setup_virtual_serial.sh
# ─────────────────────────────────────────────────────────

SOCAT_PID_FILE="/tmp/socat_virtual_serial.pid"

# 检查是否已有 socat 进程在运行
if [ -f "$SOCAT_PID_FILE" ]; then
    OLD_PID=$(cat "$SOCAT_PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "检测到 socat 已在运行 (PID: $OLD_PID)，先停止..."
        kill "$OLD_PID" 2>/dev/null
        sleep 0.5
    fi
    rm -f "$SOCAT_PID_FILE"
fi

echo "创建虚拟串口对..."
echo "  下位机端: /tmp/ttyV0"
echo "  视觉端:   /tmp/ttyV1"
echo ""

# 启动 socat，创建双向虚拟串口对
socat -d -d \
    pty,raw,echo=0,link=/tmp/ttyV0 \
    pty,raw,echo=0,link=/tmp/ttyV1 &

SOCAT_PID=$!
echo "$SOCAT_PID" > "$SOCAT_PID_FILE"

sleep 1

echo ""
echo "虚拟串口已创建!"
echo "  下位机端: /tmp/ttyV0  ←→  视觉端: /tmp/ttyV1"
echo "  socat PID: $SOCAT_PID"
echo ""
echo "调试步骤:"
echo "  1. 在一个终端运行: python main.py"
echo "  2. 在另一个终端运行: ./scripts/send_cmd.sh C1"
echo "  3. 查看视觉回复:    ./scripts/monitor_reply.sh"
echo ""
echo "停止: kill $SOCAT_PID"
