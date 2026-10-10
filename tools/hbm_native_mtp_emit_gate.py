import argparse,json,hashlib,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
if a.out.exists():raise SystemExit('immutable output exists')
sources=['rtl/hbm_accel/control/ot_hbm_native_mtp_emit_queue.sv','rtl/test/hbm_accel/tb_hbm_native_mtp_emit_queue.sv'];cases=[]
# struct-close 2026-10-09: OT_MTPEMIT_SRC (space-separated: DUT file, tb, extra sources) swaps the DUT (registered-boundary wrapper); default unchanged
import os
if os.environ.get('OT_MTPEMIT_SRC'):sources=os.environ['OT_MTPEMIT_SRC'].split()
for mut in (0,1):
 src=root/sources[0]
 if mut:
  src=a.work/'constant_ready.sv';s=(root/sources[0]).read_text();needle='(count<DEPTH || pop)';assert needle in s;src.write_text(s.replace(needle,"1'b1"))
 exe=a.work/f'gate{mut}.vvp';b=subprocess.run(['iverilog','-g2012','-s','tb_hbm_native_mtp_emit_queue','-o',str(exe),str(src),*[str(root/x) for x in sources[1:]]],capture_output=True,text=True)
 if b.returncode:raise RuntimeError(b.stderr)
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);cases.append(dict(mutant=mut,returncode=r.returncode,output=r.stdout))
ok=cases[0]['returncode']==0 and cases[1]['returncode']!=0
rec=dict(schema='opentallas.hbm.native_mtp_emit.rtl.v1',verdict='PASS' if ok else 'FAIL',cases=cases,source_sha256={s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in sources},scope='minimum full38-bit native output and finite host81-bit identity queue')
a.out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2));raise SystemExit(not ok)
