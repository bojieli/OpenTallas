#!/usr/bin/env python3
"""Generate MODEL ONLY split-safe fabric with explicitly priced reset epochs.

Does not modify production fabric or produce physical views. Serial reset delay
captures preserve assertion behavior; compact counter substitution is excluded.
"""
import argparse, hashlib, json, re
from pathlib import Path
from qc_safe_graph import extract, ROOT

p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--out',required=True);p.add_argument('--safe-xstn',action='store_true');a=p.parse_args()
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
g=extract();plan=json.loads(Path(a.plan).read_text());bydst={e['dst']:e for e in plan['edges']}
fab=(ROOT/'rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv').read_text()
# Exact 88 kept source flag copies per full landing, carried across the model.
fab=re.sub(r'wire \[3:0\] (land_\w+_vld);',r'wire [87:0] \1;',fab)
fab=re.sub(r'wire \[11:0\] (land_\w+_epo);',r'wire [139:0] \1;',fab)
fab=fab.replace('qfd_c_land_w #','cb16_model_w #').replace('qfd_c_land_r #','cb16_model_r #')
if a.safe_xstn:
 fab=fab.replace('qfd_c_xstn ', 'qfd_c_xstn_safe ').replace('qfd_c_xstnw ', 'qfd_c_xstnw_safe ')
lines=fab.splitlines();padding=[]
for idx,line in enumerate(lines):
 for n,node in g['reset_nodes'].items():
  if re.search(r'\b'+re.escape(n)+r' \(',line):
   e=bydst[n];ps=node['ports'];assert ps.get('N','1')=='1',(n,ps)
   prefix=line[:line.index('qfd_q3h_stn')]
   lines[idx]=prefix+f"cb16_model_reset #(.EDGES({2*e['hard_hops']})) {n} (.ck({ps['ck']}),.d({ps['d']}),.q({ps['q']}));"
   break
fab='\n'.join(lines)+'\n'
# Consumer padding is a serial capture model, with exact original logical clock.
# Tile reset ports are renamed only at their producing flop; other consumer pins
# get a dedicated wire. No padding is omitted from the hardware cost receipt.
for v in plan['consumers']:
 count=2*v.get('pad_hops',0)
 if not count:continue
 inst=v['inst'];node=g['nodes'].get(inst);wire='model_pad_'+inst
 if node:
  pin='rst_n' if 'xstn' in node['kind'] else 'rsi';net=node['ports'][pin];clock=node['ports']['ck']
  pat=r'(\b'+re.escape(inst)+r' \([^\n]*\.'+pin+r'\()'+re.escape(net)+r'(\))'
  fab,n=re.subn(pat,lambda m:m[1]+wire+m[2],fab);assert n==1,(inst,pin,n)
  padding.append(f"wire {wire}; cb16_model_reset #(.EDGES({count})) {wire}_u(.ck({clock}),.d({net}),.q({wire}));")
 else:
  # trst_c_r is the existing externally visible leaf reset.
  col,row=inst[4:].split('_');net=f'trst_{col}_{row}';raw=wire;clock=f'ck_c{col}r{row}'
  match=re.search(r'assign '+net+r' = (\w+);',fab)
  if match:
   source=match[1];fab=fab[:match.start()]+fab[match.end():]
   padding.append(f"cb16_model_reset #(.EDGES({count})) {wire}_u(.ck({clock}),.d({source}),.q({net}));")
  else:
   fab,n=re.subn(r'\.q\('+net+r'\)',f'.q({raw})',fab);assert n==1,(net,n)
   padding.append(f"wire {raw}; cb16_model_reset #(.EDGES({count})) {wire}_u(.ck({clock}),.d({raw}),.q({net}));")
