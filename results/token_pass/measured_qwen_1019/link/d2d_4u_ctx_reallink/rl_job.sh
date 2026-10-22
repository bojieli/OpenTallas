#!/bin/bash
# TOKSIM-QW/LINK 10-19: c92c2be9d real-link MU context transport bench (tb f8f2d2f9a) re-run on qw-gen3 e9879afda production sources.
cd "$(dirname "$0")"; export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; $VERILATOR --version
bash rtl/test/qwen_split/run_mu_context_real_link.sh out 0 1 2 3 4 5 full; echo "rc=$?"
for d in out/*/; do echo "== $d"; grep -E '^MUCTX_(REAL_LINK|FULL|SLOT|HOST_TX|WIRE|LOAD|END)' $d/run.log | head -40; done; echo RL_JOB_DONE
