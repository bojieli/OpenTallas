import json,importlib.util,pathlib,re,shutil
b=pathlib.Path('/tmp/codex-hbm-0615');k=b/'f512cf1';p=pathlib.Path('/srv/opentallas-scratch/claude/codex-hbm-0615/src/physical/die_plan/hbm_arch_cores/face_shell.py')
s=importlib.util.spec_from_file_location('fs',p);fs=importlib.util.module_from_spec(s);s.loader.exec_module(fs)
j=json.load(open(k/'face_shell.json'));st={n:1 for n in j['widths'] if j['dirs'][n]=='input' and n not in j['passthrough']}
d=b/'f512bench';d.mkdir(exist_ok=True);shutil.copytree(k/'rtl',d/'rtl',dirs_exist_ok=True);shutil.copy2(b/'f512_sram_model.v',d/'sram.v')
old=(k/'rtl/hnx_vms_bank_q0_faces__vecd4ae__fshell.sv').read_text();(d/'gold.sv').write_text(old.replace('module hnx_vms_bank_q0_faces__vecd4ae (','module f512_gold (',1))
for mode in (0,1):
 shell=fs.emit_shell('f512_new'+str(mode),j['core'],j['params'],j['widths'],j['dirs'],j['keep'],set(j['passthrough']),j['clock'],scalars=set(j['scalars']),in_stages=st,rst_relay={'rst_n':1},mutant={'kind':'in_short','bus':'wq0','bit':267}if mode else None)
 (d/('new'+str(mode)+'.sv')).write_text(shell)
# A single delivered-reset relay edge; immediate assertion and one-edge release.
(d/'reset.sv').write_text('''`default_nettype none
(* keep_hierarchy, keep *) module ot_hbm_face_rst_relay #(parameter integer W=1,N=1)(input wire clk,input wire[W-1:0] rst_ni,output wire[W-1:0] rst_no);
for(genvar b=0;b<W;b=b+1)begin:g
reg q;always @(posedge clk or negedge rst_ni[b]) if(!rst_ni[b])q<=1'b0;else q<=1'b1;assign rst_no[b]=q;
end
endmodule
''')
ls=['`timescale 1ns/1ps','module tb; parameter MUT=0; reg clk=0; always #5 clk=~clk; reg rst_n=0; integer cyc=0,bad=0,reads=0,writes=0,faults=0;']
inputs=[n for n in j['widths']if j['dirs'][n]=='input'and n not in j['passthrough']];outs=[n for n in j['widths']if j['dirs'][n]=='output']
for n in inputs:ls.append(f"reg [{j['widths'][n]-1}:0] i_{n}=0;")
for n in outs:
 w=j['widths'][n];ls.append(f'wire[{w-1}:0] a_{n},b_{n}; reg[{w-1}:0] prev_{n}; always @(posedge clk)prev_{n}<=a_{n};')
def conn(out):
 return ','.join('.'+n+'('+('rst_n'if n=='rst_n'else'clk'if n in j['passthrough']else 'i_'+n if j['dirs'][n]=='input'else out+'_'+n)+')'for n in j['widths'])
ls+=['f512_gold gold('+conn('a')+');','generate if(MUT==0)begin f512_new0 dut('+conn('b')+');end else begin f512_new1 dut('+conn('b')+');end endgenerate']
ls+=['function automatic[255:0] data(input integer row,round); for(integer w=0;w<8;w=w+1)data[32*w+:32]=32\'hbeaf1280 ^ (row<<9) ^ (w*31) ^ (round<<24); endfunction','initial begin integer t,row,g,round; for(cyc=0;cyc<4096;cyc=cyc+1)begin @(negedge clk); t=cyc%1024;round=cyc/1024; rst_n=(t>=16 && !(t>=850&&t<860));']
ls += [f'i_{n}=0;'for n in inputs]
ls += ["if(t>=32&&t<160)begin row=t-32;i_wslot_v=1;i_wslot=row%2; if(row%2==0)i_wq0={1'b1,1'b0,2'd0,10'(row),3'd0,data(row,round),8'hff}; else i_wq1={1'b1,1'b0,2'd0,10'(row),3'd0,data(row,round),8'hff};end",
"if(t>=176&&t<816)begin row=(t-176)/5;g=(t-176)%5;i_rslot_v=1;i_rslot=g;case(g)"]
ls += [f"{g}:i_rq{g}={{1'b1,1'b0,2'd0,10'(row),3'd0}};"for g in range(5)]
ls += ['endcase end',"if(t>=816&&t<824)begin i_rslot_v=1;i_rslot=5;i_pq={1'b1,1'b0,1'b0,10'(t-816),256'd0,8'd0,8'(t)};end", "if(t==830)begin i_rslot_v=1;i_rslot=0;i_rq0={1'b1,1'b0,2'd0,10'd7,3'd0};i_rq1={1'b1,1'b0,2'd0,10'd33,3'd0};end", '@(posedge clk); #1; if(t>=64&&!(t>=850&&t<880))begin']
for n in outs:ls.append(f'if(b_{n}!==prev_{n})begin bad=bad+1;if(bad<8)$display("DIFF {n} cyc%0d got%h want%h",cyc,b_{n},prev_{n});end')
ls += ['reads=reads+b_rr0[256]+b_rr1[256]+b_rr2[256]+b_rr3[256]+b_rr4[256];writes=writes+b_wq_done0+b_wq_done1;faults=faults+b_status[17];end end', '$display("F512_RELAY_RESULT MUT%0d bad%0d reads%0d writes%0d faults%0d",MUT,bad,reads,writes,faults);if(MUT==0&&bad!=0)$fatal(1,"lockstep mismatch");if(reads<2000||writes<300)$fatal(1,"coverage empty");if(MUT!=0&&bad==0)$fatal(1,"mutant escaped");$finish;end endmodule']
(d/'tb.sv').write_text('\n'.join(ls)+'\n');(d/'pincycles.json').write_text(json.dumps(dict(in_extra_stages=st,reset_release_cycles=1,immediate_assert_cycles=0,output_latency_delta=1,throughput_delta=0),indent=1));print('input relay bits',sum(j['keep'][n]for n in st),'buses',len(st))
