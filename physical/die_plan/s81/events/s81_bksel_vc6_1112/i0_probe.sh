#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/die-s81-85/bksel_vC8e
P=/srv/opentallas-scratch2/claude/die-s81-85/i0_hop_probe
sudo docker run --rm --memory 8g --memory-swap 8g --cpus 2 -v "$K":/work:ro -v "$P":/out openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /out/i0_probe.tcl
