#!/bin/bash
# Qwen TP8 VM leaf gates at the ROUTED parameters of the closed leaves (2026-10-13 VERIF).  ONE run; from the repo root
# of any source snapshot (a closure-loop job's {RUN} tree, or a synced tree on a build host; never localhost):
#   tools/qwen_tp8/vm_leaf_gate.sh <outdir> <kind> <name> [verilator args ...]
# kinds
#   xplane   tb_qfd_vm_xplane at NRB 64 / ELEMS 177,808 / XPR 10: 32 x ot_qfd_vm_xplane_t (NRB 64, the routed
#            parameter) behind 10 x 64 ot_qfd_vm_xrelay_t (W 512, routed) against the parent's flat rot1 / rot2 / bv.
#            Mutants: -GPMUT=1|2|3 (plane 5 fine rotation / element shift / range count: the parent's MUT 5, which the
#            system bench cannot see), -GRMUT=1 (one relay free-runs).
#   xplane16 the same bench at the bench shape NRB 16 / ELEMS 16,384 (the committed leaf_miter record's shape).
#   region   tb_qfd_vm_region_leaf at DEPTH 174 / LAW 8 / DEPTHS 695 / LAWS 10 with the delay leaves bound to the
#            ROUTED delay tiles ot_qwen_tree_delay1_t / delay2_t: ot_qfd_vm_region_leaf (8 x bctl_t, 6 x sctl_t, 2 x rr4_t,
#            rr2_t, 8 x bank_t, 6 x su_t, 16 x xfifo8_t, 3 x su1024_t, delay tiles) against the flat
#            ot_qfd_vm_region_quarter, every clock.  Mutants: -GLEAF_MUT=1 / 2 (rr4_t) 3 / 9 / 11 (bctl_t) 8 / 10 (sctl_t)
#            7 / 12 (rr2_t) 4 (bank_t 5's write-data pin: delay1 for delay2) 5 (bank 2's q relay) 6 (su_t's write-data
#            pin), -GROW_MUT=1 (rr2_t half select), -GSU_MUT=1 (su1024_t).
#   region8  the same bench at the bench shape (DEPTH 8 / LAW 3, soft delay leaves): the committed record's shape.
# Prints "<name> rc=<rc> <PASS|FAIL line> maxrss_kb=.. wall=.. build_s=.." and exits 0 on a PASS line, 1 on a FAIL
# line, 2 when the build failed or no verdict line was printed (a build failure is never a killed mutant).
out=$1; kind=$2; n=$3; shift 3
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$V" ] || V=verilator
P=rtl/qwen_sys/vm_plane_20261013; S=rtl/qwen_sys/vm_die_split_20261012
mkdir -p "$out"; rm -rf "$out/$n" "$out/$n.log" "$out/$n.build.log"
W="-Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT"
RSRC="$P/tb_qfd_vm_region_leaf.sv $P/ot_qfd_vm_region_leaf.sv $S/ot_qfd_vm_region_quarter.sv $S/ot_qfd_vm_answer_tiles.sv $S/ot_qfd_vm_xfifo8_t.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv $P/ot_qfd_vm_xplane.sv $P/ot_qfd_vm_xtree.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qwen_tree_delay.sv rtl/physical/ot_qwen_tree_delay_tiles.sv"
case "$kind" in
xplane)   top=tb_qfd_vm_xplane; A="-GNRB=64 -GELEMS=177808"; SRC="$P/tb_qfd_vm_xplane.sv $P/ot_qfd_vm_xplane.sv" ;;
xplane16) top=tb_qfd_vm_xplane; A="-GNRB=16 -GELEMS=16384"; SRC="$P/tb_qfd_vm_xplane.sv $P/ot_qfd_vm_xplane.sv" ;;
region)   top=tb_qfd_vm_region_leaf; SRC=$RSRC
          A="-GDEPTH=174 -GLAW=8 -GDEPTHS=695 -GLAWS=10 -GCYCLES=20000 +define+OT_QFD_VM_DELAY1_MOD=ot_qwen_tree_delay1_t +define+OT_QFD_VM_DELAY2_MOD=ot_qwen_tree_delay2_t" ;;
region8)  top=tb_qfd_vm_region_leaf; SRC=$RSRC; A="" ;;
*) echo "usage: $0 <outdir> xplane|xplane16|region|region8 <name> [verilator args]"; exit 2 ;;
esac
t0=$(date +%s)
# shellcheck disable=SC2086
$V --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 $W -j 8 --top-module $top $A "$@" \
   --Mdir "$out/$n" $SRC > "$out/$n.build.log" 2>&1 \
   || { echo "$n BUILD-FAIL $(grep -m1 -E 'Error|terminated|Killed' "$out/$n.build.log" | cut -c1-160)"; exit 2; }
t1=$(date +%s)
/usr/bin/time -f "maxrss_kb=%M wall=%e" "$out/$n/V$top" > "$out/$n.log" 2>&1; rc=$?
line=$(grep -E '^(PASS|FAIL) ' "$out/$n.log" | head -1 | cut -c1-260)
echo "$n rc=$rc $line $(grep -E '^maxrss_kb=' "$out/$n.log" | tail -1) build_s=$((t1 - t0))"
case "$line" in PASS*) exit 0 ;; FAIL*) exit 1 ;; *) exit 2 ;; esac
