#!/usr/bin/env python3
"""Minimum complete L1 metadata mechanism: all96dies, all24SMs, all12rows."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL=ROOT/'rtl/hbm_accel/control/ot_hbm_expert_workgroup.sv'
TB=r'''
module tb;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,launch_v=0,desc_ready=0,ret_v=0,out_ready=0;
reg [53:0] expert_ids; reg [6:0] die; reg [7:0] layer=20;
reg [31:0] job; wire launch_ready,desc_v,ret_ready,out_v,done,fault,busy;
wire [4:0] desc_sm; wire [2:0] desc_slot,out_slot;
wire [8:0] desc_expert,desc_lines; wire desc_matrix,out_matrix;
wire [11:0] desc_row,out_row; wire [31:0] desc_base,desc_job,out_job,out_bits;
wire [7:0] desc_layer,out_layer;
reg [4:0] ret_sm; reg [8:0] ret_expert; reg ret_matrix;
reg [11:0] ret_row; reg [31:0] ret_job,ret_bits; reg [7:0] ret_layer;
ot_hbm_expert_workgroup #(.ENABLE(1)) dut(.*);
integer checks=0,dc=0,sm,r,t,n,mode;
initial begin if(!$value$plusargs("mode=%d",mode)) mode=0; end
always @(posedge clk) if(desc_v && desc_ready) begin
 if(desc_sm!==dc || desc_slot!==dc/4 || desc_expert!==expert_ids[(dc/4)*9+:9] ||
    desc_matrix!==((dc/2)%2!=0) || desc_row!==die*24+(dc%2)*12 ||
    desc_base!==dc*288 || desc_lines!==288 || desc_job!==job || desc_layer!==layer)
   $fatal(1,"descriptor wrong sm %d",dc);
 dc=dc+1; checks=checks+1;
end
always @(posedge clk) if(out_v && out_ready) begin
 if(out_bits!==ret_bits || out_slot!==ret_sm/4 || out_matrix!==ret_matrix ||
 out_row!==ret_row || out_job!==ret_job || out_layer!==ret_layer) $fatal(1,"result corruption");
 checks=checks+1;
end
task reset;
begin @(negedge clk); rst_n=0; launch_v=0; ret_v=0; desc_ready=0; out_ready=0;
 repeat(2) @(negedge clk); rst_n=1; dc=0; end
endtask
task launch;
begin
 @(negedge clk); launch_v=1; @(negedge clk); launch_v=0;
 while(dc<24 && !fault) begin desc_ready=($random & 3)!=0; @(negedge clk); end
 desc_ready=0;
end
endtask
task result_row;
input integer s,rr;
begin
 @(negedge clk); ret_sm=s; ret_expert=expert_ids[(s/4)*9+:9]; ret_matrix=(s/2)%2;
 ret_row=die*24+(s%2)*12+rr; ret_job=job; ret_layer=layer;
 ret_bits=32'h80000000 ^ (s<<16) ^ rr; ret_v=1; out_ready=0;
 @(negedge clk); ret_v=0;
 repeat(2) @(negedge clk);
 if(!out_v || out_bits!==ret_bits) $fatal(1,"backpressure lost");
 out_ready=1; @(negedge clk); ret_v=0; out_ready=0;
end
endtask
initial begin
 for(t=0;t<96;t=t+1) begin
 reset; die=t; job=32'hc0000000+t;
 for(n=0;n<6;n=n+1) expert_ids[n*9+:9]=n*64+(t%64);
 launch;
 // Interleave SM retirement so independent rows never reorder within a matrix.
 for(r=0;r<12;r=r+1) for(sm=23;sm>=0;sm=sm-1) result_row(sm,r);
 if(!done || busy || fault || dc!=24) $fatal(1,"completion mismatch");
 end
 if(mode==1) begin
 reset; die=0; job=1; expert_ids={9'd383,9'd300,9'd200,9'd100,9'd50,9'd1}; launch;
 ret_v=1; ret_sm=0; ret_expert=50; ret_matrix=0; ret_row=0; ret_job=1; ret_layer=20; out_ready=1;
 @(negedge clk); if(!fault || out_v) $fatal(1,"wrong expert escaped"); ret_v=0;
 end
 if(mode==2) begin
 reset; expert_ids=0; launch; if(!fault || desc_v) $fatal(1,"duplicate IDs escaped");
 end
 if(mode==3) begin
 reset; die=95; expert_ids={9'd383,9'd300,9'd200,9'd100,9'd50,9'd1}; launch;
 ret_v=1; ret_sm=24; out_ready=1;
 @(negedge clk); if(!fault || out_v) $fatal(1,"inactive SM escaped"); ret_v=0;
 end
 if(mode==4) begin
 reset; die=0; expert_ids={9'd383,9'd300,9'd200,9'd100,9'd50,9'd1}; launch;
 ret_v=1; ret_sm=0; ret_expert=1; ret_matrix=0; ret_row=0; ret_job=job^1; ret_layer=20; out_ready=1;
 @(negedge clk); if(!fault || out_v) $fatal(1,"wrong job escaped"); ret_v=0;
 end
 if(mode==5) begin
 reset; die=0; expert_ids={9'd383,9'd300,9'd200,9'd100,9'd50,9'd1}; launch;
 result_row(0,0);
 ret_v=1; ret_sm=0; ret_expert=1; ret_matrix=0; ret_row=0; ret_job=job; ret_layer=20; out_ready=1;
 @(negedge clk); if(!fault || out_v) $fatal(1,"duplicate row escaped"); ret_v=0;
 end
 $display("PASS checks=%0d mode=%0d",checks,mode); $finish;
end
initial begin #20000000; $fatal(1,"protocol timeout"); end
endmodule
'''
def run(rtl,tb,mode):
    p=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(tb.parent/'sim'),str(rtl),str(tb)],capture_output=True,text=True)
    if p.returncode:return p.returncode,p.stderr
    p=subprocess.run(['vvp',str(tb.parent/'sim'),f'+mode={mode}'],capture_output=True,text=True)
    return p.returncode,p.stdout+p.stderr

def main():
    out=ROOT/'results/rtl/hbm_expert_steering_20261009'; out.mkdir(parents=True,exist_ok=True)
    record=dict(scope='full metadata mechanism; unchangedFP32 forwarding, no arithmetic, no physical qualification',cases=[])
    with tempfile.TemporaryDirectory() as tmp:
        tb=Path(tmp)/'tb.sv';tb.write_text(TB)
        for mode in range(6):
            code,log=run(RTL,tb,mode);record['cases'].append(dict(mode=mode,returncode=code,log=log)); assert code==0,log
        mutant=Path(tmp)/'mutant.sv'; mutant.write_text(RTL.read_text().replace('issued*288','issued*287'))
        code,log=run(mutant,tb,0); record['negative_wrong_source_slice']=dict(returncode=code,log=log);assert code!=0
        mutant.write_text(RTL.read_text().replace('ret_job==j &&','1\'b1 &&'))
        code,log=run(mutant,tb,4); record['negative_missing_job_check']=dict(returncode=code,log=log);assert code!=0
    record['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [RTL,Path(__file__),ROOT/'tools/hbm_expert_steering_model.py']}
    record['verdict']='PASS';(out/'exact.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
