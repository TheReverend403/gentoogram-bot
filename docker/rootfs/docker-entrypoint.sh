#!/bin/sh
set -eu

cd /app || exit 1

if ! test -f "$SETTINGS_FILE_FOR_DYNACONF"; then
    echo "Copying default settings.yml"
    cp -au gentoogram/resources/config/settings.yml "$SETTINGS_FILE_FOR_DYNACONF"
fi

exec python -m gentoogram
