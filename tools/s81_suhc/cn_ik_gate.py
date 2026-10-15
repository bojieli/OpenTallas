#!/usr/bin/env python3
"""Native synthesizable CN/IK composed arithmetic gate, all production row widths."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_suhc')]
os.environ.setdefault('HDC_V41_ARITH','chunk8')
import hdc_golden_v41 as V
import hc_gate as H
import su_gate as S

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--dim',type=int,choices=[128,512],required=True);p.add_argument('--mut',action='store_true')
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 rng=np.random.default_rng(1014000+a.dim)
 x=V.to_bf16(rng.standard_normal(a.dim).astype(np.float32));w=V.to_bf16((rng.uniform(.1,2,a.dim)).astype(np.float32))
 ang=rng.uniform(-3,3,32);c=np.cos(ang).astype(np.float32);s=np.sin(ang).astype(np.float32)
 norm=V.rmsnorm_bf16(x,w,np.float32(1e-6));ro=V.rope_tail(norm,(c,s))
 y=V.qdq_fp4_e4m3(ro,16) if a.dim==512 else V.qdq_fp4_e8m0(ro,32)
 for name,data in [('x',x),('gain',w),('cos',c),('sin',s)]:
  (a.out/(name+'.mem')).write_text(''.join(f'{int(v):08x}\n' for v in data.view(np.uint32)))
 (a.out/'expected.mem').write_text(''.join(f'{int(v):04x}\n' for v in H.bf16bits(y)))
 r=S.Run(S.SHAPES['full']);bases=(r.cn if a.dim==512 else r.ik)(x,w,np.float32(1e-6),c,s)
 (a.out/'raw.mem').write_text(''.join(f'{r.exp[bases["raw_base"]+i]:036x}\n' for i in range(a.dim//32)))
 extra=['rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_cn_ik.sv','rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv']
 tb='rtl/dsrom_sys/s81_suhc/test/tb_s81_su_cn_ik.sv'
 src=list(dict.fromkeys(H.FP['rtl']+S.RTL+S.HIER+extra))
 pins={s:H.sha(ROOT/s) for s in src+[tb]}
 obj=a.out/('obj_mut' if a.mut else 'obj')
 cmd=[H.VERILATOR,'--binary','--timing','-O1','-fno-dfg','--unroll-count','4','-Wno-fatal','-Wno-WIDTH','--top-module','tb_s81_su_cn_ik','-GD='+str(a.dim),'-GMUT_NO_ROPE='+str(int(a.mut)),'-Mdir',str(obj),'-j','8',*[str(ROOT/s) for s in src+[tb]],'-CFLAGS','-O1']
 b=subprocess.run(cmd,capture_output=True,text=True);(a.out/('build_mut.log' if a.mut else 'build.log')).write_text(b.stdout+b.stderr)
 if b.returncode:raise RuntimeError('build failed '+str(a.out/'build.log'))
 r=subprocess.run([str(obj/'Vtb_s81_su_cn_ik')],cwd=a.out,capture_output=True,text=True);(a.out/('run_mut.log' if a.mut else 'run.log')).write_text(r.stdout+r.stderr)
 ok=r.returncode==0 and 'CNIK PASS' in r.stdout
 print(r.stdout,flush=True)
 if pins!={s:H.sha(ROOT/s) for s in src+[tb]}:raise RuntimeError('source changed during build/run')
 rec=dict(schema='opentallas.s81_su.cn_ik.v1',dim=a.dim,status='pass' if ok else 'fail',fp='RTL, no DPI',mut_no_rope=a.mut,source_sha256=pins)
 (a.out/('result_mut.json' if a.mut else 'result.json')).write_text(json.dumps(rec,indent=2)+'\n');return int(not ok)
if __name__=='__main__':sys.exit(main())
