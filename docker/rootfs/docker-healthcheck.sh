#!/bin/sh
set -eu

curl -sSL "https://api.telegram.org/bot$DYNACONF_TELEGRAM__TOKEN/getMe"
