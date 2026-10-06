import os,sys,subprocess,json,time,shutil,hashlib
from pathlib import Path
root=Path('/srv/opentallas-scratch2/codex/wfc-producers-20261005/map_r1');src=root/'src'
def fit(stage):
 def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
 a=cpu();time.sleep(2);b=cpu();m={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
 row=dict(stage=stage,utc=time.time(),load1=os.getloadavg()[0],idle_cores=(b[3]-a[3])/os.sysconf('SC_CLK_TCK')/2,mem_available_bytes=m['MemAvailable'],disk_free_bytes=shutil.disk_usage(root).free,workers=1,reservation_GiB=4,basis='full14 SRAM +4 book macro minimum source component, single-worker Yosys mapped producer context; no wholecore/array; priced logic upper30000um2 +18hardmacros, prior component1017MB allocation plus mapping margin')
 with (root/'headroom.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 return row['load1']<128 and row['idle_cores']>=1 and row['mem_available_bytes']>4*2**30 and row['disk_free_bytes']>1763342096
if len(sys.argv)==1:
 if not fit('pre-guard'):raise SystemExit(75)
 raise SystemExit(subprocess.run(['/srv/opentallas-scratch/admit.sh','4','--',sys.executable,str(Path(__file__).resolve()),'--admitted']).returncode)
if not fit('actual-exec'):raise SystemExit(75)

out=root/'mapped';out.mkdir(exist_ok=False)
files=['physical/dsrom_wfc_producer_context/ot_dsrom_wfc_producer_context.sv','rtl/dsrom_sys/wfc_producers/ot_dsrom_wfc_cfg_prompt.sv','rtl/dsrom_sys/wfc_producers/ot_dsrom_wfc_whole_stage.sv','rtl/dft/ot_rom_secded_dec.sv']
macros=['ot_rom_4096x72_m8','ot_sram_1r1w_512x128_m4_r2c2']
files += ['physical/asap7_memory_macros/'+m+'/'+m+'_bb.v' for m in macros]
(out/'source_pins.json').write_text(json.dumps({'source_commit':'be07cd4e0','model':'model_v2.json','sha256':{str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(src.rglob('*')) if p.is_file()}},indent=2)+'\n')
lines=['export DESIGN_NICKNAME = copernicus_wfc_producers','export DESIGN_NAME = ot_dsrom_wfc_producer_context','export PLATFORM = asap7','export VERILOG_FILES = '+' '.join('/src/'+x for x in files),'export VERILOG_TOP_PARAMS = ENABLE 1','export SYNTH_HDL_FRONTEND = slang','export SDC_FILE = /src/physical/dsrom_wfc_producer_context/constraint.sdc','export ADDITIONAL_LEFS = '+' '.join('/src/physical/asap7_memory_macros/'+m+'/'+m+'.lef' for m in macros),'export ADDITIONAL_LIBS = '+' '.join('/src/physical/asap7_memory_macros/'+m+'/'+m+'_ss.lib' for m in macros),'export CORNER = WC','export CORNERS = WC BC','export WC_LIB_FILES = $(WC_NLDM_LIB_FILES)','export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)','export SYNTH_HIERARCHICAL = 0','export SYNTH_REPEATABLE_BUILD = 1','export ADDER_MAP_FILE =','export NUM_CORES = 1']
(out/'config.mk').write_text('\n'.join(lines)+'\n')
cmd=['docker','run','--rm','-v',str(src)+':/src:ro','-v',str(out)+':/work','openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work NUM_CORES=1 synth']
(out/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (out/'run.log').open('w') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
(out/'terminal.exit').write_text(str(rc)+'\n')
raise SystemExit(rc)
