import hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
root=Path('/srv/opentallas-scratch2/codex/fspine-v9-cfg-provider-20261005')
src=root/'src'
def capacity(stage):
    def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    a=cpu();time.sleep(2);b=cpu()
    memory={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
    row=dict(stage=stage,utc=time.time(),load1=os.getloadavg()[0],idle_cores=(b[3]-a[3])/os.sysconf('SC_CLK_TCK')/2,
             available_RAM_bytes=memory['MemAvailable'],free_disk_bytes=shutil.disk_usage(root).free,
             workers=1,reservation_GiB=1,required_disk_bytes=1763342096,
             disk_basis='conservative retained one-full-element Z18 work inventory; this is only a configuration macro+loader')
    with (root/'headroom.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    return row['load1']<128 and row['idle_cores']>=1 and row['available_RAM_bytes']>2**30 and row['free_disk_bytes']>row['required_disk_bytes']
if len(sys.argv)==1:
    if not capacity('pre-guard'):raise SystemExit(75)
    raise SystemExit(subprocess.run(['/srv/opentallas-scratch/admit.sh','1','--',sys.executable,str(Path(__file__).resolve()),'--admitted']).returncode)
if not capacity('actual-exec'):raise SystemExit(75)
inputs=[str(p.relative_to(src)) for p in sorted(src.rglob('*')) if p.is_file()]
(root/'source_pins.json').write_text(json.dumps(dict(source_commit='36a846101',sha256={p:hashlib.sha256((src/p).read_bytes()).hexdigest() for p in inputs}),indent=2)+'\n')
files=['physical/dsrom_v9_cfg_context/tb_cfgrom_context.sv','physical/dsrom_v9_cfg_context/ot_v41_pair_cfgrom_context.sv','physical/dsrom_v9_cfg_context/ot_v41_pair_pq_ld_cfgrom.sv','physical/dsrom_v9_parent_context/ot_v41_pair_pq_ld_frontend.sv','physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v']
argv=['verilator','--binary','--timing','--assert','-Wno-fatal','--top-module','tb_cfgrom_context','-j','1','--Mdir',str(root/'objects'),'-o','cfg_gate',*files]
(root/'command.json').write_text(json.dumps(argv,indent=2)+'\n')
with (root/'build.log').open('w') as log:
    rc=subprocess.run(['/usr/bin/time','-v',*argv],cwd=src,stdout=log,stderr=subprocess.STDOUT).returncode
(root/'build.exit').write_text(str(rc)+'\n')
if not rc:
    with (root/'gate.log').open('w') as log:rc=subprocess.run([str(root/'objects/cfg_gate')],cwd=src,stdout=log,stderr=subprocess.STDOUT).returncode
(root/'terminal.exit').write_text(str(rc)+'\n')
raise SystemExit(rc)
