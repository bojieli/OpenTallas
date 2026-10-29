#!/bin/bash
S=/srv/opentallas-scratch2/claude
docker run --rm --name tok-qwen-6-hp$1 --memory 4g --cpus 1 -u $(id -u):$(id -g) -e HOME=/tmp -e PYTHONPATH=$S/tok-qwen-6-1029/pylib -v $S/tok-qwen-6-1029/time_shim:/usr/bin/time:ro -v $S/wt/tok-qwen-6:$S/wt/tok-qwen-6 -v /home/ubuntu/OpenTallas/.git:/home/ubuntu/OpenTallas/.git:ro -v $S/die-kv-23-1028/bind7:$S/die-kv-23-1028/bind7:ro -v $S/tok-qwen-6-1029:$S/tok-qwen-6-1029 python:3.12 bash $S/tok-qwen-6-1029/hp/probe.sh $1
