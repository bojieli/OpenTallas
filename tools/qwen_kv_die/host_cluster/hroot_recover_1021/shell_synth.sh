#!/usr/bin/env bash
set -euo pipefail
# Diagnostic full RTL shell with mapped engine. Physical wrappers/ot_rst_copies
# are intentionally absent; this does not qualify the final shipping tile.
for f in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_*.lib.gz; do gzip -dc "$f" > "libs/$(basename "${f%.gz}")"; done
L=""; for f in libs/*.lib; do L="$L read_liberty -lib $f;"; done
yosys -l shell_synth.log -p "$L read_verilog -lib macro_bb.v; read_verilog -sv -DSYNTHESIS -DOT_ENG_N32 qkd_host_native_engine_n32.sv private_shell_proposal.sv qkd_hr_ingest_qm.v ot_reset_sync.sv ot_host_die_cdc_sram.sv ot_link_afifo.sv; hierarchy -check -top qkd_hr_ingest_qm; synth -flatten -top qkd_hr_ingest_qm; dfflibmap -liberty libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty libs/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty libs/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib; hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L; opt_clean; stat; write_verilog -noattr shell_mapped.v" > shell_yosys_stdout.log 2>&1
args=(python3 native_census.py --netlist shell_mapped.v --top qkd_hr_ingest_qm --out shell_native.json)
for f in libs/*.lib macro_libs/*.lib; do args+=(--liberty "$f"); done
"${args[@]}" > shell_native.log 2>&1
