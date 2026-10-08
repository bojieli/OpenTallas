#!/usr/bin/env python3
"""Generate opt-in immutable allocation ROM from actual installed span metadata."""
import argparse,json,hashlib
from pathlib import Path
from hbm_sm_native_allocation_model import model

def build(manifest,out):
    p=Path(manifest);m=json.loads(p.read_text());rows=m['records'];model(len(rows))
    if m['schema']!='opentallas.native_sm.installed_spans.v1' or m['record_count']!=len(rows):raise ValueError('native installed span metadata required')
    cases=[]
    for i,r in enumerate(rows):
        b,n,physical=r['weight_line_base'],r['weight_lines'],r['weight_byte_base']
        if r['record']!=i or not 0<=b<1<<32 or not 0<n<1<<24 or b*160!=physical or r['weight_stride']!=160:
            raise ValueError('nonintegral or invalid native allocation')
        if not any(s['base']==physical and s['end']==physical+160*n and not s['reserved_only'] for s in m['spans']):
            raise ValueError('weight extent has no literal installed span')
        cases.append(f"16'd{i}:begin found=1;rom_base=32'd{b};rom_lines=24'd{n};end")
    text='''// Generated installed native weight span ROM. Default off; not a loader receipt.
// Source sha256: HASH
// Model: tools/hbm_sm_native_allocation_model.py. Actual-flow DMR preservation unqualified.
module ot_hbm_sm_native_allocation #(parameter ENABLE=0)(
 input wire clk,rst_n,input wire req_valid,output wire req_ready,
 input wire[15:0] req_record,input wire[23:0] req_lines,
 output wire rsp_valid,input wire rsp_ready,output wire[15:0] rsp_record,
 output wire[31:0] rsp_base,output wire rsp_error,output wire fault);
 reg found;reg[31:0]rom_base;reg[23:0]rom_lines;
 always @* begin found=0;rom_base=0;rom_lines=0;case(req_record)
 CASES
 default:begin end
 endcase end
 (* keep=1,dont_touch=1 *) reg[49:0] a,b;
 (* keep=1,dont_touch=1 *) reg bad,bad_n;
 wire mismatch=(a[49]!=b[49]) || (a[49] && a[48:0]!=b[48:0]) || (bad==bad_n);
 wire stop=bad || mismatch;
 assign req_ready=ENABLE && !stop && !a[49];
 assign rsp_valid=ENABLE && !stop && a[49];
 assign rsp_record=a[48:33];assign rsp_base=a[32:1];assign rsp_error=a[0];
 assign fault=stop;
 always @(posedge clk or negedge rst_n)begin
 if(!rst_n)begin a<=0;b<=0;bad<=0;bad_n<=1;end
 else if(ENABLE)begin
 if(mismatch)begin bad<=1;bad_n<=0;end
 if(!stop)begin
 if(rsp_valid && rsp_ready)begin a[49]<=0;b[49]<=0;end
 if(req_valid && req_ready)begin
 a<={1'b1,req_record,rom_base,(!found || req_lines!=rom_lines)};
 b<={1'b1,req_record,rom_base,(!found || req_lines!=rom_lines)};
 end
 end
 end
 end
endmodule
'''.replace('HASH',hashlib.sha256(p.read_bytes()).hexdigest()).replace('CASES','\n '.join(cases))
    Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(text)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);a=p.parse_args();build(a.manifest,a.out)
