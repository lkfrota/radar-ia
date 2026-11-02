#!/usr/bin/env bash
# Instala o agendamento diário (6h) da coleta local do The Batch no systemd do usuário.
# Persistent=true: se o computador estava desligado às 6h, roda ao ligar.
# Para desinstalar: systemctl --user disable --now radar-batch.timer && rm ~/.config/systemd/user/radar-batch.*
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p ~/.config/systemd/user
cp "$DIR/systemd/radar-batch.service" "$DIR/systemd/radar-batch.timer" ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now radar-batch.timer
systemctl --user start radar-batch.service   # primeira coleta agora, como teste
sleep 20
systemctl --user status radar-batch.service --no-pager | tail -5 || true
systemctl --user list-timers radar-batch.timer --no-pager
