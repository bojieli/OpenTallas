#!/usr/bin/env bash
set -euo pipefail
cd /work
L=''
for f in libs/*.lib;do L="$L read_liberty -lib $f;";done
yosys -V > yosys.version
sha256sum qkd_host_native_engine.sv ot_hdc_ingest_fp8q.sv ot_sram_1r1w_32x128_m1_bb.v libs/*.lib > source_library.sha256
yosys -l map.log -p "$L read_verilog -lib ot_sram_1r1w_32x128_m1_bb.v; read_verilog -sv -defer -DSYNTHESIS qkd_host_native_engine.sv ot_hdc_ingest_fp8q.sv; hierarchy -check -top qkd_host_native_engine -chparam AW 32 -chparam HDMAX 128 -chparam KVHMAX 2 -chparam QKV 1 -chparam APIPE 0 -chparam SPIPE6 1 -chparam QPIPE 2 -chparam NATIVE_ROWS 1 -chparam QMUT 0; synth -flatten -top qkd_host_native_engine; dfflibmap -liberty libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty libs/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty libs/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib; hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L; opt_clean; stat; write_verilog -noattr original.v" > map.stdout.log 2>&1
