#!/usr/bin/env bash
set -euo pipefail
cd /work
L=''
for f in libs/*.lib;do L="$L read_liberty -lib $f;";done
yosys -l whole_wrapper.log -p "$L read_verilog -lib ot_sram_1r1w_32x128_m1_bb.v; read_verilog -sv -DSYNTHESIS qkd_host_native_engine_n32.sv qkd_hr_ingest_eng.v; hierarchy -check -top qkd_hr_ingest_eng; synth -top qkd_hr_ingest_eng -noabc; dfflibmap -liberty libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty libs/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty libs/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib; hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L; opt_clean; write_verilog -noattr whole_wrapper.v; stat" > whole_wrapper.stdout.log 2>&1
