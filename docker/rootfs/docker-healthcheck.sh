#!/bin/sh
set -eu

curl -sSL "https://api.telegram.org/bot${CFG_TELEGRAM__TOKEN}/getMe"
