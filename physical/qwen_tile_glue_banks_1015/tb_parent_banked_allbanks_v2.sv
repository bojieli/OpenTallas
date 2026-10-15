// All5 actual rpair bank groups, 16asserted+16released boot edges, full word comparison.
`timescale 1ns/1ps
module tb_parent_banked_allbanks;
 parameter integer MUT=0;
 reg ck=0,rst_n=0;always #5 ck=~ck;
 reg [507:0] tap=0;reg [513:0] n_a=0,n_b=0;
 wire [513:0] cy,ct,ry,rt;
 qfd_tile_nk_banked_v2 #(.ROM_TILE(0),.MUT(MUT)) dut(.ck(ck),.ck_bank({58{ck}}),.ck_reset({11{ck}}),.ck_child({14{ck}}),.rst_n(rst_n),.tile_id(16'b0),.tap(tap),.n_a(n_a),.n_b(n_b),.n_y(cy),.t_out(ct),.tie_hi(),.tie_lo());
 qfd_tile_nk_staged_reference #(.ROM_TILE(0)) ref_parent(.ck(ck),.ck_rp0(ck),.ck_rp1(ck),.ck_rp2(ck),.ck_rp3(ck),.ck_rp4(ck),.ck_lsl0(ck),.ck_lsl1(ck),.ck_lsl2(ck),.ck_lsl3(ck),.ck_lsl4(ck),.ck_lsl5(ck),.ck_lsl6(ck),.ck_lsl7(ck),.ck_node(ck),.rst_n(rst_n),.tile_id(16'b0),.tap(tap),.n_a(n_a),.n_b(n_b),.n_y(ry),.t_out(rt),.tie_hi(),.tie_lo());
 reg [378:0] ib=0;
 reg [17:0] nout,tiles,k;
 reg [3:0] split;
 reg round;
 integer c,j,op,checks=0,outputs=0,node_outputs=0,nonzero=0;
 integer reads[0:4];
 always @(posedge ck)if(rst_n && dut.u_logic.g_rom_pipe.g_rph.g_rb[0].g_hd.u_rp.ce_d)reads[0]=reads[0]+1;
 always @(posedge ck)if(rst_n && dut.u_logic.g_rom_pipe.g_rph.g_rb[1].g_hd.u_rp.ce_d)reads[1]=reads[1]+1;
 always @(posedge ck)if(rst_n && dut.u_logic.g_rom_pipe.g_rph.g_rb[2].g_hd.u_rp.ce_d)reads[2]=reads[2]+1;
 always @(posedge ck)if(rst_n && dut.u_logic.g_rom_pipe.g_rph.g_rb[3].g_hd.u_rp.ce_d)reads[3]=reads[3]+1;
 always @(posedge ck)if(rst_n && dut.u_logic.g_rom_pipe.g_rph.g_rb[4].g_hd.u_rp.ce_d)reads[4]=reads[4]+1;

 task instruction(input integer num);
 begin
  nout=256+(num%3)*16;tiles=1+(num%2);k=1+(num%4);split=7+(num%4);round=num%2;
  ib={nout,tiles,k,1'b0,24'((num%5)*4096+num*17),24'd7,24'd3,24'd1,24'd0,24'd1,24'd1,24'd1,3'd0,split,24'd0,round,24'd0,24'd1,24'd1,1'b0,1'b0,1'b0,1'b0,24'd0};
 end endtask
 always @(negedge ck)if(rst_n && c>40)begin
  if(cy[512]!==ry[512] || ct[512]!==rt[512])$fatal(1,"FAIL parent valid age c%0d cy%h ry%h ct%h rt%h",c,cy[513:512],ry[513:512],ct[513:512],rt[513:512]);
  if(cy!==ry)$fatal(1,"FAIL parent node complete word c%0d got%h want%h",c,cy,ry);
  if(ct!==rt)$fatal(1,"FAIL parent tile complete word c%0d got%h want%h",c,ct,rt);
  checks=checks+1;if(ct[512])begin outputs=outputs+1;if(|ct[511:0])nonzero=nonzero+1;end
  if(cy[512])node_outputs=node_outputs+1;
 end
 initial begin
  for(j=0;j<5;j=j+1)reads[j]=0;
  repeat(16)@(negedge ck);rst_n=1;
  for(c=0;c<6000;c=c+1)begin
   @(posedge ck);#1;
   tap[0]=0;
   if(c%400==16)begin instruction(c/400);tap[379:1]=ib;tap[0]=1;end
   for(j=0;j<4;j=j+1)tap[380+32*j+:32]={1'(c+j),8'(124+j),23'((c*11237+j*3319)^32'h007fffff)};
   n_a[512]=(c%8==0);n_b[512]=n_a[512];n_a[513]=c%701==0;n_b[513]=c%601==0;
   for(j=0;j<16;j=j+1)begin n_a[32*j+:32]={1'b0,8'd127,23'(c*31+j*8191)};n_b[32*j+:32]={1'b1,8'd124,23'(c*131+j*513)};end
  end
  if(checks<3400||outputs<20||node_outputs<100||nonzero<20)$fatal(1,"FAIL parent coverage checks%0d output%0d node%0d nonzero%0d",checks,outputs,node_outputs,nonzero);
  for(j=0;j<5;j=j+1)if(reads[j]<8)$fatal(1,"FAIL bank coverage bank%0d reads%0d",j,reads[j]);
  $display("ACTUAL_BANK_READS %0d %0d %0d %0d %0d",reads[0],reads[1],reads[2],reads[3],reads[4]);
  $display("PASS actual full old-parent staged-reference vs58bank TX198 checks%0d output%0d node%0d nonzero%0d",checks,outputs,node_outputs,nonzero);$finish;
 end
endmodule
