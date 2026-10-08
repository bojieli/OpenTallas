#!/bin/bash
set -o pipefail
L=${1:?label}; shift
S=${SRC:-.}; O=${OUT:?out}/$L
mkdir -p "$O"
cd "$S" || exit 1
export OT_ORFS_NUM_CORES=16
export OPENTALLAS_ORFS_IMAGE=${OPENTALLAS_ORFS_IMAGE:-sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29}
SS=${CK_SS_MEAN:-1137}
printf 'candidate=bf_root_phase baseline=61c1cf230 measured_ss=%s\n' "$SS" > "$O/MANIFEST"
python3 tools/s81/run_bf_root_phase_physical.py --half --margin --wc-only --hitfix --period .730 --work "$O/work" --output "$O/physical.json" --util 45 --tag "$L" --ins-ss "$SS" --ins-ff "$SS" --extra="$*" > "$O/run.log" 2>&1
rc=$?
printf 'rc=%s\n' "$rc" > "$O/exit"
if [ "$rc" -eq 0 ] && [[ " $* " != *"--pnr-stop-after"* ]]; then
  python3 tools/w18/corner_sta.py --orfs-dir "$O/work/orfs" --macro physical/asap7_memory_macros_v2/ot_rom_4096x274_m8 --post-sdc physical/s81_bf_root_phase/clock.sdc --post-sdc physical/s81_bf_root_phase/signoff_ref.sdc --post-sdc physical/s81_bf_root_phase/half_mc.sdc --output "$O/corner_sta.json" > "$O/sta.log" 2>&1
  printf 'corner_rc=%s\n' "$?" >> "$O/exit"
fi
exit "$rc"
