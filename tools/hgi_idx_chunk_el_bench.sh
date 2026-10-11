#!/bin/bash
# hgi-1010/g2: lockstep bench of the indexer chunk ELEMENT (ot_hdc_v41x_idx_chunk_el) vs the parameterised chunk.
# usage: hgi_idx_chunk_el_bench.sh <out> [+MUT_HB]   (run from the source root; prints HGI_IDX_CHUNK_EL PASS / FAIL)
set -u
O=$1; P=${2:-}; mkdir -p $O
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x $VL ] || VL=verilator
S="rtl/hdc/v41x/ot_hdc_v41x_idx_chunk_el.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv"
if [ ! -x $O/obj/Vtb_hgi_idx_chunk_el ]; then
 $VL --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-PINMISSING \
  --top-module tb_hgi_idx_chunk_el -Mdir $O/obj $S rtl/test/hbm_idx_chunk_el/tb_hgi_idx_chunk_el.sv -j 16 > $O/build.log 2>&1 \
  || { tail -20 $O/build.log; echo HGI_IDX_CHUNK_EL BUILD_FAIL; exit 2; }
fi
$O/obj/Vtb_hgi_idx_chunk_el $P > $O/run$P.log 2>&1; grep -m5 ERR $O/run$P.log; grep 'summary\|HGI_IDX_CHUNK_EL' $O/run$P.log
grep -q "HGI_IDX_CHUNK_EL PASS" $O/run$P.log
