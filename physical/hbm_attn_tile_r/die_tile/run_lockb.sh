#!/bin/bash
# run_lockb.sh <outdir> <pos|neg> [-G stage params]: hfd_attn_tile_b lockstep vs the quad parent (rtl/test/tb_hfd_attn_tile_b.sv),
# pos = roles 0..3 must PASS, neg = role 0 with NEG=1 must FAIL.  Verilator 5.050 (fleet).
O=$1; M=$2; shift 2; mkdir -p $O
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC="rtl/test/tb_hfd_attn_tile_b.sv rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv rtl/hdc/v41x/ot_hdc_v41x_attn_bank.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m6h1r.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_m8_phys.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/test/hdc_v41_harness.cpp"
run() { t=$1; shift
  $V --cc --exe --build -j ${J:-8} -O1 -CFLAGS -O1 -MAKEFLAGS OPT_SLOW=-O0 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-PINMISSING --top-module tb_hfd_attn_tile_b --prefix Vtb -Mdir $O/$t "$@" $SRC > $O/$t.log 2>&1 && $O/$t/Vtb > $O/$t.run 2>&1; echo "$t rc=$?" >> $O/rc_$M.txt; }
: > $O/rc_$M.txt
if [ "$M" = neg ]; then run n0 -GROLE=0 -GNEG=1 "$@"; else for r in 0 1 2 3; do run r$r -GROLE=$r "$@" & done; wait; fi
grep -h ATTNDIE $O/*.run | sort | uniq
if grep -q "rc=[1-9]" $O/rc_$M.txt; then echo "ATTN_LOCKB FAIL"; exit 1; fi
echo "ATTN_LOCKB PASS"
