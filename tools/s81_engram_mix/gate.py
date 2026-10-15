#!/usr/bin/env python3
"""Production 4x5120 native S81 Engram mix gate, canonical chunk8 CPU reference."""
import argparse,os,sys,pickle,subprocess,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_suhc')]
os.environ['HDC_V41_ARITH']='chunk8'
import hdc_golden_v41 as V
import hc_gate as H
F=np.float32

def pack(x): return ''.join(f'{int(v):08x}' for v in np.asarray(x,F).view(np.uint32).ravel()[::-1])
def prep(out,snap):
 if snap:
  s=pickle.load(open(snap,'rb'));assert all(s['checks'].values());h,k,w,v=[s[n] for n in ('h','key','wgt','value')]
  assert F(s['eps'])>0 and F(s['scale'])==F(5120**-.5)
 else:
  rng=np.random.default_rng(1014);h=V.to_bf16(rng.normal(0,1,(4,5120)).astype(F));k=rng.normal(0,1,(4,5120)).astype(F);w=rng.normal(0,1,(4,5120)).astype(F);v=rng.normal(0,1,5120).astype(F)
 eps=F(s['eps']) if snap else F(1e-5);scale=F(s['scale']) if snap else F(5120**-.5)
 (out/'cfg.mem').write_text(pack([eps,scale])+'\n')
 gs=[];ys=[]
 for a,b,c in zip(h,k,w):
  hh=V.reduce_sum_c(V.mul(a,a));kk=V.reduce_sum_c(V.mul(b,b));dd=V.reduce_sum_c(V.mul(V.mul(a,c),b))
  r=V.mul(V.rsqrt(V.add(V.div(hh,F(5120)),eps)),V.rsqrt(V.add(V.div(kk,F(5120)),eps)))
  dot=V.mul(V.mul(dd,r),scale);mag=V.sqrt(F(max(abs(dot),F(1e-6))));g=V.sigmoid(-mag if dot<0 else mag)
  gs.append([hh,kk,dd,g]);ys.append(V.to_bf16(V.add(a,V.mul(g,v))))
 for name,x in [('h',h),('k',k),('w',w),('v',v),('y',ys)]:
  (out/(name+'.mem')).write_text('\n'.join(pack(r) for r in np.asarray(x,F).reshape(-1,32))+'\n')
 (out/'g.mem').write_text('\n'.join(pack(r) for r in gs)+'\n')
 if snap:assert np.array_equal(np.asarray(ys,F).view('u4'),np.asarray(s['out'],F).view('u4'))

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--snap');p.add_argument('--mut',type=int,default=0);p.add_argument('--endpoint',action='store_true');p.add_argument('--issue-period',type=int,default=1);p.add_argument('--mix4',action='store_true',help='four parallel copy clusters dsfd_engram_mix4_c');p.add_argument('--fp',choices=('rtl','dpi'),default='rtl',help='rtl = every FP operator is target RTL (native); dpi = historical C models');a=p.parse_args();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True);prep(out,a.snap)
 top='tb_s81_engram_mix4_c' if a.mix4 else 'tb_s81_engram_mix_c' if a.endpoint else 'tb_s81_engram_mix';obj=out/f'obj_{a.fp}_m{a.mut}_{top}';obj.mkdir(exist_ok=True)
 extras=['rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv','rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv','rtl/dsrom_sys/engram/mix/tb_s81_engram_mix.sv']
 if a.mix4:extras+=['rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv','rtl/dsrom_sys/engram/mix/tb_s81_engram_mix4_c.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv']
 elif a.endpoint:extras+=['rtl/dsrom_sys/engram/mix/dsfd_engram_mix_c.sv','rtl/dsrom_sys/engram/mix/tb_s81_engram_mix_c.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_slab_ep.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv']
 libs=[x for x in H.RTL if '/hdc/' in x]
 fp=[*map(str,H.dpi_rest(obj)),*[str(ROOT/x) for x in H.FP['dpi']]] if a.fp=='dpi' else [str(ROOT/x) for x in H.FP['rtl']]
 srcs=fp+[str(ROOT/x) for x in libs+extras]
 (out/f'sources_{a.fp}_m{a.mut}_{top}.json').write_text(json.dumps({'fp':a.fp,'top':top,'mut':a.mut,'sha256':{str(Path(x).resolve().relative_to(ROOT)) if str(Path(x).resolve()).startswith(str(ROOT)) else x:__import__('hashlib').sha256(Path(x).read_bytes()).hexdigest() for x in srcs}},indent=1))
 cmd=[H.VERILATOR,'--binary','--timing','-O2','-Wno-fatal','--top-module',top,'-Mdir',str(obj),'-j','16',f'-GMUT={a.mut}',*([f'-GISSUE_PERIOD={a.issue_period}'] if a.endpoint and not a.mix4 else []),*srcs,'-CFLAGS','-O1']
 r=subprocess.run(cmd,capture_output=True,text=True);(out/f'build_m{a.mut}.log').write_text(r.stdout+r.stderr)
 if r.returncode:sys.exit(r.returncode)
 r=subprocess.run([str(obj/('V'+top)),'+dir='+str(out)],capture_output=True,text=True);(out/f'run_m{a.mut}.log').write_text(r.stdout+r.stderr);print(r.stdout,flush=True);sys.exit(r.returncode)
if __name__=='__main__':main()
