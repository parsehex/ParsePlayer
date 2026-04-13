#!/bin/bash

HOST="raspberrypi"

# this assumes that there's a host named "raspberrypi" in your ssh config
# requires watchman-make: https://facebook.github.io/watchman/docs/install.html

watchman-make -p '**/*' --run "rsync -avz \
	--exclude '.git' \
	--exclude 'venv/' \
	--exclude '.venv/' \
	. ${HOST}:~/ParsePlayer/"
