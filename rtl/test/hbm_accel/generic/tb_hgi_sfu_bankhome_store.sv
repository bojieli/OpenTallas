`timescale 1ns/1ps
module tb_hgi_sfu_bankhome_store;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0;
 reg[3:0]scalar_load=0,scalar_enable=0;
 reg[95:0]scalar_addr=0;reg[127:0]scalar_data=0;
 reg[63:0]rd_re=0;reg[1535:0]rd_addr=0;reg[127:0]rd_src=0;
 reg[15:0]vm_we=0;reg[383:0]vm_waddr=0;reg[511:0]vm_wdata=0;
 reg[7:0]stage_v=0;reg[15:0]stage_group=0;reg[119:0]stage_addr=0;
 reg[63:0]stage_mask='1;reg[2047:0]stage_data=0;
 reg[1:0]drain_v=0;reg[29:0]drain_addr=0;
 wire[2047:0]g_rd_q,d_rd_q;wire[511:0]g_drain_data,d_drain_data;
 wire[1:0]g_drain_result_v,d_drain_result_v;wire g_fault,d_fault;
 parameter MUT=0;
ot_hgi_sfu_static_operand_store g(
 .clk(clk),.rst_n(rst_n),
.scalar_load(scalar_load),
.scalar_enable(scalar_enable),
.scalar_addr(scalar_addr),
.scalar_data(scalar_data),
.rd_re(rd_re),
.rd_addr(rd_addr),
.rd_src(rd_src),
.vm_we(vm_we),
.vm_waddr(vm_waddr),
.vm_wdata(vm_wdata),
.stage_v(stage_v),
.stage_group(stage_group),
.stage_addr(stage_addr),
.stage_mask(stage_mask),
.stage_data(stage_data),
.drain_v(drain_v),
.drain_addr(drain_addr),
.rd_q(g_rd_q),
.drain_data(g_drain_data),
.drain_result_v(g_drain_result_v),
.fault(g_fault));
ot_hgi_sfu_bankhome_store #(.MUT(MUT)) d(
 .clk_home({4{clk}}),.rst_n(rst_n),
.scalar_load(scalar_load),
.scalar_enable(scalar_enable),
.scalar_addr(scalar_addr),
.scalar_data(scalar_data),
.rd_re(rd_re),
.rd_addr(rd_addr),
.rd_src(rd_src),
.vm_we(vm_we),
.vm_waddr(vm_waddr),
.vm_wdata(vm_wdata),
.stage_v(stage_v),
.stage_group(stage_group),
.stage_addr(stage_addr),
.stage_mask(stage_mask),
.stage_data(stage_data),
.drain_v(drain_v),
.drain_addr(drain_addr),
.rd_q(d_rd_q),
.drain_data(d_drain_data),
.drain_result_v(d_drain_result_v),
.fault(d_fault));

 reg[2047:0]hist_rd[0:2];reg[511:0]hist_drain[0:2];
 reg[63:0]hist_en[0:2];reg[1:0]hist_rv[0:2];reg hist_fault[0:2];
 integer warmed=0,checks=0,errors=0,oracle=0,cycle=0;
 reg monitor=1;
 always @(posedge clk) begin
 #1;cycle++;
 if(!rst_n)warmed=0;
 else begin
  if(warmed>=3)begin
   for(integer l=0;l<64;l++)if(hist_en[2][l])begin
    checks++;
    if(d_rd_q[32*l+:32]!==hist_rd[2][32*l+:32])begin
     errors++;if(errors<8)$display("RD_MISMATCH cycle=%0d port=%0d got=%h exp=%h",cycle,l,d_rd_q[32*l+:32],hist_rd[2][32*l+:32]);
    end
   end
   checks+=2;
   if(d_drain_result_v!==hist_rv[2])begin errors++;if(errors<8)$display("DRAIN_PHASE %0d got%h exp%h",cycle,d_drain_result_v,hist_rv[2]);end
   for(integer s=0;s<2;s++)if(hist_rv[2][s])begin
    checks+=8;if(d_drain_data[256*s+:256]!==hist_drain[2][256*s+:256])begin errors++;if(errors<8)$display("DRAIN_DATA %0d slot%0d",cycle,s);end
   end
   if(d_fault!==hist_fault[2])begin errors++;if(errors<8)$display("FAULT_PHASE %0d got%b exp%b",cycle,d_fault,hist_fault[2]);end
  end
  warmed++;
 end
 for(integer h=2;h>0;h--)begin hist_rd[h]=hist_rd[h-1];hist_drain[h]=hist_drain[h-1];hist_en[h]=hist_en[h-1];hist_rv[h]=hist_rv[h-1];hist_fault[h]=hist_fault[h-1];end
 hist_rd[0]=g_rd_q;hist_drain[0]=g_drain_data;hist_en[0]=rd_re;hist_rv[0]=g_drain_result_v;hist_fault[0]=g_fault;
 end
 function automatic[31:0]value(input integer g,a);value=32'h3e000000+32'(100000*g+a*7);endfunction
 task tick;begin @(negedge clk);end endtask
 task clear_cmd;begin rd_re=0;vm_we=0;stage_v=0;drain_v=0;scalar_load=0;scalar_enable=0;rd_src=0;end endtask
 task reset_fault;begin clear_cmd();rst_n=0;repeat(6)tick();rst_n=1;repeat(6)tick();end endtask
 initial begin
 repeat(6)tick();rst_n=1;repeat(6)tick();
 // Eight sectors/edge, all80 macros exercised; four4096word operands.
 for(integer beat=0;beat<256;beat++)begin
  stage_v='1;
  for(integer s=0;s<8;s++)begin
   stage_group[2*s+:2]=2'(s/2);stage_addr[15*s+:15]=15'(16*beat+(s%2)*8);
   for(integer j=0;j<8;j++)stage_data[256*s+32*j+:32]=value(s/2,16*beat+(s%2)*8+j);
  end
  tick();
 end
 stage_v=0;
 for(integer beat=0;beat<256;beat++)begin
  vm_we='1;
  for(integer l=0;l<16;l++)begin vm_waddr[24*l+:24]=24'(16*beat+l);vm_wdata[32*l+:32]=value(4,16*beat+l);end
  tick();
 end
 vm_we=0;repeat(6)tick();
 // Own, swap, bothhalf candidates andlane0-any;64wordreads/edge sustained.
 for(integer mode=0;mode<4;mode++)begin
  for(integer beat=0;beat<256;beat++)begin
   rd_re='1;
   for(integer l=0;l<16;l++)for(integer g=0;g<4;g++)begin:addr_gen
    integer b;b=mode==0?l:mode==1?(l^1):mode==2?(l/2):(l/2+8);
    if(l==0)b=beat%16;
    rd_addr[24*(4*l+g)+:24]=24'(beat*16+b);
   end
   @(posedge clk);#2;
   for(integer l=0;l<16;l++)for(integer g=0;g<4;g++)begin
    oracle++;if(g_rd_q[32*(4*l+g)+:32]!==value(g,rd_addr[24*(4*l+g)+:24]))$fatal(1,"GOLD_ORACLE");
   end
   tick();
  end
 end
 rd_re=0;
 for(integer beat=0;beat<256;beat++)begin drain_v=3;drain_addr={15'(beat*16+8),15'(beat*16)};tick();end
 drain_v=0;repeat(6)tick();
 // Masked stage writes: mutateeachbyteposition, thenreadallbanks.
 stage_v=1;stage_group=0;stage_addr=15'd0;stage_mask=64'h55;
 for(integer j=0;j<8;j++)stage_data[32*j+:32]=32'h55aa0000+j;
 tick();stage_v=0;repeat(5)tick();rd_re='1;rd_addr=0;
 for(integer l=0;l<16;l++)for(integer g=0;g<4;g++)rd_addr[24*(4*l+g)+:24]=24'(l);
 tick();rd_re=0;repeat(6)tick();
 // Scalarbroadcast state andidentity.
 scalar_load=15;scalar_enable=15;
 for(integer g=0;g<4;g++)begin scalar_addr[24*g+:24]=24'(18000+g);scalar_data[32*g+:32]=32'h3f000000+g;end
 tick();scalar_load=0;rd_re='1;
 for(integer l=0;l<16;l++)for(integer g=0;g<4;g++)rd_addr[24*(4*l+g)+:24]=24'(18000+g);
 repeat(12)tick();rd_re=0;repeat(8)tick();if(g_fault||d_fault)$fatal(1,"UNEXPECTED_LEGAL_FAULT");
 // Independent malformedcommands: exactstickyfaultphase mustmatch, no retry.
 for(integer bad=0;bad<6;bad++)begin
  reset_fault();
  case(bad)
   0:begin rd_re=1;rd_addr[23:0]=32768;end
   1:begin rd_re=1;rd_src[1:0]=1;end
   2:begin rd_re=64'h10;rd_addr[24*4+:24]=7;end
   3:begin rd_re=64'h11;rd_addr[23:0]=0;rd_addr[24*4+:24]=16;end
   4:begin stage_v=3;stage_group=0;stage_addr=0;stage_mask='1;end
   5:begin scalar_enable=1;rd_re=1;rd_addr[23:0]=18099;end
  endcase
  tick();clear_cmd();repeat(12)tick();
  if(!g_fault||!d_fault)$fatal(1,"FAULT_NOT_RAISED bad=%0d",bad);
 end
 repeat(8)tick();
 $display("SFU_BANKHOME checks=%0d oracle=%0d errors=%0d macros_perDUT=80 roots=4 latency=4 delta=3 MUT=%0d",checks,oracle,errors,MUT);
 if(errors)$fatal(1,"SFU_BANKHOME FAIL");
 $display("SFU_BANKHOME PASS");$finish;
 end
endmodule
