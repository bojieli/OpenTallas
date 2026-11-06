#!/usr/bin/env bash
set -euo pipefail
base=/srv/opentallas-scratch2/claude/codex-tx-ff-p37-1106
kit=$base/generated/ot_pdie_serdes_tx_c77a41179db8-FF
out=$base/lec_isolated
mkdir "$out"
sha256sum "$kit/run/results/asap7/hbc_ot_pdie_serdes_tx/base/1_2_yosys.v" "$kit/lec.py" "$kit/freeze.json" "$kit/rtl/ot_s81_kp4_enc_la.sv" "$kit/rtl/ot_pdie_serdes_tx__fshell.sv" > "$out/input.sha256"
# The fresh generated kit, its exact mapped netlist, and source fixture are read-only.
# Only /out is writable; this is independent of any physical-flow container.
rc=0
sudo docker run --rm --name "txff-p37-lec-$PPID" --cpus=4 --memory=48g --memory-swap=48g \
 -v "$kit:/work:ro" -v "$out:/out" -w /work openroad/orfs:asap7lock \
 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v python3 -I /work/lec.py /work --netlist /work/run/results/asap7/hbc_ot_pdie_serdes_tx/base/1_2_yosys.v --out /out' || rc=$?
sudo chown -R "$(id -u):$(id -g)" "$out"
printf "%s\n" "$rc" > "$out/exit.rc"
exit "$rc"
