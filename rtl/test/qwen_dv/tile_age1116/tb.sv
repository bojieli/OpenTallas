`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[507:0]tap=0;reg[378:0]cmds[0:3];wire[513:0]tout,ny;
qfd_tile_nk_rp2_romleaf_rr #(.REGROOT_MODE(3)) d(.ck(ck),.ck_rp0(ck),.ck_rp1(ck),.ck_rp2(ck),.ck_rp3(ck),.ck_rp4(ck),.ck_rp5(ck),.ck_rp6(ck),.ck_rp7(ck),.ck_rp8(ck),.ck_rp9(ck),.ck_tx0(ck),.ck_tx1(ck),.ck_tx2(ck),.ck_tx3(ck),.ck_tx4(ck),.ck_tx5(ck),.ck_tx6(ck),.ck_tx7(ck),.ck_rsw(ck),.ck_rnw(ck),.ck_dw(ck),.ck_de(ck),.ck_rs(ck),.ck_rn(ck),.ck_fa0(ck),.ck_fa1(ck),.ck_fa2(ck),.ck_fa3(ck),.ck_fa4(ck),.ck_lsl0(ck),.ck_lsl1(ck),.ck_lsl2(ck),.ck_lsl3(ck),.ck_lsl4(ck),.ck_lsl5(ck),.ck_lsl6(ck),.ck_lsl7(ck),.ck_node(ck),.rst_n(rst_n),.tile_id(16'd0),.tap(tap),.n_a(514'd0),.n_b(514'd0),.t_out(tout),.n_y(ny),.tie_hi(),.tie_lo());
integer op=0,cy=0,n=0,first=-1,last=-1;string file;
initial begin
 if(!$value$plusargs("cmds=%s",file))$fatal(1,"no commandfile");$readmemh(file,cmds);
 if($value$plusargs("op=%d",op))begin end
 repeat(20)@(negedge ck);rst_n=1;
 for(cy=0;cy<4096;cy++)begin
 @(negedge ck);tap=0;tap[507:380]={4{32'h3f800000}};
 if(cy==32)begin tap[0]=1;tap[379:1]=cmds[op];end
 @(posedge ck);
 if(tout[512])begin n++;if(first<0)first=cy;last=cy;$display("TV edge%0d age%0d",cy,cy-32);end
 if(tout[513])$display("FAULT edge%0d",cy);
 end
 $display("TILE_TIMING op%0d n%0d first%0d last%0d firstage%0d lastage%0d fault%b",op,n,first,last,first-32,last-32,tout[513]);$finish;
end
endmodule
