#!/usr/bin/env bash
set -euo pipefail
cd /srv/opentallas-scratch2/claude/codex-rx-bm3-native-1106
sudo docker run --rm --name "rx-bm3-proof-$PPID" --memory=8g --memory-swap=8g --cpus=2 -u "$(id -u):$(id -g)" -v "$PWD:/work" -v "$HOME/.local/opentallas-tools:$HOME/.local/opentallas-tools:ro" -e HOME="$HOME" -e OBJCACHE= -w /work/proof python:3.12 bash -c '$HOME/.local/opentallas-tools/bin/verilator --binary -j 2 -Wno-fatal --top-module tb -I/work/rtl -Mdir obj -o sim tb.sv helper.sv /work/rtl/ot_s81_kp4_bm.sv /work/rtl/ot_s81_kp4_common.sv > build.log 2>&1;for mode in 0 1 2 3;do ./obj/sim +MUT=$mode > mode${mode}.log 2>&1 || exit $?;done'
printf 'ALL_COHORT_PASS\n' > proof/result.txt
