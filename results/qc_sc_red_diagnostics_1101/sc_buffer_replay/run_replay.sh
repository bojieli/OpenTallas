#!/bin/bash
set -euo pipefail
bash run_probe.sh
bash run_readout.sh
printf '0\n' > replay.rc
