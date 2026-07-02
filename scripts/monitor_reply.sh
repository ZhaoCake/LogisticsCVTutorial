#!/bin/bash
# 串口监视工具 - 直接用 cat 查看视觉端回复的原始字节
# 用法: ./monitor_reply.sh
# 注意: 二进制数据会直接打到终端，可能乱码，建议配合 xxd/od 使用

TTY="${TTY:-/tmp/ttyV0}"

if [ ! -e "$TTY" ]; then
    echo "错误: 串口 $TTY 不存在!"
    exit 1
fi

echo "正在监视 $TTY ... (Ctrl+C 退出)"
stty -F "$TTY" raw -echo 2>/dev/null
cat "$TTY"
