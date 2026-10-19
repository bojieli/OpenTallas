#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir out
img=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker image inspect "$img" > out/docker_inspect.json
test "$(docker image inspect "$img" --format '{{.Id}}')" = sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
hostname > out/host.txt
date -Is > out/start.txt
free -b > out/free_before.txt
df -B1 . > out/disk_before.txt
/usr/bin/time -v -o out/resources.txt docker run --rm --cpus 8 -v "$PWD:/src:ro" -v "$PWD/out:/work" "$img" bash /src/inside.sh
free -b > out/free_after.txt
df -B1 . > out/disk_after.txt
du -sb out > out/scratch_bytes.txt
date -Is > out/finish.txt
