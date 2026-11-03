#!/bin/bash
set -euo pipefail
printf '%s  input.odb\n' '1e5f74c32f72e7ca965dcccd4c1f5510417b312777884af50db6cf8921f0bceb' | sha256sum -c -
test "$(docker image inspect --format '{{.Id}}' openroad/orfs:asap7lock)" = 'sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
bash run_probe.sh
bash run_readout.sh
printf '0\n' > replay.rc
