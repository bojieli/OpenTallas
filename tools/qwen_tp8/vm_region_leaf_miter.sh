#!/bin/bash
# Region leaf miter runner (RTL-B 2026-10-13).  Runs ON ot-epyc1tb (never localhost):
#   rsync -a --relative rtl/qwen_sys/vm_me_20261008 rtl/qwen_sys/vm_plane_20261013 rtl/qwen_sys/vm_die_split_20261012 \
#         rtl/qwen_sys/rtl_finish_20261007 rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qwen_tree_delay.sv \
#         rtl/physical/ot_qwen_tree_delay_tiles.sv tools/qwen_tp8/vm_region_leaf_miter.sh ot-epyc1tb:~/claude-vm-rtl-1013/b/wt/
#   ssh ot-epyc1tb ot-heavy --mem 48 -- bash ~/claude-vm-rtl-1013/b/wt/tools/qwen_tp8/vm_region_leaf_miter.sh all
# usage: vm_region_leaf_miter.sh all | flops | one <name> [verilator args...] | sys <name> <tile module> [verilator args...]
#   sys = the system bench tb_qfd_vm_bv_ports with the region tile = <tile module> (needs rtl/test/qwen_vm_me; ~24 GB at NRB 64)
# Results: $B/<name>.log, $B/<name>.build.log, $B/summary.txt, $B/flops.txt
R=${VM_RTL_ROOT:-$HOME/claude-vm-rtl-1013/b/wt}; B=${VM_RTL_OUT:-$HOME/claude-vm-rtl-1013/b/out}
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
cd "$R" || exit 9; mkdir -p "$B"
P=rtl/qwen_sys/vm_plane_20261013; S=rtl/qwen_sys/vm_die_split_20261012
SRC="$P/tb_qfd_vm_region_leaf.sv $P/ot_qfd_vm_region_leaf.sv $S/ot_qfd_vm_region_quarter.sv $S/ot_qfd_vm_answer_tiles.sv $S/ot_qfd_vm_xfifo8_t.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv $P/ot_qfd_vm_xplane.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_vector_memory.sv rtl/qwen_sys/rtl_finish_20261007/ot_qfd_sp_tree_top.sv rtl/hdc/ot_hdc_delay.sv rtl/physical/ot_qwen_tree_delay.sv rtl/physical/ot_qwen_tree_delay_tiles.sv"
one() {
    n=$1; shift
    $V --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING \
        -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j 8 --top-module tb_qfd_vm_region_leaf "$@" \
        --Mdir $B/$n $SRC > $B/$n.build.log 2>&1 || { echo "$n BUILD-FAIL"; grep -m5 -i error $B/$n.build.log; return 2; }
    /usr/bin/time -f "maxrss_kb=%M wall=%e" $B/$n/Vtb_qfd_vm_region_leaf > $B/$n.log 2>&1
    echo "$n rc=$? $(grep -E '^(PASS|FAIL)' $B/$n.log | head -1) $(grep maxrss $B/$n.log)"
}
flops() {   # exact flop bits per new leaf at the production shape (module defaults): yosys proc + simplemap, no merging
    for m in ot_qfd_vm_bctl_t ot_qfd_vm_sctl_t ot_qfd_vm_rr4_t ot_qfd_vm_rr2_t ot_qfd_vm_delay1_t ot_qfd_vm_delay2_t; do
        yosys -q -p "read_verilog -sv $P/ot_qfd_vm_region_leaf.sv rtl/hdc/ot_hdc_delay.sv; hierarchy -top $m; proc; flatten; opt_clean; simplemap; tee -o $B/stat_$m.txt stat" > $B/yosys_$m.log 2>&1
        echo "$m flops=$(awk '/DFF/ {for (i = 1; i <= NF; i++) if ($i ~ /^[0-9]+$/) s += $i} END {print s+0}' $B/stat_$m.txt) cells: $(grep -E '\$_[A-Z]*DFF' $B/stat_$m.txt | tr -s ' ' | tr '\n' ';')"
    done
}
sys() {
    n=$1; t=$2; shift 2
    $V --binary --timing -O1 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-PINMISSING \
        -Wno-TIMESCALEMOD -Wno-LATCH -Wno-MULTIDRIVEN -Wno-BLKSEQ -Wno-UNOPTFLAT -j 8 --top-module tb_qfd_vm_bv_ports \
        -GCYCLES=40000 -GTSR=1 -GXQT=1 -GMEE=1 -GVMT=1 +define+OT_QFD_VM_TILE_MOD=$t "$@" --Mdir $B/$n \
        rtl/test/qwen_vm_me/tb_qfd_vm_bv_ports.sv ${SRC#* } > $B/$n.build.log 2>&1 || { echo "$n BUILD-FAIL"; grep -m5 -i error $B/$n.build.log; return 2; }
    /usr/bin/time -f "maxrss_kb=%M wall=%e" $B/$n/Vtb_qfd_vm_bv_ports > $B/$n.log 2>&1
    echo "$n rc=$? $(grep -E '^(PASS|FAIL)' $B/$n.log | head -1 | cut -c1-200) $(grep maxrss $B/$n.log)"
}
case "$1" in
sys) shift; sys "$@" ;;
one) shift; one "$@" ;;
flops) flops | tee $B/flops.txt ;;
all)
    {
    one ok          -GSEED=1 &
    one ok_s2       -GSEED=2 -GOVFMODE=1 &
    one ok_s3_tree  -GSEED=3 +define+OT_QFD_VM_DELAY1_MOD=ot_qwen_tree_delay1_t +define+OT_QFD_VM_DELAY2_MOD=ot_qwen_tree_delay2_t &
    for m in 1 2 3 4 5 6 7 8 9 10 11 12; do one mut$m -GLEAF_MUT=$m & done
    flops > $B/flops.txt &
    wait
    } | sort | tee $B/summary.txt
    cat $B/flops.txt ;;
*) echo "usage: $0 all | flops | one <name> [args]"; exit 1 ;;
esac
