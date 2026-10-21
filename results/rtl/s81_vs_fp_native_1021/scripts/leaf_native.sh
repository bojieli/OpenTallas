#!/usr/bin/env bash
set -euo pipefail
S="rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_fp_n32.sv"
bash census.sh fpadd ot_s81sl_fp_add_n32 - $S > fpadd.log 2>&1 & p=$!
bash census.sh fpmul ot_s81sl_fp_mul_n32 - $S > fpmul.log 2>&1 & q=$!
wait "$p";wait "$q"
cat fpadd.log fpmul.log
