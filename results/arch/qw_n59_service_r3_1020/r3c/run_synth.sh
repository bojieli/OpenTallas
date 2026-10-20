#!/bin/bash
set -uo pipefail
root=/srv/opentallas-scratch/claude/qw-cb16a0-n59r3c-1020
run=$root/synth_recv
mkdir -p "$run/src"
tar -xzf /srv/opentallas-scratch/claude/codex-qw-n59v3-census-1020/source.tgz -C "$run/src"
tar -xzf "$root/source.tgz" -C "$run/src"
tar -xzf "$root/overlay.tgz" -C "$run/src"
cd "$run/src"
printf '%s\n' 'f03c8a431 R3c + R2 archive + helper7eb7cfb48 synthesis-only' > SOURCE_COMMIT
printf '\nPARAMS+=(--param RECV_INPUTS=1 --param LOCAL32=1)\n' >> physical/ref_tile/qfd_n59_svc2/kit.env
export SRC=$run/src SYNTH_TIMEOUT=unlimited OT_SYNTH_TIMEOUT_SECONDS=unlimited
bash tools/ref_tile/n59_synth_only.sh physical/ref_tile/qfd_n59_svc2/kit.env census "$run/routes" floorplan
rc=$?
n=$(find "$run/routes/census/work/orfs/results" -name 1_2_yosys.v -print -quit)
test -s "$n" || exit 2
sha256sum "$n" > "$run/netlist.sha256"
sha256sum rtl/qwen_split/qfd_native59_svc.sv physical/ref_tile/qfd_n59_svc2/kit.env > "$run/source.sha256"
python3 tools/textbook_lint.py check --netlist "$n" --top qfd_native59_svc --out "$run/textbook_strict.json" --mode refuse --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 > "$run/census.log" 2>&1
crc=$?
python3 "$root/native_extra.py" tools "$n" qfd_native59_svc "$run/native_extra.json" > "$run/extra.log" 2>&1
python3 "$root/target_audit.py" tools "$n" "$run/target_audit.json" > "$run/target_audit.log" 2>&1
printf 'N59_V6_SYNTH_DONE synth_rc=%s census_rc=%s\n' "$rc" "$crc" | tee "$run/DONE"
exit "$rc"
