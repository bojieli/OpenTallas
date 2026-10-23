`timescale 1ns/1ps
module tb_issue;
reg ck=0;always #5 ck=~ck;
reg rst_n=0;reg[115:0]cmd=0;reg[21:0]ctx=0;
wire[37:0]obs;wire[115:0]forwarded;wire[21:0]fctx;
qfd_dv_f16_dispatch_cut dut(.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.context_i(ctx),.cmd_o(forwarded),.context_o(fctx),.observation(obs));
task issue(input[3:0]target,input[2:0]kind,input[8:0]pc,input[21:0]context_word,input bit expected_v);
reg[115:0]word;begin
 word=0;word[0]=1;word[3:1]=kind;word[12:4]=pc;word[115:112]=target;
 @(negedge ck);cmd=word;ctx=context_word;
 @(posedge ck);#1;
 @(negedge ck);cmd=0;ctx=0;
 @(posedge ck);#1;
 if(obs[37]!==expected_v) $fatal(1,"ACTUAL_DISPATCH_VALID target%0d kind%0d",target,kind);
 if(expected_v&&obs!=={1'b1,pc[8:7],4'd3,pc,context_word}) $fatal(1,"ACTUAL_DISPATCH_ID got=%h expected=%h",obs,{1'b1,pc[8:7],4'd3,pc,context_word});
 if(fctx!==context_word) $fatal(1,"COMMAND_CONTEXT_HOP");
 if(kind!=7&&forwarded!==word) $fatal(1,"COMMAND_HOP");
 @(negedge ck);@(posedge ck);#1;
 if(obs[37]!==0) $fatal(1,"SPURIOUS_DISPATCH");
end endtask
initial begin
 repeat(5)@(negedge ck);rst_n=1;repeat(5)@(negedge ck);
 issue(0,7,9'd3,0,0); // actual SETID enumeration assigns slice3
 issue(3,1,9'd257,{6'd11,16'd777},1);
 issue(15,1,9'd129,{6'd2,16'd888},1);
 issue(2,1,9'd257,{6'd11,16'd777},0); // wrong slice address
 issue(3,2,9'd257,{6'd11,16'd777},0); // real station, never SU read
 issue(3,1,9'd388,{6'd37,16'd999},1);
 rst_n=0;repeat(5)@(negedge ck);if(obs!==0)$fatal(1,"ISSUE_RESET");
 $display("PASS F16_ACTUAL_DISPATCH_CUT real_SETID selectedPC/user/slice/stage/token broadcast wrongtarget nonSU context_hop reset");$finish;
end
endmodule
