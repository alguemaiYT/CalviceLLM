#!/bin/bash
MSG="$*"
[[ -z "$MSG" ]] && { echo "Uso: ./client.sh <mensagem>"; exit 1; }

echo "$MSG" | socat -t 15 - UNIX-CONNECT:/tmp/grok_daemon.sock
