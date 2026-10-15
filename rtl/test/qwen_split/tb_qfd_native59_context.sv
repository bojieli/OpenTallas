`timescale 1ns/1ps
module tb_qfd_native59_context;
 parameter integer BAD_HOST=0,BAD_STAGE=0,BAD_CMD=0,BAD_CAP=0,BAD_GEN=0,BAD_TAG=0;
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg hev=1,cv=0;reg[1:0]generation=1;reg[58:0]htag={16'd9,6'd0,18'd50994,13'd255,6'd0};reg[15:0]he=9;reg[5:0]stage=1;reg[17:0]token=50994,pos=255;
 reg[379:0]cmd=0;wire bs,rs,fault;wire[58:0]bt,rt;wire[19:0]base;
 qfd_native59_command_context dut(.ck(ck),.rst_n(rst_n),.host_epoch_valid(hev),.host_fused_capability(BAD_CAP?1'b0:1'b1),.host_epoch(he),.host_tag(htag),.host_generation(generation),
 .context_v(cv),.context_stage(stage),.context_token(token),.context_position(pos),
 .native_cmd(cmd),.command_stage(BAD_STAGE?6'd37:6'd1),.command_token(18'd50994),.command_position(18'd255),
 .service_active(1'b0),.begin_slot(bs),.begin_tag(bt),.request_slot(rs),.request_tag(rt),.result_base_word(base),.fault(fault));
 task step;begin @(negedge ck);end endtask
 initial begin
 repeat(3)step();rst_n=1;cv=1;step();cv=0;
 // Future raw context changes cannot relabel the accepted head command.
 token=123;pos=8191;stage=3;
 if(BAD_HOST)he=10;
 if(BAD_GEN)generation=2;
 if(BAD_TAG)htag[58:43]=10;
 cmd=380'h0000003000001000001000c5f0000000000000000000000000100358000000000000000000000000080100000080401;if(BAD_CMD)cmd[56]=!cmd[56];
 #0.1;
 if(!rs||base!=3167)$fatal(1,"native slot/base changed");
 if(!BAD_STAGE&&rt!={16'd9,6'd1,18'd50994,13'd255,6'd0})$fatal(1,"accepted context relabeled by future raw signals");
 step();cmd=0;
 if(fault!==(BAD_HOST!=0||BAD_STAGE!=0||BAD_CMD!=0||BAD_CAP!=0||BAD_GEN!=0||BAD_TAG!=0))$fatal(1,"context fault missing or spurious");
 $display("PASS real-host-epoch context/PC11descriptor observation badhost%0d badstage%0d badcmd%0d badcap%0d badgen%0d badtag%0d",BAD_HOST,BAD_STAGE,BAD_CMD,BAD_CAP,BAD_GEN,BAD_TAG);$finish;
 end
endmodule
