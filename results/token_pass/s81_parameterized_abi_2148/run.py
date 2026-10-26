#!/usr/bin/env python3
"""Small actual-master ABI gate for the S81 source manifest's relay/delay leaves."""
import argparse,json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'tools/die_plan'))
import bind_elab as E
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--omit-specialization',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
files=['rtl/dsrom_sys/s81_glue/ot_s81_rly.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv']
cases=[('ot_s81_rly','r1',1,{'RSREG':0}),('ot_s81_rly','r66',66,{'RSREG':1}),('ot_s81_rly','r276',276,{'RSREG':0}),('ot_s81_rly_k','k266',266,{'RSREG':0,'ID':7}),('ot_s81_rly_k','k283',283,{'RSREG':1,'ID':8}),('ot_hdc_delay','d1',1,{'D':7,'RESET':1}),('ot_hdc_delay','d4',4,{'D':3,'RESET':0}),('ot_hdc_v41x_dly','x8',8,{'D':2}),('ot_hdc_v41x_dly','x32',32,{'D':6})]
ports=['input ck','input rs','input [282:0] i'];body=[]
for master,name,width,params in cases:
 ports += [f'output [{width-1}:0] {name}']; ps=dict(W=width,**params); pp=','.join(f'.{k}({v})' for k,v in ps.items())
 pins=f'.ck(ck),.rs(rs),.i(i[{width-1}:0]),.o({name})' if master.startswith('ot_s81_rly') else (f'.clk(ck),.rst_n(rs),.d(i[{width-1}:0]),.q({name})' if master=='ot_hdc_delay' else f'.clk(ck),.d(i[{width-1}:0]),.q({name})')
 body += [f'{master} #({pp}) u_{name}({pins});']
top=a.out/'top.sv';top.write_text('module top('+','.join(ports)+');\n'+'\n'.join(body)+'\nendmodule\n')
ab={'top':'top','frontend':'slang','netlist':[str(top)],'files':files,'rtl_roots':[],'slang_parameterized_blackboxes':sorted({x[0] for x in cases})}
if a.omit_specialization: ab.pop('slang_parameterized_blackboxes')
r=E.elab(ab,root,a.out/'elab',mem_gb=8);j=json.loads((a.out/'elab/asbuilt.json').read_text());F=E.flatten(j,'top');by={c.path:c for c in F.cells};checks=[]
for master,name,width,params in cases:
 c=by['u_'+name];out='o' if master.startswith('ot_s81_rly') else 'q';expected=dict(W=width,**params)
 assert c.module==master and len(c.ports[out])==width,(name,'wrong port shape',len(c.ports[out]),width)
 for k,v in expected.items(): assert int(c.params[k],0)==v,(name,k,c.params,v)
 checks.append(dict(instance=name,module=master,width=width,parameters=expected))
(a.out/'result.json').write_text(json.dumps(dict(verdict='PASS',instances=len(checks),checks=checks,specializations=r['parameterized_interface_restore']),indent=1)+'\n');print('ACTUAL_RELAY_DELAY_ABI_PASS',len(checks))
