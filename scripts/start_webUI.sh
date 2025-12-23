#!/bin/bash

export UV_PROJECT_ENVIRONMENT=~/.nc4touch_uv_env
sudo pigpiod
cd /mnt/shared/code/NC4Touch
~/.local/bin/uv run Controller/WebUI.py
