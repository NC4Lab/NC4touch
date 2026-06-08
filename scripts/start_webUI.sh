#!/bin/bash

set -euo pipefail

export UV_PROJECT_ENVIRONMENT=~/.nc4touch_uv_env

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

screen_on() {
	if command -v xset >/dev/null 2>&1; then
		xset s off -dpms s noblank >/dev/null 2>&1 || true
		xset dpms force on >/dev/null 2>&1 || true
	fi
}

screen_off() {
	if command -v xset >/dev/null 2>&1; then
		xset dpms force off >/dev/null 2>&1 || true
	fi
}

cleanup() {
	screen_off
}

trap cleanup EXIT INT TERM

screen_on
sudo pigpiod
cd /mnt/shared/code/NC4Touch
~/.local/bin/uv run Controller/WebUI.py
