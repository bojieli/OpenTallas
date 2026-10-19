#!/usr/bin/env python3
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/qwen_layerbench')]
import global_boundary as G
import dv_lower as D
import dv_lower_vec as V

def main():
 a=argparse.ArgumentParser();a.add_argument('--work',type=Path,required=True);a.add_argument('--vl',required=True);p=a.parse_args();p.work.mkdir(parents=True,exist_ok=True)
 c=G.layer_contract(ROOT/V.PROG);own=D.ownership();vm=V.vm_map_vec(own);cr=V.crom_map(own)
 # Source-derived words; unused non-X fields have no bearing on this address bench.
 isa=dict(head_k=7,head_eps=0,sigm_imm=D.f32(-1.0));rows=[];rewrites=0
 for stage in range(1,37):
  for user in range(4):
   for name in ('qkv','o','gu','down'):
    e=c['epochs'][name];me=G.rewrite_me(int(e['word'],16),user,e)
    xb=G.get(me,G.ISA.LAYOUT,'me_xbase')
    f=G.ISA.decode(int(e['word'],16))
    original_xpf=(f['me_round']<<71)|(f['me_k']<<53)|(f['me_split']<<49)|(f['me_xks']<<37)|(f['me_xcs']<<25)|(e['original_base']<<1)|1
    xpf=G.rewrite_xpf72(original_xpf,user,e)
    if xpf>>1&((1<<24)-1)!=xb:raise ValueError('ME/XPF namespace mismatch')
    try:G.rewrite_xpf72(original_xpf^2,user,e)
    except ValueError:pass
    else:raise ValueError('wrong XPF source accepted')
    # Verify every emitted actual SU element has one exact matching ME position.
    writes=[]
    for s in range(12):
     ws=V.words(s,own,vm,cr,isa,att=[0,1,2,3])
     key={'qkv':'xs','gu':'xs','o':'xa','down':'silu'}[name]
     if key not in ws:continue
     w=G.rewrite_x(ws[key],user,c);rewrites+=1
     g=lambda k:G.get(w,G.SU_LAYOUT,k)
     for o in range(g('nout')):
      writes.extend((g('d')&((1<<22)-1))+o*g('dso')+i*g('dsi') for i in range(g('nin')))
    if sorted(writes)!=list(range(xb,xb+e['elements'])):raise ValueError('source producer/consumer element mismatch '+name)
    rows.append(f'{xb:x} {min(writes):x} {G.get(me,G.ISA.LAYOUT,"me_k")} {G.get(me,G.ISA.LAYOUT,"me_split")} {e["elements"]//64}\n')
 inp=p.work/'x_events.txt';inp.write_text(''.join(rows))
 d=p.work/'build';exe=d/'Vtb_global_x_join';d.mkdir(exist_ok=True)
 cmd=[p.vl,'--binary','--timing','-j','4','-Wno-fatal','--top-module','tb_global_x_join','-Mdir',str(d),str(ROOT/'rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv'),str(ROOT/'rtl/qwen_dv/qfd_dv_stream.sv'),str(ROOT/'rtl/test/mu_qwen_seq/tb_global_x_join.sv')]
 r=subprocess.run(cmd,capture_output=True,text=True);(d/'build.log').write_text(r.stdout+r.stderr)
 if r.returncode:raise RuntimeError('buildfailed')
 for mut in (0,1,2,3,4):
  r=subprocess.run([str(exe),f'+INPUT={inp}',f'+MUT={mut}'],capture_output=True,text=True);(p.work/f'm{mut}.log').write_text(r.stdout+r.stderr)
  if (r.returncode==0)!=(mut==0):raise RuntimeError('unexpected mutant outcome '+str(mut))
  print(r.stdout.strip(),flush=True)
 (p.work/'source_contract.json').write_text(json.dumps(dict(contract=c,stages=36,users=4,actual_SU_rewrites=rewrites,added_cycles=0,scope='address publication/tap component only; arithmetic uses exactly representable 1.0; no token proof'),indent=2)+'\n')
 print('GLOBAL_X_JOIN_MATRIX_PASS',flush=True)
if __name__=='__main__':main()
