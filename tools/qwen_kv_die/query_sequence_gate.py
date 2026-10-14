#!/usr/bin/env python3
"""Exercise exact production query-counter block; full core arithmetic separate."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rtl=pathlib.Path('rtl/hdc/ot_qwen_w12_matvec.sv');s=rtl.read_text();start=s.index('    generate if(XCONTEXT_EXPORT != 0)begin:g_query_identity');end=s.index('    end endgenerate',start)+len('    end endgenerate');block=s[start:end]
header='''module query_fixture(input wire clk,rst_n,active,go,ready,i_query_ack_toggle,input wire[31:0]gb,input wire[3:0]split_r,output wire[39:0]x_query_seq,output wire x_query_toggle,x_query_credit,x_query_fault);
localparam G=4,NPX=4,GT=3072,XCONTEXT_EXPORT=1;
'''
bench='''`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0,active=0,go=0,ready=0,i_query_ack_toggle=0;reg[31:0]gb=0;reg[3:0]split_r=7;wire[39:0]x_query_seq;wire x_query_toggle,x_query_credit,x_query_fault;
query_fixture dut(.*);
task step;begin #2;clk=1;#2;clk=0;#2;end endtask
initial begin
#1;rst_n=1;#1;rst_n=0;#1;rst_n=1;
go=1;repeat(3)step();if(x_query_toggle)$fatal(1,"offer created query");ready=1;step();go=0;ready=0;active=1;
step();if(x_query_seq!==0||x_query_toggle!==1||x_query_credit)$fatal(1,"actual first issue identity");
#120;if(x_query_seq!==0||x_query_toggle!==1)$fatal(1,"pause duplicated level");
i_query_ack_toggle=1;step();if(x_query_seq!==1||x_query_toggle!==0)$fatal(1,"next real issue not unique");
active=0;repeat(60)step();if(x_query_seq!==1||x_query_toggle!==0||x_query_fault)$fatal(1,"arithmetic drain invented queries");
i_query_ack_toggle=0;dut.g_query_identity.next_sequence=40'h00ffffffff;active=1;step();if(x_query_seq!==40'h00ffffffff)$fatal(1,"32bit boundary issue");i_query_ack_toggle=x_query_toggle;step();if(x_query_seq!==40'h0100000000)$fatal(1,"sequence truncated32");
i_query_ack_toggle=x_query_toggle;dut.g_query_identity.next_sequence=40'h7fffffffff;step();if(x_query_seq!==40'h7fffffffff||dut.g_query_identity.next_sequence!==40'h8000000000)$fatal(1,"sourcebound2to39 wrapped");
active=0;i_query_ack_toggle=x_query_toggle;go=1;ready=1;step();go=0;ready=0;active=1;step();if(x_query_seq!==0||x_query_fault)$fatal(1,"acceptedop notresetnamespace");
$display("PASS exact productionblock actualqueryedge/pause/drain/ACK;40bit crossing32/39;acceptedopreset");$finish;
end endmodule
'''
records={}
with tempfile.TemporaryDirectory(prefix='qwen-query-seq-') as tmp:
 for name,content in {'positive':block,'truncated32':block.replace('issued_sequence<=next_sequence','issued_sequence<=next_sequence[31:0]')}.items():
  path=pathlib.Path(tmp)/f'{name}.sv';path.write_text(header+content+'\nendmodule\n'+bench);exe=path.with_suffix('.vvp');r=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(path)],capture_output=True,text=True);assert r.returncode==0,r.stderr
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(a.out/f'{name}.log').write_text(r.stdout+r.stderr);records[name]={'exit':r.returncode,'block_sha256':hashlib.sha256(content.encode()).hexdigest()};assert (r.returncode==0)==(name=='positive'),name
(a.out/'record.json').write_text(json.dumps({'status':'EXACT_PRODUCTION_COUNTER_BLOCK_UNIT_ONLY_FULL_CORE_PENDING','source_sha256':hashlib.sha256(rtl.read_bytes()).hexdigest(),'cases':records},indent=2)+'\n')
