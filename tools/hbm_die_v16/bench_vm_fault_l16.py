#!/usr/bin/env python3
"""Generate minimal real VM-status -> updated quadrant leaf -> host-join fault proof.

Uses l16_vm_fault.apply on the actual input contract. Every bank UE/protocol and
hub protocol/mask bit is injected in each quadrant; exact latency, cause, sticky
fault and blocked host admission are checked. Existing serial sync bits retain
one extra cycle. Corrected-error counts alone do not assert fatal status.
"""
import argparse,importlib.util,json
from pathlib import Path

H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('l16',H/'d4g_layers/l16_vm_fault.py')
L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('contract');ap.add_argument('out');a=ap.parse_args()
    c,report=L.apply(L.load(a.contract));I=c['instances'];Q=list(L.QS)
    text=["`timescale 1ns/1ps\n`default_nettype none\nmodule tb_vm_fault_l16;\n parameter integer MUT=0;\n reg clk=0,rst_n=0;always #5 clk=~clk;\n reg [143:0] bank_status[0:3];reg[2:0] hub_status[0:3];reg[15:0] legacy[0:3];\n wire[18:0] vmstat[0:3];wire[3:0] leaf_fault,a_fault;\n wire die_fault,block_ready,program_active,program_fault,irq;wire[3:0]cause;\n integer checked=0;integer cause_bit[0:3];integer sync_bit[0:3];\n"]
    for k,q in enumerate(Q):
        n=I['fr_'+q]['params']['N'];old=n-3;mask=I['fr_'+q]['params']['SYNC_MASK']
        value=int(mask.split("'h")[1],16);sync=next(b for b in range(old) if value&(1<<b))
        edges=[e for e in c['edges'] if e['source'][:2]==['fr_'+q,'fault'] and e['sink'][:2]==['host_status','a_fault']]
        assert len(edges)==1;cb=edges[0]['sink'][2]
        text.append(f" ot_vms_status_static status_{q}(.clk(clk),.rst_n(rst_n),.bank_status(bank_status[{k}]),.hub_status(hub_status[{k}]),.ring_fault(1'b0),.vmstat(vmstat[{k}]));\n")
        text.append(f" wire[{n-1}:0] leaf_in_{q}={{(MUT==1?3'd0:vmstat[{k}][18:16]),legacy[{k}][{old-1}:0]}};\n")
        text.append(f" ot_hbm_fault_leaf #(.N({n}),.SYNC_MASK({mask}),.MUT(MUT==2?3:0)) fr_{q}(.clk(clk),.rst_n(rst_n),.in(leaf_in_{q}),.fault(leaf_fault[{k}]));\n assign a_fault[{cb}]=leaf_fault[{k}];\n")
        text.append(f' initial begin cause_bit[{k}]={cb};sync_bit[{k}]={sync};end\n')
    text.append(""" ot_hbm_status_join_fa #(.NT(1),.NF(1),.NH(1),.TGTS(8'd0),.NA(4),.FCLR(125),.RRELAY(1)) host_status(
 .clk(clk),.rst_n(rst_n),.cfg_v(1'b0),.desc_v(1'b0),.launch_v(1'b0),.cfg_target(8'd0),
 .t_ready(1'b1),.t_active(1'b0),.t_fault(1'b0),.h_fault(1'b0),.a_fault(a_fault),
 .block_ready(block_ready),.program_active(program_active),.program_fault(program_fault),.irq(irq),.die_fault(die_fault),.a_cause(cause));
 task tick;begin @(posedge clk);#1;end endtask
 task reset_case;begin
 @(negedge clk);rst_n=0;
 for(integer q=0;q<4;q=q+1)begin bank_status[q]=0;hub_status[q]=0;legacy[q]=0;end
 repeat(5)tick();@(negedge clk);rst_n=1;repeat(32)tick();
 if(die_fault||cause!=0||!block_ready)$fatal(1,"VM_FAULT_FAIL reset/admission");
 end endtask
 // kind0 bank UE,1 bank protocol,2 hub status,3 preexisting serial source,4 CEcount only.
 task run_case(input integer q,input integer kind,input integer item);
 integer latency;reg expected_fault;reg[3:0] expected_cause;
 begin
 reset_case();latency=(kind==3)?6:8;expected_fault=(kind!=4);expected_cause=4'b1<<cause_bit[q];
 @(negedge clk);
 case(kind)
 0:bank_status[q][item*18+16]=1;
 1:bank_status[q][item*18+17]=1;
 2:hub_status[q][item]=1;
 3:legacy[q][sync_bit[q]]=1;
 4:bank_status[q][item*18]=1;
 endcase
 for(integer age=1;age<=latency+12;age=age+1)begin
  tick();
  if(expected_fault)begin
   if(age<latency && die_fault)$fatal(1,"VM_FAULT_FAIL early q=%0d kind=%0d item=%0d age=%0d",q,kind,item,age);
   if(age>=latency && (!die_fault||block_ready||cause!==expected_cause))
    $fatal(1,"VM_FAULT_FAIL missing/wrong-cause q=%0d kind=%0d item=%0d age=%0d fault=%0b cause=%h",q,kind,item,age,die_fault,cause);
  end else if(die_fault||cause!=0||!block_ready)$fatal(1,"VM_FAULT_FAIL CEcount became fatal q=%0d",q);
  if(age==1)begin @(negedge clk);bank_status[q]=0;hub_status[q]=0;legacy[q]=0;end
 end
 checked=checked+1;
 end endtask
 initial begin
 for(integer q=0;q<4;q=q+1)begin
  for(integer b=0;b<8;b=b+1)begin run_case(q,0,b);run_case(q,1,b);end
  for(integer h=0;h<3;h=h+1)run_case(q,2,h);
 end
 for(integer q=0;q<4;q=q+1)run_case(q,3,0);
 for(integer q=0;q<4;q=q+1)run_case(q,4,0);
 $display("VM_FAULT_PASS cases=%0d all32banksUE/protocol all12hubflags serialsync-preserved CEcount-nonfatal",checked);
 $finish;
 end
endmodule
`default_nettype wire
""")
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'tb_vm_fault_l16.sv').write_text(''.join(text))
    (out/'source_model.json').write_text(json.dumps(report,indent=1)+'\n')

if __name__=='__main__':main()
