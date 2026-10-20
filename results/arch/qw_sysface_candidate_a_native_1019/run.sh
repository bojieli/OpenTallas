#!/bin/bash
set -euo pipefail
mkdir -p receipts
date -u > receipts/start.txt
hostname > receipts/host.txt
docker image inspect sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 > receipts/image_inspect.json
find . -maxdepth 2 -type f -not -path './receipts/*' -print0 | sort -z | xargs -0 sha256sum > receipts/inputs.sha256
docker run --rm -v "$PWD:/work" -w /work sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash map_component.sh
date -u > receipts/map_end.txt
