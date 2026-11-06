#!/usr/bin/env bash
# dk.sh NAME args... : run drive.sh in a capped docker container
E=/srv/opentallas-scratch2/claude/hbm-gaps-5-l1p/eq
docker run --rm --name l1p-eq-$1 --memory 16g --cpus 8 -v $HOME/.local/opentallas-tools:$HOME/.local/opentallas-tools:ro -v $E:$E -e HOME=$HOME -e OBJCACHE= -u $(id -u):$(id -g) python:3.12 "$E/drive.sh" "$@"
