#!/usr/bin/env python3
"""Literal control-only PART1/PART2 issue lockstep for priced SMIN6 BD1.

No datapath, actual ready producer or physical implementation. Root issue and
all-tile acceptance remain conditional on shared reset/clock, legal binary
source fields, matched FAST_ISSUE/KV_PREP and correctly delayed broadcast.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
from qwen_rom_kv_launch_readiness import FIELDS
from qwen_rom_literal_launch_pipeline_gate import literal,YOSYS,SPINE,TILE,DELAY,PRICE
ROOT=Path(__file__).resolve().parents[1]
ME=Path('rtl/hdc/ot_qwen_w12_matvec.sv')
ARITH=Path('rtl/hdc/ot_qwen_w12_arith.sv')

def source(mutant=None):
 raw=(ROOT/ME).read_text();decl=raw[raw.index('    reg              active;'):raw.index('    assign ready = !active && !pend;')]
 fast=raw.split('end else begin : g_issue_fast',1)[1].split('end endgenerate',1)[0]
 if 'PART' in fast or 'gb' in fast or 'GBASE' in fast:raise ValueError('issue loop now depends on tile position/PART')
 for t in ('else if (pend)','else if (!active)','pcnt <= KV_PREP - 1','active <= 1\'b0;'):
  if t not in fast:raise ValueError('literal control source changed')
 fields=',\n'.join('input wire [%d:0]i_%s'%(w-1,n) for n,w in FIELDS)
 view='''module issue_control #(parameter PART=2,LOCAL_KV_PREP=3)(input clk,rst_n,go,
'''+fields+''',output ready,output wire[6:0]state,output reg wrom_re,kv_re,output reg[23:0]wrom_addr);
localparam W=16,IL=8,AW=24,NW=18,GT=6144,PRUNE=1,SMIN=6,KV_PREP=LOCAL_KV_PREP,INT8_WEIGHT=1,INT8_SCALE_WCS_BASE=1;
'''+decl+'''assign ready=!active&&!pend;
assign state={active,pend,pcnt,split_fault};
generate begin:g_issue_fast
'''+fast+'''end endgenerate
endmodule
'''
 # The literal source_boundary connects actual spine go&&ready broadcast
 #to retained tile's reset-valid IREG, all24 source fields, and x capture.
 boundary=literal().split('module proof(',1)[0]
 def ports(bus):return ','.join('.i_%s(%s[%d -: %d])'%(n,bus,sum(w2 for _,w2 in FIELDS[i:])-1,w) for i,(n,w) in enumerate(FIELDS))
 tile_prep=2 if mutant=='KV_PREP_mismatch' else 3
 go='go' if mutant=='ungated_broadcast' else 'go'
 miter='''module lockstep(input clk,rst_n,go,input[378:0]ib,input[127:0]xl);
wire ready,tre,go_q;wire[378:0]ib_q;wire[127:0]xl_q;
wire[6:0]root_state,tile_state;wire rr,kr,tr,tk;wire[23:0]ra,ta;
issue_control #(.PART(2)) root(.clk(clk),.rst_n(rst_n),.go(go),'''+ports('ib')+''',.ready(ready),.state(root_state),.wrom_re(rr),.kv_re(kr),.wrom_addr(ra));
source_boundary broadcast(.clk(clk),.rst_n(rst_n),.go('''+go+'''),.ready(ready),.xl(xl),'''+ports('ib')+''',.go_q(go_q),.ib_q(ib_q),.xl_q(xl_q));
issue_control #(.PART(1),.LOCAL_KV_PREP('''+str(tile_prep)+''')) tile(.clk(clk),.rst_n(rst_n),.go(go_q),'''+ports('ib_q')+''',.ready(tre),.state(tile_state),.wrom_re(tr),.kv_re(tk),.wrom_addr(ta));
reg seen_reset=0;
reg[6:0]shadow;reg ref_rr,ref_kr,ref_accept;reg[23:0]ref_addr;
always @(posedge clk)begin
 if(!rst_n)begin seen_reset<=1;shadow<=0;ref_rr<=0;ref_kr<=0;ref_accept<=0;end
 else begin shadow<=root_state;ref_rr<=rr;ref_kr<=kr;ref_accept<=go&&ready;end
 ref_addr<=ra;
end
always @* if(seen_reset && rst_n)begin
 assert(tile_state==shadow);
 assert(tr==ref_rr);assert(tk==ref_kr);
 if(tr)assert(ta==ref_addr);
 assert(go_q==ref_accept);
 if(go_q)assert(tre);
end
endmodule
'''
 if mutant=='ungated_broadcast':boundary=boundary.replace('.d(go && ready)','.d(go)')
 return view+boundary+miter

def run(out,mutant=None):
 if out.exists():raise ValueError('preserve existing verdict')
 text=source(mutant);out.mkdir(parents=True);(out/'literal.sv').write_text(text)
 setup='read_verilog -formal -sv '+str(out/'literal.sv')+' '+str(ROOT/DELAY)+' '+str(ROOT/ME)+' '+str(ROOT/ARITH)+'; prep -top lockstep -flatten; async2sync; dffunmap; opt; '
 commands={
 'base':setup+'sat -seq 12 -prove-asserts -set-def-inputs -set rst_n 1 -set-at 1 rst_n 0 -verify -dump_vcd '+str(out/'base.vcd'),
 'induction':setup+'sat -seq 12 -tempinduct -prove-asserts -set-def-inputs -set rst_n 1 -set-at 1 rst_n 0 -verify -dump_vcd '+str(out/'induction.vcd')}
 results={}
 for name,cmd in commands.items():
  (out/(name+'.ys')).write_text(cmd+'\n')
  p=subprocess.run([YOSYS,'-Q','-T','-p',cmd],capture_output=True,text=True)
  (out/(name+'.log')).write_text(p.stdout+p.stderr);results[name]=p.returncode
  if p.returncode:break
 passed=results==dict(base=0,induction=0)
 result=dict(status='PASS_LITERAL_ISSUE_LOCKSTEP' if passed else 'FAIL_LITERAL_ISSUE_LOCKSTEP',mutant=mutant,results=results,source_sha256={str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (ME,SPINE,TILE,DELAY,PRICE)},clock='same streaming clock',BD=1,KV_PREP=3,SMIN=6,GT=6144,TG=4,all1536_straps_scope='issue loop literal source has no PART/gb/GBASE dependence; no independent per-tile ready fixture',shared_reset_and_binary_inputs_assumed=True,root_go_to_delayed_tile_idle=True if passed else None,actual_ready_owner=False,actual_provider_instantiated=False,physical_pin_context=False,whole_engine=False,new_map=False,new_token=False)
 (out/'terminal.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);p.add_argument('--mutant',choices=['KV_PREP_mismatch','ungated_broadcast']);a=p.parse_args();r=run(a.out,a.mutant);print(r['status']);raise SystemExit(0 if r['status'].startswith('PASS') else 1)
