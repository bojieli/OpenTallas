#!/bin/bash
set -e
cd "$(dirname "$0")"
verilator --cc --exe --build -j 8 -Wno-fatal --top-module profile_eq --Mdir obj profile_eq.sv profile_eq.cpp rtl/ot_hdc_fastfp.sv rtl/ot_hdc_fp32_mul_lat.sv rtl/ot_hdc_fp32_add_lat.sv rtl/ot_hdc_prefix.sv rtl/ot_hdc_fp32_f12.sv > build.log 2>&1
./obj/Vprofile_eq > positive.log
if ./obj/Vprofile_eq mutant > mutant.log; then echo MUTANT_SURVIVED; exit 2; fi
cat positive.log mutant.log
