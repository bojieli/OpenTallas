#!/bin/bash
# whole-core native: wc_native.sh OUTNAME TOP "DEFINES" [EXTRA_CHPARAM]
set -e
R=/srv/opentallas-scratch/claude/svcatt-1021; S=$R/src; O=$R/$1; T=$2; DEF="$3"
LIB=/srv/opentallas-scratch/claude/elemsvc-g4-1021/out_norst/map/lib
mkdir -p $O
F="/src/rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv /src/rtl/hdc/v41x/ot_hdc_v41x_kreg.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv /src/rtl/hdc/ot_hdc_fastfp.sv /src/rtl/hdc/ot_hdc_fp32_add_lat.sv /src/rtl/hdc/ot_hdc_prefix.sv /src/rtl/hdc/ot_hdc_fp32_f12.sv /src/rtl/hdc/v41x/ot_dsrom_su_add6.sv /src/rtl/hdc/ot_hdc_delay.sv /src/rtl/hdc/ot_hdc_fastfp_lat_f12.sv /src/rtl/hdc/ot_hdc_fp32_mul_lat.sv /src/rtl/hdc/v41x/ot_hdc_v41x_merge_ring_sram.sv /src/rtl/hdc/v41x/ot_hdc_v41x_attn_tr_sram.sv /src/rtl/hdc/v41x/ot_hdc_v41x_stagepick_n32.sv /src/rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_smj_payload_n32.sv /src/rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_pword_pick_n32.sv /src/rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_offset144_n32.sv /src/rtl/dsrom_sys/s81_dv/svc_rs/ot_s81svc_reset132_n32.sv /src/rtl/dsrom_sys/s81_dv/svc_rs/ot_s81svc_reset9_n32.sv /src/rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att_reset9.sv /src/rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv"
case "$DEF" in *OT_F12_ADD5_N32*) NL="read_verilog /src/rtl/hdc/v41x/ot_hdc_fp32_add_f12_l5x_n32.v";; *) NL="";; esac
cat > $O/map.ys <<YS
read_verilog -lib /src/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2_bb.v
read_verilog -lib /src/physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v
read_verilog -lib /hg/ot_s81svc8_hgrp_s81_bounded_bb.v
read_liberty -lib /tmp/lib/SIMPLE.lib
read_liberty -lib /tmp/lib/AO.lib
read_liberty -lib /tmp/lib/OA.lib
read_liberty -lib /tmp/lib/INVBUF.lib
read_liberty -lib /tmp/lib/SEQ.lib
$NL
read_verilog -defer -sv -DSYNTHESIS $DEF -I/src/rtl/dsrom_sys/s81_dv/svc_rs $F
hierarchy -check -top $T -chparam MUT 0 -chparam DIE_ID 0 -chparam ST 0 -chparam SRAM_MACRO 1 -chparam NTP 1 -chparam PMEM 1 -chparam QMEM_SRAM 0
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top $T -flatten -noshare
dfflibmap -liberty /tmp/lib/SEQ.lib
abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
opt_clean
setattr -mod -unset keep_hierarchy
flatten
opt_clean
tee -o /out/stat_flat.txt stat -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib
write_verilog -noattr /out/flat.v
write_json /out/flat.json
YS
HG=$(dirname $(ls /srv/opentallas-scratch/claude/elemsvc-g4-1021/src_norst/tools/s81_dv/svc_rs/attn1/ot_s81svc8_hgrp_s81_bounded_bb.v))
docker run --rm -v "$S:/src:ro" -v "$HG:/hg:ro" -v "$O:/out" -v "$LIB:/tmp/lib:ro" openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /out/synth.log -s /out/map.ys' > $O/build.log 2>&1 || { echo SYNTH_FAIL; tail -30 $O/synth.log; exit 1; }
args=(); for f in $LIB/*.lib; do args+=(--liberty $f); done
python3 $R/tools/ref_tile/native_census.py --netlist $O/flat.v --top $T --out $O/census.json "${args[@]}" > $O/census.log 2>&1 || true
cat $O/census.log
python3 $R/attrib.py $O/flat.v $O/census.json $O/attrib.json > $O/attrib.log 2>&1 || true
head -60 $O/attrib.log
