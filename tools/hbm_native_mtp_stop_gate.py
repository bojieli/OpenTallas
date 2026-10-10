import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/hbm_accel/control/ot_dshbm_dspark_ctl_stop.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_accept.sv','rtl/gpu/dshbm/ot_dshbm_accept_port.sv','rtl/test/hbm_accel/tb_dshbm_dspark_ctl_stop.sv']
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
if a.out.exists():raise SystemExit('immutable fresh evidence path required')
cases=[]
for kind,m,prl in [(k,m,0) for k in (0,1,2) for m in (0,1)]+[(2,2,0)]+[(k,0,2) for k in (0,1,2)]:
 if True:
  exe=a.work/f'k{kind}m{m}p{prl}.vvp';b=subprocess.run(['iverilog','-g2012','-s','tb_dshbm_dspark_ctl_stop',f'-Ptb_dshbm_dspark_ctl_stop.KIND={kind}',f'-Ptb_dshbm_dspark_ctl_stop.MUT={m}',f'-Ptb_dshbm_dspark_ctl_stop.PRL={prl}','-o',str(exe),*[str(ROOT/s) for s in SRC]],capture_output=True,text=True)
  if b.returncode:raise RuntimeError(b.stderr)
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);cases.append(dict(kind=kind,mutant=m,prompt_read_latency=prl,returncode=r.returncode,output=r.stdout))
ok=all((c['returncode']==0)==(c['mutant']==0) for c in cases)
record=dict(schema='opentallas.hbm.native_mtp_stop.rtl.v1',verdict='PASS' if ok else 'FAIL',scope='real native40layer gamma5 controller and accept, synthetic engine outputs; stop-aware prefix reference, not legacy full-batch state',cases=cases,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC})
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(0 if ok else 1)
