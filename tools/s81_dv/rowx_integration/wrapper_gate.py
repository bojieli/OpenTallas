#!/usr/bin/env python3
"""ROWX wrapper lockstep and parameter propagation gate (arithmetic leaf remains an opaque, shared sentinel).

The actual dsdv_svc_att implementation is unchanged and has independent ROWX/PK2 gates. Here its interface is retained
and its fault output encodes ROWX to make a dropped parameter observable. Other unchanged child interfaces are shared
zero-output stubs. Default-off wrapper state/routing is compared at every output bit; all production face wrappers'
ROWX=1 specialization is checked at the actual leaf parameter. This is not an attention arithmetic or whole-die test.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/die_plan'),str(ROOT/'tools/s81_dv')]
import bind_elab as B
import die_port_bind as D
from frame_schedule_asb import header

FILES=['rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs.sv',
       'physical/die_plan/s81/bind/source_modules/portfix178/dsdv_svc_rs_pvso_entry.sv',
       'physical/die_plan/s81/bind/source_modules/portfix178/dsdv_svc_rs_fv.sv']
DEFINES={'OT_SVC_ALLQ':'1','SU_SMU_T':'1','OT_ATTN_HCORE':'1','OT_S81C_HCORE_CTLA':'1','OT_S81C_HCORE_RST_TIMED':'1'}


def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--out',type=Path,required=True); ap.add_argument('--base',default='4b93311de')
 ap.add_argument('--mutant',action='store_true'); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
 new='\n'.join((ROOT/f).read_text() for f in FILES)
 old='\n'.join(subprocess.check_output(['git','-C',str(ROOT),'show',a.base+':'+f],text=True) for f in FILES)
 names={m.group(1) for m in B.MOD_RE.finditer(B._strip(old))}
 old=re.sub(r'\b(?:'+ '|'.join(map(re.escape,sorted(names,key=len,reverse=True)))+r')\b',lambda m:m[0]+'_before',old)
 if a.mutant:
  old_marker='dsdv_svc_att #(.ROWX(ROWX),'
  assert new.count(old_marker)==1
  new=new.replace(old_marker,'dsdv_svc_att #(.ROWX(0),')
 (a.out/'before.sv').write_text(old); (a.out/'after.sv').write_text(new)
 manifest=json.loads((ROOT/'physical/die_plan/s81/bind/asbuilt_b178_coll.json').read_text())
 preferred=[str(ROOT/f) for f in manifest['files']]+[str(ROOT/f) for f in FILES]
 idx=B.module_index(['rtl'],preferred,str(ROOT))
 stubs=[]
 children=set().union(*(B.instantiated(B.module_body(ROOT/f,n),idx) for f in FILES for n in names if B.module_body(ROOT/f,n))) - names
 for n in sorted(children):
  f,_=B.pick(idx,n,preferred)
  raw=D.preprocess(Path(f).read_text(),DEFINES)
  h=header(B._strip(raw),n)
  m=next(x for x in D.parse_modules(raw,f) if x.name==n)
  body=[]
  for p,(direction,_) in m.ports.items():
   if direction=='output':
    body.append('assign '+p+" = "+("(ROWX != 0)" if n=='dsdv_svc_att' and p=='fault' else "'0")+';')
  stubs.append(h+'\n'+'\n'.join(body)+'\nendmodule\n')
 (a.out/'leaves.sv').write_text('\n'.join(stubs))
 core=next(x for x in D.parse_modules(D.preprocess(new,DEFINES),'after') if x.name=='dsdv_svc_rs_c')
 tb=['`timescale 1ns/1fs','module tb;','reg ck=0; always #0.4165 ck=~ck; reg rst=0;']
 conn0=[];conn1=[]; checks=[];drive=[]
 for p,(direction,_) in core.ports.items():
  if p in ('ck','rst'): conn0.append('.'+p+'('+p+')');conn1.append('.'+p+'('+p+')');continue
  w=core.width(p,core.env()); assert w is not None,(p,core.ports[p])
  if direction=='input':
   tb.append(f"reg [{w-1}:0] {p}='0;"); conn0.append('.'+p+'('+p+')');conn1.append('.'+p+'('+p+')')
   if p not in ('sid',):
    drive.extend(f'{p}[{k} +: {min(32,w-k)}] = {min(32,w-k)}\'($urandom);' for k in range(0,w,32))
  elif direction=='output':
   for suffix in ('old','new'):tb.append(f'wire [{w-1}:0] {p}_{suffix};')
   conn0.append('.'+p+'('+p+'_old)');conn1.append('.'+p+'('+p+'_new)')
   checks.append(f'if ({p}_old !== {p}_new) $fatal(1,"LOCKSTEP {p} cycle %0d", c);')
 tb.append('dsdv_svc_rs_c_before #(.ENTRY(1)) u_old ('+','.join(conn0)+');')
 tb.append('dsdv_svc_rs_c #(.ENTRY(1),.ROWX(0)) u_new ('+','.join(conn1)+');')
 fv=[x for x in D.parse_modules(D.preprocess(new,DEFINES),'after') if '_fv_' in x.name]
 trace_checks=[]
 for i,m in enumerate(fv):
  cn=[f'.{p}(\'0)' if d=='input' else f'.{p}()' for p,(d,_) in m.ports.items()]
  tb.append(m.name+f' #(.ROWX(1)) p{i} ('+','.join(cn)+');')
  path='u.u.u_att' if 'pvso_entry' in m.name else 'u.u_att'
  trace_checks.append(f'if(p{i}.{path}.ROWX != 1) $fatal(1,"PARAM {m.name}");')
 tb+=['integer c; integer checked=0; initial begin',*trace_checks,'repeat(4) @(negedge ck); rst=1;',
      'for(c=0;c<40;c=c+1) begin @(negedge ck);',*checks,
      'checked=checked+1; if(c>2) begin',*drive,'end end',
      f'$display("ROWX_WRAPPER_GATE PASS lockstep=%0d profiles={len(fv)}",checked); $finish; end endmodule']
 (a.out/'tb.sv').write_text('\n'.join(tb)+'\n')
 args=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','--Mdir',str(a.out/'obj'),'-j','4',
       '-I'+str(ROOT/'rtl/dsrom_sys/s81_dv/svc_rs')]+['-D'+k+'='+v for k,v in DEFINES.items()]+[str(a.out/f) for f in ('leaves.sv','before.sv','after.sv','tb.sv')]
 with (a.out/'build.log').open('w') as f: subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (a.out/'run.log').open('w') as f: run=subprocess.run([str(a.out/'obj/Vtb')],stdout=f,stderr=subprocess.STDOUT)
 print((a.out/'run.log').read_text(),end='')
 return run.returncode
if __name__=='__main__':sys.exit(main())
