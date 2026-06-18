#!/bin/bash

set -euo pipefail

export UV_PROJECT_ENVIRONMENT=~/.nc4touch_uv_env

if ! pgrep -x pigpiod >/dev/null 2>&1; then
	if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
		pigpiod
	elif command -v sudo >/dev/null 2>&1; then
		sudo pigpiod
	fi
fi

cd /mnt/shared/code/NC4Touch
exec ~/.local/bin/uv run Controller/WebUI.py
