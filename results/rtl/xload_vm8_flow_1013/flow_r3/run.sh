#!/bin/bash
# flow_r3 gate for the XW_FLOW held x-write transport.  usage: run.sh <src dir> <out dir>   (on ot-epyc1tb)
set -u
SRC=$1; D=$2
BASE=/srv/opentallas-scratch/codex/xload-vm8-flow-1013/beats.txt
HASH=1c1d69aa905b131e6dd4c11d0a9c2c87c0ae20ab8e78dadc7dd304c16aac5570
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
S='rtl/hbm_accel/generic/peers/ot_hgi_sm_xload.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_wrd.sv rtl/lib/ot_rst_relay.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/proto/ot_fp32_add_rne_pipe.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v rtl/hbm_accel/generic/adapters/tb/tb_xload_cadence.sv'
mkdir -p "$D"; cd "$SRC"
sha256sum $S tools/vm8_service/xload_flow_compare.py > "$D/source.sha256"
build() { # name defines...
  local n=$1; shift
  ot-heavy --mem 8 -- $V --binary --timing -O1 -CFLAGS -O0 -j 4 -Wno-fatal "$@" --top-module tb_xload_cadence --Mdir "$D/obj_$n" $S > "$D/build_$n.log" 2>&1
  echo $? > "$D/build_$n.rc"
}
build base & build flow -DXW_FLOW & build mut_credit -DXW_FLOW -DMUT_XW_CREDIT & build mut_rdpin -DXW_FLOW -DMUT_XW_RDPIN & wait
run() { # name binary cmpflags plusargs...
  local n=$1 b=$2 f=$3; shift 3
  mkdir -p "$D/$n"
  ( cd "$D/$n"; timeout 1500 ot-heavy --mem 2 -- "$D/obj_$b/Vtb_xload_cadence" "$@" > run.log 2>&1; echo $? > run.rc
    python3 -I "$SRC/tools/vm8_service/xload_flow_compare.py" $f --expect-sha256 $HASH "$BASE" beats.txt > compare.json 2> compare.err; echo $? > compare.rc
    sha256sum beats.txt > beats.sha256; rm -f beats.txt )
}
run base_flow0        base       --cycles &
run flow_p1           flow       "" +SINK_PERIOD=1 &
run flow_p13          flow       "" +SINK_PERIOD=13 &
run flow_lfsr_a_half  flow       "" +SINK_LFSR=2463534242 +SINK_BITS=1 &
run flow_lfsr_b_quart flow       "" +SINK_LFSR=88172645 +SINK_BITS=2 &
run flow_lfsr_c_eighth flow      "" +SINK_LFSR=3141592653 +SINK_BITS=3 &
run mut_credit_p13    mut_credit "" +SINK_PERIOD=13 &
run mut_credit_lfsr_a mut_credit "" +SINK_LFSR=2463534242 +SINK_BITS=1 &
run mut_credit_p1     mut_credit "" +SINK_PERIOD=1 &
run mut_rdpin_p13     mut_rdpin  "" +SINK_PERIOD=13 &
run mut_rdpin_lfsr_a  mut_rdpin  "" +SINK_LFSR=2463534242 +SINK_BITS=1 &
run mut_rdpin_p1      mut_rdpin  "" +SINK_PERIOD=1 &
wait
rm -rf "$D"/obj_*
date > "$D/DONE"
