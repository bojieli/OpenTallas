#!/bin/bash
set -uo pipefail
unit=$1
root=/srv/opentallas-scratch/claude/codex-qw-n59v3-census-1020
run=$root/$unit
mkdir -p "$run/src"
tar -xzf "$root/source.tgz" -C "$run/src"
cd "$run/src"
printf '%s\n' '5aa523531 + latest helper sync7eb7cfb48 (synth-only exit before phase2)' > SOURCE_COMMIT
export SRC=$run/src SYNTH_TIMEOUT=unlimited OT_SYNTH_TIMEOUT_SECONDS=unlimited
bash tools/ref_tile/n59_synth_only.sh physical/ref_tile/qfd_n59_${unit}2/kit.env census "$run/routes" floorplan
rc=$?
printf 'SYNTH_DRIVER_RC=%s\n' "$rc"
net=$(find "$run/routes/census/work/orfs/results" -name 1_2_yosys.v -print -quit)
if [ ! -s "$net" ]; then echo SYNTH_NO_MAPPED_NETLIST; exit 2; fi
sha256sum "$net" > "$run/netlist.sha256"
python3 tools/textbook_lint.py check --netlist "$net" --top qfd_native59_${unit} --out "$run/textbook_strict.json" --mode refuse --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 > "$run/census.log" 2>&1
crc=$?
printf 'N59_CENSUS_COMPLETE unit=%s synth_rc=%s strict_census_rc=%s\n' "$unit" "$rc" "$crc" | tee "$run/DONE"
exit "$rc"
