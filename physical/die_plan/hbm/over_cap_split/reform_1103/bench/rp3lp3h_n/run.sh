#!/usr/bin/env bash
# DIE-HBM-61/SPLIT rp3lp3h lock-step benches (fleet host, verilator 5):
#   run.sh nx KITRTL_N KITRTL_S SRAM_MODEL OUT   pair N + S: kit cores vs split compositions (proves the n split; MUT on n)
#   run.sh s  KITRTL_N KITRTL_S SRAM_MODEL OUT   S half alone: kit core vs split composition
# Kit VERILOG_DEFINES (SYNTHESIS form = the built netlist); SRAM = behavioural model of ot_sram_1r1w_128x256_m1_r2c2
# (physical/asap7_memory_macros/...), kit blackbox views excluded.  MUT 0 must PASS; MUT 1, 2, 3 must FAIL.
set -u
MODE=$1; KN=$2; KS=$3; SM=$4; O=$5
H=$(cd "$(dirname "$0")" && pwd); R=$H/../..; RT=$H/../../../../../../../rtl/hbm_accel/cores_split/reform_1103/hnx_rp3lp3h
V=${VERILATOR:-$HOME/.local/opentallas-tools/bin/verilator}; mkdir -p "$O"
DEFS="SYNTHESIS OT_SMH_CG_ENREG OT_SMH_XLK OT_FP_DATA_NORST OT_SMH_DRST0 OT_SMH_RSTRELAY OT_SMH_RSTPIN OT_SMH_HIER OT_SMH_PTW_OHDLY OT_SMH_PINREG OT_SMH_XREL OT_SMH_PRODUCTION_SHAPE OT_SMH_COMPACT_PT OT_SMH_GROUP_TRANSPORT OT_SMH_WEST_SPLIT OT_SMH_TRANSPORT_KEEP OT_SMH_RP4_SRST"
FD=$(for d in $DEFS; do printf -- '-D %s ' $d; done); VD=$(for d in $DEFS; do printf -- '+define+%s ' $d; done)
# shared leaf RTL (n kit; identical files in the s kit except hnx_rp3lp3h.sv + fshells)
LIB=$(ls $KN/*.sv | grep -v -e '/hnx_rp3lp3h.sv$' -e '__fshell.sv$')
SPL=$RT/hnx_rp3h_split.sv
for t in xs lc gn gs; do python3 "$H/facewrap_proc.py" --top hnx_rp3h_$t --out "$O/${t}__fs.sv" --pass-param MUT $FD $SPL > "$O/${t}_ports.json" || exit 1; done
python3 "$H/facewrap_proc.py" --top hnx_rp3h_tl --out "$O/tl__fs.sv" $FD $SPL > "$O/tl_ports.json" || exit 1
if [ "$MODE" = nx ]; then SPEC=$H/spec.json; TBW=$H/tbw.sv; DUTW=tbw_dut_nx; else SPEC=$H/../rp3lp3h_s/spec.json; TBW=$H/../rp3lp3h_s/tbw.sv; DUTW=tbw_dut_s; fi
python3 "$R/lockstep_gen.py" "$SPEC" "$O/tb.sv"
# ref cores: the kit n fshell + n fcore (n kit hnx_rp3lp3h.sv) and the kit s fshell + s fcore (s kit hnx_rp3lp3h.sv)
# (the two hnx_rp3lp3h.sv differ only in which half is the __fcore): build the ref S from a renamed copy of the s kit file
sed -e 's/\bhnx_rp3lp3h_n\b/hnx_rp3lp3h_n__skit_unused/; s/\bhnx_rp3x_halves\b/hnx_rp3x_halves__skit_unused/' $KS/hnx_rp3lp3h.sv \
  | awk '/^module hnx_rp3lp3h_s__fcore/{p=1} p{print} /^endmodule/{if(p){exit}}' > "$O/ref_s_fcore.sv"
awk '/^module hnx_rp3lp3h_n__fcore/{p=1} p{print} /^endmodule/{if(p){exit}}' $KN/hnx_rp3lp3h.sv > "$O/ref_n_fcore.sv"
REF="$KN/hnx_rp3lp3h_n__fshell.sv $KS/hnx_rp3lp3h_s__fshell.sv $O/ref_n_fcore.sv $O/ref_s_fcore.sv"
for M in ${MUTS:-0 1 2 3}; do
  sed "s/$DUTW u_dut/$DUTW #(.MUT($M)) u_dut/" "$O/tb.sv" > "$O/tb_m$M.sv"
  rm -rf "$O/obj_m$M"; $V --binary -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN $VD --top-module tb -Mdir "$O/obj_m$M" -o sim \
    "$O/tb_m$M.sv" $TBW $REF $LIB $SM $H/cells_sim.sv $SPL $RT/hnx_rp3lp3h_n__split.sv $RT/hnx_rp3lp3h_s__split.sv $O/*__fs.sv > "$O/build_m$M.log" 2>&1 || { grep -m5 Error "$O/build_m$M.log"; exit 2; }
  "$O/obj_m$M/sim" > "$O/sim_m$M.log" 2>&1; echo "$MODE MUT $M: $(grep -m1 LOCKSTEP "$O/sim_m$M.log") $(grep -c MISMATCH "$O/sim_m$M.log") mm-lines"
done
sha256sum $REF $LIB $SM $SPL $RT/*.sv $TBW $SPEC > "$O/sources.sha256"
