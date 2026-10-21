#!/bin/bash
set -euo pipefail
python3 - <<'BIND'
from pathlib import Path
import json,hashlib
for n,sha in json.load(open('readset_sha256.json')).items():
 assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==sha,n
BIND
docker run --rm --memory=8g --cpus=4 --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash map_model.sh > map_docker.log 2>&1
python3 estimate_model.py > estimate.stdout.log
cat estimate.stdout.log
