#!/usr/bin/env python3
"""Actual remaining varied soft-transport ABIs, preserving evaluated dimensions and parameters."""
import argparse,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[3];sys.path[:0]=[str(root/'tools'),str(root/'tools/die_plan')]
import bind_elab as E
import die_port_bind as D
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--omit-specialization',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
specs=[('ot_pl_pad','rtl/common/landed_parent/ot_pl_land.sv',[dict(W=1,N=0),dict(W=1,N=7)]),('ot_pl_land_n32_chunk_w','rtl/common/landed_parent/ot_pl_land_n32.sv',[dict(W=1,D=4,CHUNK_BITS=24),dict(W=280,D=4,CHUNK_BITS=24)]),('ot_pl_land_chunk_r','rtl/common/landed_parent/ot_pl_land.sv',[dict(W=1,D=4,K=2,CHUNK_BITS=24),dict(W=280,D=4,K=2,CHUNK_BITS=24)]),('ot_pl_land_vector_reset_kw_w','rtl/common/landed_parent/ot_pl_land_kept_enable.sv',[dict(W=1,D=4,CHUNK_BITS=8),dict(W=667,D=4,CHUNK_BITS=8)]),('ot_pl_land_vector_reset_r','rtl/common/landed_parent/ot_pl_land_reset_forest.sv',[dict(W=1,D=4,K=2,CHUNK_BITS=8),dict(W=667,D=4,K=2,CHUNK_BITS=8)]),('ot_s81_mu72_land','rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv',[dict(W=11),dict(W=1106)]),('ot_hdc_v41x_vdly','rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv',[dict(D=1),dict(D=14)]),('ot_hdc_v41x_kreg','rtl/hdc/v41x/ot_hdc_v41x_kreg.sv',[dict(W=1,R=1),dict(W=2,R=0)]),('ot_rst_relay','rtl/lib/ot_rst_relay.sv',[dict(REGIONS=1,SYNC_STAGES=2,TREE_STAGES=1),dict(REGIONS=4,SYNC_STAGES=2,TREE_STAGES=1)]),('ot_s81_frs','rtl/dsrom_sys/s81_dv/unit/ot_s81_frs.sv',[dict(NL=1),dict(NL=4)])]
ports=[];lines=[];expected={}
for master,file,variants in specs:
 module={m.name:m for m in D.parse_modules((root/file).read_text(),file)}[master]
 for n,ps in enumerate(variants):
  inst=f'u_{master}_{n}';env=module.env(ps);conn=[];shape={}
  for pn in module.order:
   direction=module.ports[pn][0];w=module.width(pn,env);assert w is not None,(master,pn,env)
   name=f'{inst}__{pn}';ports.append(f'{direction} wire [{w-1}:0] {name}');conn.append(f'.{pn}({name})');shape[pn]=w
  lines.append(master+' #('+','.join(f'.{k}({v})' for k,v in ps.items())+') '+inst+'('+','.join(conn)+');');expected[inst]=dict(module=master,parameters=ps,ports=shape)
top=a.out/'top.sv';top.write_text('module top('+','.join(ports)+');\n'+'\n'.join(lines)+'\nendmodule\n')
ab=dict(top='top',frontend='slang',netlist=[str(top)],files=list(dict.fromkeys(x[1] for x in specs)),rtl_roots=[])
if not a.omit_specialization:ab['slang_parameterized_blackboxes']=[x[0] for x in specs]
rec=E.elab(ab,root,a.out/'elab',mem_gb=8);design=json.loads((a.out/'elab/asbuilt.json').read_text());cells={c.path:c for c in E.flatten(design,'top').cells}
for inst,want in expected.items():
 c=cells[inst];assert c.module==want['module'],(inst,c.module)
 for pn,width in want['ports'].items():assert len(c.ports[pn])==width,(inst,pn,len(c.ports[pn]),width)
 for k,v in want['parameters'].items():assert k in c.params and int(c.params[k],0)==v,(inst,k,c.params,v)
result=dict(verdict='PASS',instances=len(expected),masters=len(specs),checks=expected,specializations=rec['parameterized_interface_restore']);(a.out/'result.json').write_text(json.dumps(result,indent=1)+'\n');print('ACTUAL_TRANSPORT_ABI_PASS',len(expected))
