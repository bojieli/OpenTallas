#!/usr/bin/env bash
set -euo pipefail
# Diagnostic decomposition: retain reviewed Gray FIFO/reset hierarchy and SRAMs;
# partition all other mapped cells into one source-pinned native soft region.
mkdir -p partition_probe_r3
cd partition_probe_r3
for f in qkd_host_native_engine_n32.sv private_shell_proposal.sv qkd_hr_ingest_qm.v ot_reset_sync.sv ot_host_die_cdc_sram.sv ot_link_afifo.sv macro_bb.v;do cp ../"$f" .;done
ln -sfn ../libs libs
L='';for f in libs/*.lib;do L="$L read_liberty -lib $f;";done
yosys -l partition.log -p "$L read_verilog -lib macro_bb.v; read_verilog -sv -DSYNTHESIS -DOT_ENG_N32 qkd_host_native_engine_n32.sv private_shell_proposal.sv qkd_hr_ingest_qm.v ot_reset_sync.sv ot_host_die_cdc_sram.sv ot_link_afifo.sv; setattr -mod -set keep_hierarchy 1 ot_link_afifo ot_host_reset_bank ot_reset_sync; hierarchy -check -top qkd_hr_ingest_qm; setattr -set keep_hierarchy 1 t:*ot_link_afifo* t:*ot_host_reset_bank* t:*ot_reset_sync*; synth -flatten -top qkd_hr_ingest_qm; dfflibmap -liberty libs/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib; abc -liberty libs/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib -liberty libs/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty libs/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib; hilomap -hicell TIEHIx1_ASAP7_75t_R H -locell TIELOx1_ASAP7_75t_R L; opt_clean; select -set protected qkd_hr_ingest_qm/t:*ot_link_afifo* qkd_hr_ingest_qm/t:*ot_host_reset_bank* qkd_hr_ingest_qm/t:*ot_reset_sync* qkd_hr_ingest_qm/t:ot_sram*; select -set soft qkd_hr_ingest_qm/c:* @protected %d; submod -hidden -name native_soft @soft; select *; write_verilog -noattr partitioned.v; stat" > partition_stdout.log 2>&1
