import os,sys,time,json,subprocess,shutil,hashlib
from pathlib import Path
root=Path('/srv/opentallas-scratch/codex/ds-protected-vm-20261006/gate_r2_portable');src=root/'src'
tool=root/'tool'
os.environ['VERILATOR_ROOT']=str(tool/'usr/share/verilator')
os.environ['VERILATOR_BIN']=str(tool/'verilator_bin_portable.sh')
need=4*2**30
# Reservation only; no process wall/AS/file limit. Source288hardmacro bodies
# total2.25MiB storage +~20k protected transport bits, one compiler worker.
# Prior same-macro component runtime allocation1GiB;4GiB leaves compile margin.
def fit(stage):
 def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
 a=cpu();time.sleep(2);b=cpu();mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
 row=dict(stage=stage,utc=time.time(),load1=os.getloadavg()[0],idle_cores=(b[3]-a[3])/os.sysconf('SC_CLK_TCK')/2,mem_available_bytes=mem['MemAvailable'],disk_free_bytes=shutil.disk_usage(root).free,workers=1,reservation_GiB=4)
 ok=row['load1']<os.cpu_count() and row['idle_cores']>=1 and row['mem_available_bytes']>need and row['disk_free_bytes']>2**31
 (root/'capacity_current.json').write_text(json.dumps(row,indent=2)+'\n')
 if ok or stage=='actual-exec':
  with (root/'headroom.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 return ok
if len(sys.argv)==1:
 while True:
  if fit('pre-guard'):
   rc=subprocess.run(['/srv/opentallas-scratch/admit.sh','4','--',sys.executable,str(Path(__file__).resolve()),'--admitted']).returncode
   if rc==75:time.sleep(20);continue
   (root/'controller.exit').write_text(str(rc)+'\n');raise SystemExit(rc)
  time.sleep(20)
if not fit('actual-exec'):raise SystemExit(75)
(root/'source_pins.json').write_text(json.dumps({'source_commit':'554d7b0c9','sha256':{str(p.relative_to(src)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(src.rglob('*')) if p.is_file()}},indent=2)+'\n')
cmd=[str(tool/'usr/bin/verilator'),'--binary','--timing','--x-assign','unique','--x-initial','unique','--assert','-Wno-fatal','-Wno-TIMESCALEMOD','--top-module','tb_dsrom_protected_vm','-j','1','--Mdir',str(root/'objects'),'-o','vm_gate','rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/dsrom_sys/protected_vm/ot_dsrom_vm_pkg.sv','rtl/dsrom_sys/protected_vm/ot_dsrom_vm_codec.sv','rtl/dsrom_sys/protected_vm/ot_dsrom_vm_ratio_fifo.sv','rtl/dsrom_sys/protected_vm/ot_dsrom_vm_backend.sv','rtl/dsrom_sys/protected_vm/ot_dsrom_protected_vm.sv','rtl/dsrom_sys/protected_vm/tb_dsrom_protected_vm.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
(root/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (root/'build.log').open('w') as log:rc=subprocess.run(cmd,cwd=src,stdout=log,stderr=subprocess.STDOUT).returncode
(root/'build.exit').write_text(str(rc)+'\n')
if rc:raise SystemExit(rc)
(root/'generated_inventory.json').write_text(json.dumps({'cpp_files':len(list((root/'objects').glob('*.cpp'))),'generated_bytes':sum(p.stat().st_size for p in (root/'objects').rglob('*') if p.is_file())},indent=2)+'\n')
failures=0
for mode in range(9):
 with (root/('mode'+str(mode)+'.log')).open('w') as log:rc=subprocess.run([str(root/'objects/vm_gate'),'+MODE='+str(mode),'+verilator+seed+1'],cwd=src,stdout=log,stderr=subprocess.STDOUT).returncode
 (root/('mode'+str(mode)+'.exit')).write_text(str(rc)+'\n');failures+=bool(rc)
(root/'terminal.exit').write_text(str(failures)+'\n')
raise SystemExit(bool(failures))
