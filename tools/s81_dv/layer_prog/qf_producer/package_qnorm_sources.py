from pathlib import Path
import re,subprocess,json,hashlib
root=Path('results/rtl/s81_qf_producer_1019/sid6_vehicle/qnorm_source_bundle');root.mkdir(exist_ok=True)
files=set()
for name in ['tools/s81_slice/vs_bench.sh','tools/s81_slice/xs_bench.sh','tools/s81_dv/layer_prog/qf_producer/run.sh']:
 s=Path(name).read_text()
 files.update(re.findall(r'(?:rtl|physical)/[A-Za-z0-9_./-]+\.(?:sv|v)\b',s))
files.update(['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs_ctl.sv'])
files={f for f in files if '/test/' not in f and not Path(f).name.startswith('tb_') and 'physical/s81_pq_hier/' not in f and f!='rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv'}
# The component uses the actual XS source; the independent PQ reference is not built.
files-={'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv'}
rec=[]
for f in sorted(files):
 r=subprocess.run(['git','show','ceaed19c4:'+f],capture_output=True)
 if r.returncode:raise RuntimeError(f+' '+r.stderr.decode())
 dst=root/'src'/f;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(r.stdout)
 rec.append(dict(path=f,ref='ceaed19c4',sha256=hashlib.sha256(r.stdout).hexdigest(),bytes=len(r.stdout)))
(root/'files.f').write_text('\n'.join('src/'+f for f in sorted(files))+'\n')
(root/'manifest.json').write_text(json.dumps(dict(ref='ceaed19c4',files=rec,new_hardware=False,scope='ONE private QB source component; no frame/CAP source pass'),indent=2)+'\n')
print('PACKAGED',len(files),'bytes',sum(x['bytes'] for x in rec))
