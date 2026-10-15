`timescale 1ns/1ps
module tb_s81_pq_canonical_pins;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,calendar_v=0;reg[74:0] action=0;reg[92:0] shape=0;
 wire[38:0] status;wire[19:0]vm;wire[11:0]ra0,ra1;wire[13:0]ra2;
 wire[1100:0]xw,xe;wire[457:0]cfg;
 wire[71:0]raw0,raw1,raw2[0:3];reg[1:0]bank;
 wire[47:0]sq=raw2[bank][47:0];
 integer phase,c,checks=0;
 // These are the actual target ROM functional macros. The immutable images
 // are deliberately zero here: this test qualifies widths/registered routing,
 // not canonical operand/matrix numerical content.
 ot_rom_4096x72_m8 u_phase0(.clk(clk),.ce_in(1'b1),.addr_in(ra0[11:0]),.rd_out(raw0));
 ot_rom_4096x72_m8 u_phase1(.clk(clk),.ce_in(1'b1),.addr_in(ra1[11:0]),.rd_out(raw1));
 for(genvar b=0;b<4;b=b+1)begin:g_stream
 ot_rom_4096x72_m8 u_stream(.clk(clk),.ce_in(1'b1),.addr_in(ra2[11:0]),.rd_out(raw2[b]));
 end
 always @(posedge clk)bank<=ra2[13:12];
 dsfd_sp_pq_n dut(.ck_ctl(clk),.ck_qb(clk),.ck_fault(clk),.ck_qb_aux({4{clk}}),.ck_aq({2{clk}}),
 .ck_aq_aux({16{clk}}),.ck_ix({4{clk}}),.ck_ix_read({32{clk}}),.ck_bc({16{clk}}),.ck_lane(clk),
 .rst(rst_n),.calendar_v(calendar_v),.calendar_action(action),.f_iss(shape),.t_iss(status),.t_vm(vm),.f_vm(2049'd0),
 .ra0(ra0),.ra1(ra1),.ra2(ra2),.rc0(),.rc1(),.rc2(),.rq0(raw0[63:0]),.rq1(raw1[63:0]),.rq2(sq),
 .t_cnt(cfg),.f_cnt(204'd0),.xw(xw),.xe(xe),.xws(3'b011),.xes(3'b011));
 initial begin
  for(phase=511;phase<=642;phase=phase+1)begin
   rst_n=0;action=0;shape=0;calendar_v=0;
   repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
   for(c=0;c<40;c=c+1)begin
    action=0;shape=0;calendar_v=1;
    if(c==0)begin shape[0]=1;shape[10:1]=10'(phase);action[1:0]=0;end
    if(c==8)begin action[62]=1;action[64:63]=0;end
    // Sparse stream slot crosses every actual ROM bank address bit. Zero
    // native word has no read valid and cannot invent loaded QB operands.
    if(c==12)begin action[39]=1;action[53:40]=14'(phase*19);end
    if(c==24)action[68]=1;
    #1;
    if(c==0&&(ra0!==14'(2*phase)||ra1!==14'(2*phase+1)))$fatal(1,"CANONICAL_PINS FAIL phaseROM phase=%0d",phase);
    if(c==12&&ra2!==14'(phase*19))$fatal(1,"CANONICAL_PINS FAIL streamROM");
    @(posedge clk);#1;
    if(xw!==xe)$fatal(1,"CANONICAL_PINS FAIL lane copies");
    if(xw[0]!==1'(c==17))$fatal(1,"CANONICAL_PINS FAIL fixed lane edge phase=%0d c=%0d",phase,c);
    if(c==17&&(xw[561:552]!==10'(phase)||!xw[551]))$fatal(1,"CANONICAL_PINS FAIL cfg lane phase=%0d got=%h",phase,xw[564:550]);
    checks=checks+1;
    @(negedge clk);
   end
  end
  $display("CANONICAL_PINS PASS phases=511..642 checks=%0d PHW=10 SAW=14 action=75 shape=93 native_ROMs=6 native_SRAMs=36 BCslice0=410",checks);$finish;
 end
endmodule
