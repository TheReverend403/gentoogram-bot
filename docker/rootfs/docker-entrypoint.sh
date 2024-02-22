#!/bin/sh
set -eu

if [ -z "$(find "${ROOT_PATH_FOR_DYNACONF}" -type f -mindepth 1 -maxdepth 1)" ]; then
    echo "Copying default settings.yml to ${ROOT_PATH_FOR_DYNACONF}"
    cp -au "gentoogram/resources/config/settings.yml" "${ROOT_PATH_FOR_DYNACONF}"
fi

exec python -m gentoogram
