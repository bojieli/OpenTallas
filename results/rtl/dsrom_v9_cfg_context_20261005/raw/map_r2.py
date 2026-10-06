import json,os,subprocess,sys,time,shutil
from pathlib import Path
root=Path('/srv/opentallas-scratch2/codex/fspine-v9-cfg-provider-20261005')
src=root/'src_synth_r2';out=root/'mapped_provider_r2'
def fit(stage):
    def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    a=cpu();time.sleep(2);b=cpu()
    mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
    row=dict(utc=time.time(),stage=stage,load1=os.getloadavg()[0],idle_cores=(b[3]-a[3])/os.sysconf('SC_CLK_TCK')/2,mem_available_bytes=mem['MemAvailable'],disk_free_bytes=shutil.disk_usage(root).free,workers=1,reservation_GiB=1)
    with (root/'map_r2_headroom.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    return row['load1']<128 and row['idle_cores']>=1 and row['mem_available_bytes']>2**30 and row['disk_free_bytes']>1763342096
if len(sys.argv)==1:
    if not fit('pre-guard'):raise SystemExit(75)
    raise SystemExit(subprocess.run(['/srv/opentallas-scratch/admit.sh','1','--',sys.executable,str(Path(__file__).resolve()),'--admitted']).returncode)
if not fit('actual-exec'):raise SystemExit(75)
out.mkdir(exist_ok=False)
(out/'constraint.sdc').write_text('''set_units -time ps -capacitance fF
create_clock -name core_clk -period 833.333333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
# Conditional same-v9 planning cut; external launch insertion remains unqualified.
set_input_delay -min 360 -clock core_clk [get_ports {rst_n cfg_go cfg_ph* cfg_np* go e_sh_free e_bank_free external_cfg_q*}]
set_input_delay -max 727 -clock core_clk [get_ports {rst_n cfg_go cfg_ph* cfg_np* go e_sh_free e_bank_free external_cfg_q*}]
set_output_delay -min 360 -clock core_clk [all_outputs]
set_output_delay -max 727 -clock core_clk [all_outputs]
''')
(out/'config.mk').write_text('''export DESIGN_NICKNAME = copernicus_cfg_provider
export DESIGN_NAME = ot_v41_pair_cfgrom_context
export PLATFORM = asap7
export VERILOG_FILES = /src/physical/dsrom_v9_cfg_context/ot_v41_pair_cfgrom_context.sv /src/physical/dsrom_v9_cfg_context/ot_v41_pair_pq_ld_cfgrom.sv /src/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v
export VERILOG_TOP_PARAMS = HARD_CFG 1 PQ 0
export SYNTH_HDL_FRONTEND = slang
export SDC_FILE = /work/constraint.sdc
export ADDITIONAL_LEFS = /src/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.lef
export ADDITIONAL_LIBS = /src/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8_ss.lib
export CORNER = WC
export CORNERS = WC BC
export WC_LIB_FILES = $(WC_NLDM_LIB_FILES)
export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)
export SYNTH_HIERARCHICAL = 0
export SYNTH_REPEATABLE_BUILD = 1
export ADDER_MAP_FILE =
export NUM_CORES = 1
''')
cmd=['docker','run','--rm','-v',str(src)+':/src:ro','-v',str(out)+':/work','openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work NUM_CORES=1 synth']
(out/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (out/'run.log').open('w') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
(out/'terminal.exit').write_text(str(rc)+'\n')
raise SystemExit(rc)
