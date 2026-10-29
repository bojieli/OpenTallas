"""Generate the two boundary forms, plus exact instance substitutions from bind_tied.json.
No global constant permission: the original source bit must equal zero at every removed pin.
"""
import json,re,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as D
SPECS=[('ot_hbm_sm_attn_tile','gin',r'sm_N[WE][0-7]\.g_c\[[0-7]\]\.g_p\[0\]\.u_t',64,100),
       ('ot_hbm_sm_attn_be','qin',r'sm_N[WE][0-7]\.g_c\[[07]\]\.u_be',16,138)]
def wrapper(module,seed):
 p=ROOT/'rtl/hbm_accel/sm/attn'/f'{module}.sv';s=p.read_text();m=next(x for x in D.parse_modules(s,str(p)) if x.name==module)
 header=s[s.index('module '+module):re.search(r'^\s*\);\s*$',s[s.index('module '+module):],re.M).end()+s.index('module '+module)]
 header=header.replace('module '+module+' #(','module '+module+'_seed #(',1)
 lines=[line for line in header.splitlines() if not re.search(r'\binput\b.*\b'+seed+r'\b',line)]
 header='\n'.join(lines)
 params=[k for k in m.params if k not in m.localparams];ports=list(m.ports)
 text=header+'\n    '+module+' #(\n'+',\n'.join('        .'+k+'('+k+')' for k in params)+'\n    ) u_seed (\n'+',\n'.join('        .'+k+"('0)" if k==seed else '        .'+k+'('+k+')' for k in ports)+'\n    );\nendmodule\n'
 return text,dict(module=module,variant=module+'_seed',seed_port=seed,source=str(p.relative_to(ROOT)),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),forwarded_parameters=params,forwarded_ports=[x for x in ports if x!=seed])
def generate(tied):
 out='`timescale 1ns/1ps\n`default_nettype none\n// Exact boundary forms: seed absent from interface; original chain identity is internal.\n'
 rules=[];census=[]
 for mod,seed,rx,n,w in SPECS:
  text,info=wrapper(mod,seed);out+=text
  rows=[r for r in tied if r['module']==mod and r['port']==seed]
  assert len(rows)==n,(mod,len(rows),n)
  for r in rows:
   assert re.fullmatch(rx,r['path']),r['path'];assert r['bits']==list(range(w));assert r['values']=='0'*w
   rules.append(dict(inst=re.escape(r['path']),module=mod+'_seed',reason='Exact mathematical seed at the original chain boundary; no added cycle',port_bit_constants={seed:{str(i):'0' for i in range(w)}}))
  info.update(instances=[r['path'] for r in rows],count=n,width=w,bits=n*w);census.append(info)
 out+='`default_nettype wire\n'
 return out,rules,census
if __name__=='__main__':
 tied=json.loads(Path(sys.argv[1]).read_text());text,rules,census=generate(tied)
 (ROOT/'rtl/hbm_next/bind/ot_hnx_sm_seed_heads.sv').write_text(text)
 here=Path(__file__).resolve().parent
 (here/'seed_substitute_inst.json').write_text(json.dumps(rules,indent=1)+'\n')
 (here/'seed_census.json').write_text(json.dumps(dict(schema='opentallas.hbm.seed_heads.v1',instances=sum(x['count'] for x in census),bits=sum(x['bits'] for x in census),added_cycles=0,declarations=census),indent=2)+'\n')
 print('seed heads:80 exact instances,8608 bits,0 added cycles')
