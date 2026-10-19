#!/bin/bash
set -euo pipefail
mkdir -p out
docker image inspect openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 --format '{{.Id}} {{json .RepoDigests}}' >out/image.txt
docker run --rm --network none -v "$PWD:/work" -w /work openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash tools/hbm_hidx_coupon1/map.sh
for step in sta_runner formal_mapped strict_runner finalize path_runner pack; do
 (cd out; bash ../tools/hbm_hidx_coupon1/$step.sh)
done
