#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --cc --exe --build -j 8 -Wno-fatal -DOT_HBM_NATIVE_F12_ADD4 -DOT_HBM_NATIVE_F12_MUL5 --top-module profile_eq --Mdir obj profile_eq.sv profile_eq.cpp rtl/gold_fastfp_lat.sv rtl/ot_hdc_fastfp_lat_native_f12.sv rtl/ot_hdc_fastfp.sv rtl/ot_hdc_fp32_mul_lat.sv rtl/ot_hdc_fp32_add_lat.sv rtl/ot_hdc_prefix.sv rtl/ot_hdc_fp32_f12.sv > build.log 2>&1
./obj/Vprofile_eq > positive.log
if ./obj/Vprofile_eq 1 > wrong_data.log;then echo DATA_MUTANT_SURVIVED;exit 2;fi
if ./obj/Vprofile_eq 2 > wrong_date.log;then echo DATE_MUTANT_SURVIVED;exit 2;fi
cat positive.log wrong_data.log wrong_date.log
