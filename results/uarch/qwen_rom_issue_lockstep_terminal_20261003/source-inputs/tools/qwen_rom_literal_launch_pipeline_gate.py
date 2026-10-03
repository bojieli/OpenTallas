#!/usr/bin/env python3
"""Literal source broadcast/IREG proof for the priced BD1/XVM0 boundary.

No engine, mapping or provider hardware. Binary formal variables permit every
379-bit instruction on every edge. Unreset payload is never qualified before
reset-valid go. Actual parent ready ownership and physical admission stay open.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from qwen_rom_kv_launch_readiness import FIELDS
ROOT=Path(__file__).resolve().parents[1]
SPINE=Path('rtl/hdc/ot_qwen_me_array_w12.sv')
TILE=Path('rtl/hdc/ot_qwen_rom_tile_context_candidate_r3_retained.sv')
DELAY=Path('rtl/hdc/ot_hdc_delay.sv')
PRICE=Path('results/uarch/qwen_rom_owned_ready_context_20261002/model-r1.json')
YOSYS='/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys'

def literal(mutant=None):
 s=(ROOT/SPINE).read_text().split('module ot_qwen_me_spine_w12',1)[1]
 start=s.index('    wire [IBW-1:0] ib =');end=s.index('    // -- x network:',start)
 block=s[start:end]
 order=re.search(r'ib = \{(.*?)\};',block,re.S)[1]
 if re.findall(r'i_(\w+)',order)!=[n for n,w in FIELDS]:raise ValueError('379bit source ordering changed')
 if '.D(BD - IREG)' not in block or '.d(go && ready)' not in block:raise ValueError('source go/delay contract changed')
 t=(ROOT/TILE).read_text();start=t.index('    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) go_q')
 end=t.index('    wire [NW-1:0] b_nout',start);capture=t[start:end]
 if 'else go_q <= ib_go;' not in capture or 'ib_q <= ib; xl_q <= xl;' not in capture:raise ValueError('literal IREG source changed')
 if mutant=='ungated_go':block=block.replace('.d(go && ready)','.d(go)')
 if mutant=='payload_bit':capture=capture.replace('ib_q <= ib;','ib_q <= ib ^ 379\'d1;')
 if mutant=='missing_go_reset':capture=capture.replace("go_q <= 1'b0;","go_q <= 1'b1;")
 # Extract only literal source pipeline. The independent expected register
 #captures actual preedge source fields; it does not hold them artificially.
 inputs=',\n'.join('input wire [%d:0] i_%s'%(w-1,n) for n,w in FIELDS)
 pipeline='''module source_boundary(input clk,rst_n,go,ready,input[127:0]xl,
'''+inputs+''',output reg go_q,output reg[378:0]ib_q,output reg[127:0]xl_q);
localparam NW=18,AW=24,IBW=379,BD=1,IREG=1;
wire[378:0]tb;wire tgo;
'''+block+'''wire ib_go=tgo;
wire[378:0]tile_ib=tb;
'''+capture.replace('ib_q <= ib;','ib_q <= tile_ib;').replace("ib_q <= ib ^ 379'd1;","ib_q <= tile_ib ^ 379'd1;")+'''endmodule
'''
 ports=','.join('.i_%s(ib[%d -: %d])'%(n,sum(w2 for _,w2 in FIELDS[i:])-1,w) for i,(n,w) in enumerate(FIELDS))
 miter='''module proof(input clk,rst_n,go,ready,input[378:0]ib,input[127:0]xl);
wire go_q;wire[378:0]ib_q;wire[127:0]xl_q;
source_boundary dut(.clk(clk),.rst_n(rst_n),.go(go),.ready(ready),.xl(xl),'''+ports+''',.go_q(go_q),.ib_q(ib_q),.xl_q(xl_q));
reg seen_reset=0,ref_go;reg[378:0]ref_ib;reg[127:0]ref_x;
always @(posedge clk) begin
 if(!rst_n)seen_reset<=1;
 ref_go<=rst_n && go && ready;
 ref_ib<=ib;ref_x<=xl;
end
always @* if(!rst_n)assert(!go_q);
always @* if(seen_reset && rst_n)begin
 assert(go_q==ref_go);
 if(go_q)begin assert(ib_q==ref_ib);assert(xl_q==ref_x);end
end
endmodule
'''
 return pipeline+miter

def run(out,mutant=None):
 if out.exists():raise ValueError('preserve existing receipt')
 price=json.loads((ROOT/PRICE).read_text())
 if price['steady_added_staging_cycles']!=1 or price['tile_successor_counts_unchanged']!=dict(clock=102352,reset=56683):raise ValueError('priced boundary changed')
 text=literal(mutant);out.mkdir(parents=True);(out/'literal.sv').write_text(text)
 setup='read_verilog -formal -sv '+str(out/'literal.sv')+' '+str(ROOT/DELAY)+'; prep -top proof -flatten; async2sync; dffunmap; opt; '
 base=setup+'sat -seq 4 -prove-asserts -set-def-inputs -set rst_n 1 -set-at 1 rst_n 0 -verify -dump_vcd '+str(out/'counterexample.vcd')
 script=setup+'sat -seq 4 -tempinduct -prove-asserts -set-def-inputs -set rst_n 1 -set-at 1 rst_n 0 -verify -dump_vcd '+str(out/'induction_counterexample.vcd')
 (out/'base_command.ys').write_text(base+'\n')
 b=subprocess.run([YOSYS,'-Q','-T','-p',base],text=True,capture_output=True)
 (out/'base.log').write_text(b.stdout+b.stderr)
 (out/'command.ys').write_text(script+'\n')
 p=subprocess.run([YOSYS,'-Q','-T','-p',script],text=True,capture_output=True)
 (out/'yosys.log').write_text(p.stdout+p.stderr)
 success=b.returncode==0 and 'SAT proof finished - no model found: SUCCESS!' in b.stdout and p.returncode==0 and 'Induction step proven: SUCCESS!' in p.stdout
 result=dict(schema='QWEN_LITERAL_LAUNCH_BD1_V1',status='PASS_LITERAL_BINARY_PIPELINE_INDUCTION' if success else 'FAIL_LITERAL_BINARY_PIPELINE_INDUCTION',returncode=b.returncode or p.returncode,base_returncode=b.returncode,induction_returncode=p.returncode,tool_version=subprocess.check_output([YOSYS,'-V'],text=True).strip(),mutant=mutant,BD=1,XVM=0,IREG=1,IBW=379,vector_width=128,all24_fields=True,
  source_sha256={str(n):hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in (SPINE,TILE,DELAY,PRICE)},
  source_fields_change_every_edge=True,invalid_payload_unreset=True,proof_scope='source broadcast and IREG sampling/validity only; conditional known binary inputs and initial reset',
  actual_parent_ready_owner=False,actual_accepted_program_trace=False,all_tile_active_pend_induction=False,vector_owner_and_read_timing=False,
  CDC_or_metastability=False,contextual_SSFF=False,physical_source_admission=False,new_engine=False,new_map=False,new_token=False)
 (out/'terminal.json').write_text(json.dumps(result,indent=2)+'\n')
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--mutant',choices=['ungated_go','payload_bit','missing_go_reset']);a=p.parse_args()
 r=run(a.out,a.mutant);print(r['status']);raise SystemExit(r['returncode'])
