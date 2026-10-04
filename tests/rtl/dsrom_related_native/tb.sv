`timescale 1ns/1ps
module tb;
 reg fast_clk=0,slow_clk=0;always #3 fast_clk=~fast_clk;always #4 slow_clk=~slow_clk;
 reg cold_n=0,fast_rst_n=0,slow_rst_n=0,abort_fast=0,abort_slow=0;
 reg go=0;reg [29:0] base=0;
 wire request,req_ready,reply_v,reply_ready;wire [29:0] address;wire [16:0] cookie,reply_cookie;
 wire [2047:0] reply_data;wire debt,quarantine,nfault,sp_fault,ready,idle;
 reg [3:0] init_wr_v=0;reg [59:0] init_wr_addr=0;reg [2047:0] init_wr_data=0;reg [63:0] init_wr_mask=0;
 wire [3:0] init_wr_accept,init_wr_visible;
 wire [127:0] w_we;wire [3839:0] w_addr;wire [4095:0] w_data;
 integer group,bank,lane,i,cases=0,accepts=0,replies=0; reg [31:0] value;
 wire [134:0] descriptor={10'd0,base,30'd128,30'd256,30'd128,3'd0,2'd0};
 ot_ds_field_x_related_native #(.ENABLE(1)) bridge(.*,
 .req_v(request),.req_addr(address),.req_cookie(cookie),.reply_data(reply_data),.fault(nfault));
 ot_v41_spine_related_vm #(.VM_RESPONSE_WAIT(1),.PHW(10),.SAW(16),.R(128),.VAW(30),.VRD(64),.KMAX(6144),.BST(17)) spine(
 .clk(fast_clk),.rst_n(cold_n),.go(go),.i_ph(10'd0),.i_np(3'd0),.i_xbase(base),.i_xps(30'd128),
 .i_obase(30'd256),.i_ops(30'd128),.i_fmt(2'd0),.ready(ready),.idle(idle),
 .x_re(request),.x_addr(address),.x_q(reply_data),.x_req_ready(req_ready),.x_reply_v(reply_v),
 .x_reply_cookie(reply_cookie),.x_reply_ready(reply_ready),.x_cookie(cookie),
 .w_we(w_we),.w_addr(w_addr),.w_data(w_data),.f_cfg_go(),.f_cfg_ph(),.f_cfg_np(),.f_go(),.f_go_bf(),
 .f_xs_v(),.f_xs_p(),.f_xs_b(),.f_xs_sv(),.f_xs_q0(),.f_xs_e0(),.f_xs_q1(),.f_xs_e1(),.f_xs_pos(),
 .f_xb_pos(),.f_xb_v(),.f_xb_b(),.f_xb_sv(),.f_xb_u(),.f_xb_d(),.f_bus(),
 .r_v(128'b0),.r_row(2048'b0),.r_pos(384'b0),.r_fp32(4096'b0),.r_bf16(2048'b0),.r_e(128'b0),
 .f_fault(1'b0),.fault(sp_fault),.phase_cycles());
 function [31:0] fp(input integer k);
 case(k%8)0:fp=32'h3f800000;1:fp=32'h3f808000;2:fp=32'h3f818000;3:fp=32'hbf818000;4:fp=32'h00008000;5:fp=32'h007f8000;6:fp=32'h7f7fffff;default:fp=32'h80000000;endcase
 endfunction
 function [15:0] bf(input integer k);
 case(k%8)0:bf=16'h3f80;1:bf=16'h3f80;2:bf=16'h3f82;3:bf=16'hbf82;4:bf=0;5:bf=16'h0080;6:bf=16'h7f80;default:bf=16'h8000;endcase
 endfunction
 always @(posedge fast_clk)begin
 if(request&&req_ready)begin accepts=accepts+1;$display("EVENT request t=%0t addr=%0d cookie=%0d",$time,address,cookie);end
 if(reply_v&&reply_ready)begin if(reply_cookie!==cookie)$fatal(1,"reply cookie mismatch expected%0d received%0d",cookie,reply_cookie);replies=replies+1;$display("EVENT reply t=%0t cookie=%0d",$time,reply_cookie);end
 end
 task phase(input integer start);
 begin
 @(negedge fast_clk);base=start;go=1;@(negedge fast_clk);go=0;
 @(negedge fast_clk);while(!idle)@(negedge fast_clk);
 while(debt)@(negedge fast_clk);
 for(i=0;i<128;i=i+1)if(spine.bb[i]!==bf(start+i))$fatal(1,"actual BF16 buffer mismatch base%0d lane%0d got%h",start,i,spine.bb[i]);
 if(nfault||sp_fault||quarantine)$fatal(1,"source fault");cases=cases+1;
 end endtask
 initial begin
 repeat(5)@(negedge slow_clk);cold_n=1;fast_rst_n=1;slow_rst_n=1;
 // Full macro instance set is retained; explicit accepted writes initialise read addresses.
 for(group=0;group<3;group=group+1)begin
 @(negedge slow_clk);
 for(bank=0;bank<4;bank=bank+1)begin
 init_wr_addr[bank*15+:15]=group*4+bank;
 for(lane=0;lane<16;lane=lane+1)init_wr_data[(bank*16+lane)*32+:32]=fp((group*4+bank)*16+lane);
 end
 init_wr_mask=64'hffffffffffffffff;init_wr_v=15;
 @(negedge slow_clk);init_wr_v=0;
 while(init_wr_visible!=15)@(negedge slow_clk);cases=cases+1;
 end
 // Same retained stream/phase formats, no generated checkpoint payload.
 spine.phrom[0]=64'd1|(64'd128<<1)|(64'd1<<14);spine.phrom[1]=0;
 spine.strom[0]=48'h11;
 phase(0);phase(1);
 if(accepts!=4||replies!=4)$fatal(1,"lost actual issuer/consumer events %0d/%0d",accepts,replies);
 $display("PASS ACTUAL_SPINE_RELATED_NATIVE cases=%0d macros=256 R=128 VRD=64 reads=4 BF16=256 aligned_and_unaligned=1",cases);$finish;
 end
 initial begin #200000;$fatal(1,"directed event bound");end
endmodule