pos=fab.rfind('endmodule');fab=fab[:pos]+'\n'.join(padding)+'\n'+fab[pos:]
(out/'safe_fabric_model.sv').write_text(fab)
helper=r'''
`timescale 1ns/1ps
module cb16_model_reset #(parameter EDGES=2)(input ck,d,output q);
 wire[EDGES:0]s;assign s[0]=d;
 genvar j;generate for(j=0;j<EDGES;j=j+1)begin:g
  reg v;always@(posedge ck)v<=s[j];assign s[j+1]=v;
 end endgenerate
 assign q=s[EDGES];
endmodule
module cb16_model_w #(parameter W=516,D=4)(input ck,rsi,input[W-1:0]i,output[4*W-1:0]bank,output[139:0]epo,output[87:0]vld);
 localparam H=W/2;wire[4*H-1:0]b0,b1;wire[43:0]v0,v1;
 qfd_c_land_safe_w #(.W(H)) a(ck,rsi,i[H-1:0],b0,v0);
 qfd_c_land_safe_w #(.W(H)) b(ck,rsi,i[W-1:H],b1,v1);
 genvar s;generate for(s=0;s<4;s=s+1)begin:g
  assign bank[s*W+:H]=b0[s*H+:H];assign bank[s*W+H+:H]=b1[s*H+:H];
 end endgenerate
 assign vld={v1,v0};
 // Absolute edge tags are simulation-only. Modulo slot tags alone cannot
 // detect a G/R offset that still lies within a slot's four-edge lifetime.
 reg[31:0]cycle=0;always@(posedge ck)cycle<=cycle+1'b1;
 reg[2:0]wc;reg[2:0]tag[0:3];reg[31:0]born[0:3];integer z;
 always@(posedge ck)if(!a.g_slice[0].u.r2)wc<=0;else begin tag[wc%4]<=wc;born[wc%4]<=cycle;wc<=wc+1'b1;end
 generate for(s=0;s<4;s=s+1)begin:t assign epo[35*s+:35]={born[s],tag[s]};end endgenerate
endmodule
module cb16_model_r #(parameter W=516,D=4,K=2)(input ck,rsi,input[4*W-1:0]bank,input[139:0]epo,input[87:0]vld,output[W-1:0]o);
 localparam H=W/2;wire[4*H-1:0]b0,b1;
 genvar s;generate for(s=0;s<4;s=s+1)begin:g
  assign b0[s*H+:H]=bank[s*W+:H];assign b1[s*H+:H]=bank[s*W+H+:H];
 end endgenerate
 qfd_c_land_safe_r #(.W(H),.K(K)) a(ck,rsi,b0,vld[43:0],o[H-1:0]);
 qfd_c_land_safe_r #(.W(H),.K(K)) b(ck,rsi,b1,vld[87:44],o[W-1:H]);
 reg[2:0]rc;wire[2:0]expected=rc-K;wire[1:0]slot=expected[1:0];
 reg[31:0]cycle=0;always@(posedge ck)cycle<=cycle+1'b1;
 always@(posedge ck)begin
  if(!a.g_slice[0].u.r2)rc<=0;else rc<=rc+1'b1;
  if(a.g_slice[0].u.warm&&vld[slot]&&(epo[slot*35+:3]!==expected || cycle-epo[slot*35+3+:32]!=K))
   $fatal(1,"SAFE_PARENT_EPOCH %m slot%0d tag%0d expected%0d absoluteage%0d K%0d",slot,epo[slot*35+:3],expected,cycle-epo[slot*35+3+:32],K);
 end
endmodule
'''
(out/'model_helpers.sv').write_text(helper)
# Price reset initialization in the generated compiler fixture. All normal data
# latencies stay byte-for-byte unchanged. The conservative boot guard allows
# the latest local reset state, a complete D4 fill, and the longest fabric path.
lat=(ROOT/'rtl/test/qcluster_lat.svh').read_text()
longest=max(int(v)for v in re.findall(r'LAT_(?:TAP\d|BCO|RS_FABRIC) = (\d+)',lat))
warm=plan['latest_landing_epoch']+4+longest
lat=re.sub(r'Q3H_RST_DEPTH = \d+',f"Q3H_RST_DEPTH = {plan['A0_xstn_reset_pin_depth']}",lat)
lat=re.sub(r'QC_LAT_WARM = \d+',f'QC_LAT_WARM = {warm}',lat)
(out/'qcluster_lat.svh').write_text(lat)
tb=(ROOT/'rtl/test/tb_qcluster_fabric.sv').read_text()
tb=tb.replace('`include "qcluster_lat.svh"', '`include "qcluster_lat.svh"\n'+f'    initial begin if(QC_LAT_WARM!={warm} || Q3H_RST_DEPTH!={plan["A0_xstn_reset_pin_depth"]}) $fatal(1,"SAFE_COMPILER_WRONG_INCLUDE"); $display("SAFE_COMPILER warm%0d reset%0d",QC_LAT_WARM,Q3H_RST_DEPTH); end')
(out/'tb_safe_fabric_model.sv').write_text(tb)
inputs=[ROOT/'rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv',ROOT/'rtl/physical/qcluster/qfd_c_land_safe.sv',Path(a.plan)]
if a.safe_xstn:inputs.append(ROOT/'rtl/physical/qcluster/qfd_c_xstn_safe.sv')
receipt=dict(schema='opentallas.cb16.safe_fabric_model.v1',model_only=True,inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in inputs},generated={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.glob('*')if p.suffix in ['.sv','.svh']},reset_forward_hops=plan['mapped_forward_hops'],reset_padding_hops=plan['equal_depth_padding_hops'],reset_ff_total=2*plan['total_two_stage_relay_hops'],compiler_reset_core_edge=plan['A0_xstn_reset_pin_depth'],compiler_latest_landing_reset_state=plan['latest_landing_epoch'],compiler_first_active_landing=plan['latest_landing_epoch']+1,compiler_warm_guard_edges=warm,warm_guard_formula='latest landing reset state +D4fill +max normal fabric latency',normal_data_calendar_unchanged=True,physical_adoption=False)
(out/'model_sources.json').write_text(json.dumps(receipt,indent=1)+'\n')
print('SAFE_FABRIC_MODEL',len(bydst),'reset nodes',len(padding),'consumer pads')
