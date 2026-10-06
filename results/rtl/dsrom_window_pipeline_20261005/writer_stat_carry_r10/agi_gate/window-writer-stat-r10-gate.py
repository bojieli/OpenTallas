import pathlib, subprocess, json, hashlib, os, time
root=pathlib.Path('/srv/opentallas-scratch/jobs/mencius-window-writer-stat-r10'); src=root/'source'
def resource():
 a=[int(x) for x in pathlib.Path('/proc/stat').read_text().splitlines()[0].split()[1:]];time.sleep(1); b=[int(x) for x in pathlib.Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
 delta=[y-x for x,y in zip(a,b)]; total=sum(delta[:8]); idle=os.cpu_count()*sum(delta[3:5])/total
 mem=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 disk=os.statvfs(root); return dict(time=time.time(),load=os.getloadavg(),cores=os.cpu_count(),idle_cores=idle,mem_available_bytes=mem,disk_free_bytes=disk.f_bavail*disk.f_frsize)
r=resource();(root/'postguard.json').write_text(json.dumps(r,indent=2)); assert r['idle_cores']>=16 and r['mem_available_bytes']>=16*2**30 and r['disk_free_bytes']>=2**30
os.environ['TMPDIR']=str(root/'tmp');os.environ['NUM_CORES']='16'
p='results/rtl/dsrom_window_pipeline_20261005/writer_stat_carry_r10/'
writer=src/'rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_writer_pipeline.sv'
files=[src/'rtl/test/dsrom_sys/s81_window_la/tb_window_writer_stat_carry.sv',writer,src/(p+'writer_reference_for_gate.sv'),src/'rtl/chip/ot_chip_v41x_window_row_codec.sv',src/'rtl/chip/ot_chip_v41x_window_stage4.sv']
def execute(label,cmd):
 with (root/(label+'.log')).open('w') as log:
  code=subprocess.call(['/usr/bin/time','-v','-o',str(root/(label+'.time'))]+list(map(str,cmd)),stdout=log,stderr=subprocess.STDOUT,cwd=src)
 (root/(label+'.exit')).write_text(str(code)+'\n'); return code
assert execute('compile_positive',['iverilog','-g2012','-s','tb_window_writer_stat_carry','-o',root/'positive.vvp']+files)==0
assert execute('positive',['vvp',root/'positive.vvp'])==0
assert 'WINDOW_WRITER_STAT_CARRY_PASS' in (root/'positive.log').read_text()
mutant=root/'writer_missing_carry_mutant.sv'; txt=writer.read_text(); needle='sectors_written_carry <= stat_carry_after_increment(st_sectors_written);'; assert needle in txt
mutant.write_text(txt.replace(needle,'sectors_written_carry <= sectors_written_carry; // deliberately stale',1)); files[1]=mutant
assert execute('compile_negative',['iverilog','-g2012','-s','tb_window_writer_stat_carry','-o',root/'negative.vvp']+files)==0
code=execute('negative',['vvp',root/'negative.vvp']);log=(root/'negative.log').read_text(); assert code!=0 and 'COUNTER_BOUNDARY_ENTER value=000000fe' in log and 'writer cycle/identity/debt/stat mismatch' in log
(root/'gate.json').write_text(json.dumps(dict(positive='PASS',negative='EXPECTED_FAIL',source={str(x.relative_to(src)):hashlib.sha256(x.read_bytes()).hexdigest() for x in src.rglob('*') if x.is_file() and '.git' not in x.parts},post=resource()),indent=2))
print('WINDOW_WRITER_STAT_R10_GATE_COMPLETE',flush=True)
