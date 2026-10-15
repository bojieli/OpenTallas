#!/usr/bin/env python3
"""Real-RTL32-head128-dimensional query RoPE/FP4/weight-scale/frame gate."""
import argparse,json,os,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_suhc')]
os.environ.setdefault('HDC_V41_ARITH','chunk8')
import hdc_golden_v41 as V
import hc_gate as H
import su_gate as S

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--mut',type=int,default=0);p.add_argument('--snapshot',type=Path)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 if a.snapshot:
  import pickle
  snap=pickle.loads(a.snapshot.read_bytes());src=snap['idx_q'];x=np.asarray(src['x'],np.float32)
  c,s=(np.asarray(v,np.float32) for v in src['cs']);w=np.asarray(src['weight_input'],np.float32)
 else:
  rng=np.random.default_rng(2026101432);x=V.to_bf16((rng.standard_normal((32,128))*rng.choice([.01,1,7],(32,128))).astype(np.float32))
  w=V.to_bf16(rng.uniform(-3,3,32).astype(np.float32));ang=rng.uniform(-3,3,32);c=np.cos(ang).astype(np.float32);s=np.sin(ang).astype(np.float32)
 if x.shape!=(32,128) or w.shape!=(32,):raise ValueError('actual global32x128 query/32weights required')
 ro=V.rope_tail(x,(c,s));weights=V.to_bf16(V.mul(w,np.float32(1/64)))
 hdr=(4<<508)|(1<<503)|(64<<480)|(31<<495)|(17<<449)|(512<<56)|(0x1234<<33)|1048576
 expected=[hdr]
 for h in range(32):
  blocks=S.aq(ro[h],True);codes=[v for _,cs,_ in blocks for v in cs]
  scales=[(int(e)+127)&255 for e,_,_ in blocks]
  expected.append(S.pack(codes,4));expected.append(S.pack(scales,8)|(int(H.bf16bits(weights)[h])<<32))
 def write(name,values,width): (a.out/name).write_text(''.join(f'{int(v):0{width}x}\n' for v in values))
 write('queries.mem',[S.pack(H.bf16bits(row),16) for row in x],512)
 write('weights.mem',H.bf16bits(w),4);write('cs.mem',[S.pack(S.u32(c),32),S.pack(S.u32(s),32)],256)
 write('expected.mem',expected,128)
 extra=['rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_iq.sv'];tb='rtl/dsrom_sys/s81_suhc/test/tb_s81_su_iq.sv'
 paths=list(dict.fromkeys(H.FP['rtl']+S.RTL+S.HIER+extra+[tb]));pins={s:H.sha(ROOT/s) for s in paths}
 obj=a.out/('obj_m'+str(a.mut))
 cmd=[H.VERILATOR,'--binary','--timing','-O2','-fno-dfg','--unroll-count','4','-Wno-fatal','-Wno-WIDTH','--top-module','tb_s81_su_iq','-GMUT='+str(a.mut),'-Mdir',str(obj),'-j','8',*[str(ROOT/s) for s in paths],'-CFLAGS','-O1']
 b=subprocess.run(cmd,capture_output=True,text=True);(a.out/f'build_m{a.mut}.log').write_text(b.stdout+b.stderr)
 if b.returncode:raise RuntimeError('build failed '+str(a.out/f'build_m{a.mut}.log'))
 r=subprocess.run([str(obj/'Vtb_s81_su_iq')],cwd=a.out,capture_output=True,text=True);(a.out/f'run_m{a.mut}.log').write_text(r.stdout+r.stderr)
 if pins!={s:H.sha(ROOT/s) for s in paths}:raise RuntimeError('sources changed during IQ build/run')
 ok=r.returncode==0 and 'IQ PASS' in r.stdout;print(r.stdout,flush=True)
 rec=dict(schema='opentallas.s81.index-query.native.v1',fp='actual RTL, mapped SRAM models, no DPI',mut=a.mut,status='pass' if ok else 'fail',source_sha256=pins)
 (a.out/f'result_m{a.mut}.json').write_text(json.dumps(rec,indent=2)+'\n');return int(not ok)
if __name__=='__main__':sys.exit(main())
