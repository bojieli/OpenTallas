#!/usr/bin/env bash
# DIE-HBM-61/SPLIT split3_lane lock-step: uncut kit core ot_hgi_sfu_split3_lane_core__idpin (kit face shell) vs the
# split composition (_fr__fs + _ex__fs + _bk__fs), declared shift +4 on the _bk outputs (spec.json "shift").
#   run.sh KITRTL OUT      (fleet host; verilator 5).  MUT 0 must PASS; MUT 1 / 2 / 3 must FAIL.
set -u
KR=$1; O=$2; H=$(cd "$(dirname "$0")" && pwd); R=$H/../..
RT=$H/../../../../../../../rtl/hbm_accel/cores_split/reform_1103/ot_hgi_sfu_split3_lane_core__idpin
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p "$O"
LIB=$(ls $KR/*.sv | grep -v -e __fshell -e __wrap -e ot_hgi_sfu_split3_lane_core.sv)
for s in fr bk ex; do PP=--pass-param; PV=MUT; [ $s = ex ] && { PP=; PV=; }
  python3 "$R/facewrap.py" --top ot_hgi_sfu_split3_lane_core_$s --out "$O/${s}__fs.sv" $PP $PV --clk-re '_clk$' --rst-re '_rst_n$' \
    $RT/ot_hgi_sfu_split3_lane_core_$s.sv $LIB > "$O/${s}_ports.json" || exit 1; done
python3 "$R/lockstep_gen.py" "$H/spec.json" "$O/tb.sv"
for M in ${MUTS:-0 1 2 3}; do
  sed "s/ot_hgi_sfu_split3_lane_core__idpin__split u_dut/ot_hgi_sfu_split3_lane_core__idpin__split #(.MUT($M)) u_dut/" "$O/tb.sv" > "$O/tb_m$M.sv"
  rm -rf "$O/obj_m$M"; $V --binary -j 16 -Wno-fatal -Wno-lint -Wno-style --x-initial 0 --top-module tb -Mdir "$O/obj_m$M" -o sim \
    "$O/tb_m$M.sv" $KR/*.sv $RT/*.sv "$O/fr__fs.sv" "$O/ex__fs.sv" "$O/bk__fs.sv" > "$O/build_m$M.log" 2>&1 || { grep -m5 -i error "$O/build_m$M.log"; exit 2; }
  "$O/obj_m$M/sim" > "$O/sim_m$M.log" 2>&1; echo "MUT $M: $(grep LOCKSTEP "$O/sim_m$M.log")"
done
sha256sum $KR/*.sv $RT/*.sv > "$O/sources.sha256"
