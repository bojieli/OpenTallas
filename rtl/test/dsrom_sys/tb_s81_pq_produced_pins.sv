`timescale 1ns/1ps
module tb_s81_pq_produced_pins;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[84:0]cmd=0;reg[35:0]desc=0;reg prime=0,start=0;
 wire[8:0]done;wire[1:0]command_status;wire sealed,primed,calendar_fault;
 reg[116:0]descriptor;integer page,valids,completed;
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
 dsfd_sp_pq_produced dut(.ck_ctl(clk),.ck_qb(clk),.ck_qb_align(clk),.ck_fault(clk),.ck_qb_aux({4{clk}}),.ck_aq({2{clk}}),
 .ck_aq_aux({16{clk}}),.ck_ix({4{clk}}),.ck_ix_read({32{clk}}),.ck_bc({16{clk}}),.ck_lane(clk),
 .rst(rst_n),.ck_cmd(clk),.ck_calendar(clk),.c_cmd(cmd),.f_desc_pw(desc),.c_done(done),.c_st(command_status),.image_sealed(sealed),.calendar_prime(prime),.stage_start(start),.calendar_base(12'd0),.calendar_length(13'd4),.calendar_primed(primed),.calendar_fault(calendar_fault),.t_iss(status),.t_vm(vm),.f_vm(2049'd0),
 .ra0(ra0),.ra1(ra1),.ra2(ra2),.rc0(),.rc1(),.rc2(),.rq0(raw0[63:0]),.rq1(raw1[63:0]),.rq2(sq),
 .t_cnt(cfg),.f_cnt(204'd0),.xw(xw),.xe(xe),.xws(3'b011),.xes(3'b011));
 task write_desc(input[35:0]word);
  @(negedge clk);desc=word|36'h800000000;
 endtask
 initial begin
  for(phase=511;phase<=514;phase=phase+1)begin
   rst_n=0;cmd=0;desc=0;prime=0;start=0;valids=0;completed=0;
   repeat(8)@(negedge clk);rst_n=1;repeat(8)@(negedge clk);
   descriptor=117'(phase)|(117'd34<<91);
   write_desc((36'd7<<25)|1);
   for(page=0;page<5;page=page+1)write_desc((36'(page)<<25)|36'((descriptor>>(24*page))&24'hffffff));
   write_desc((36'd7<<25)|(36'd1<<24)|1);
   @(negedge clk);desc=0;repeat(70)@(negedge clk);
   if(!sealed)$fatal(1,"PRODUCED FAIL descriptor seal");
   prime=1;@(negedge clk);prime=0;repeat(10)@(negedge clk);
   if(!primed)$fatal(1,"PRODUCED FAIL fixed prime");
   cmd=85'd1<<84;start=1;
   for(c=0;c<70;c=c+1)begin
    @(posedge clk);#1;
    if(c==1&&(ra0!==12'(2*phase)||ra1!==12'(2*phase+1)))$fatal(1,"PRODUCED FAIL hardware descriptor phase=%0d ra=%0d",phase,ra0);
    if(xw!==xe)$fatal(1,"PRODUCED FAIL duplicate lanes");
    if(xw[0])begin
     valids=valids+1;
     if(xw[561:552]!==10'(phase)||!xw[551])$fatal(1,"PRODUCED FAIL native config payload");
    end
    if(done[8])begin
     if(c!=35)$fatal(1,"PRODUCED FAIL fixed completion edge c=%0d",c);
     completed=completed+1;end
    if(calendar_fault||command_status[0]||status[2])$fatal(1,"PRODUCED FAIL faults c=%0d cal=%d cmd=%d core=%d",c,calendar_fault,command_status[0],status[2]);
    checks=checks+1;
    @(negedge clk);cmd=0;start=0;
   end
   if(valids!=1||completed!=1)$fatal(1,"PRODUCED FAIL lost hardware commands %0d/%0d",valids,completed);
  end
  $display("PRODUCED PASS actual descriptor->PQ+pairedROM calendar phases511..514 checks=%0d",checks);$finish;
 end
endmodule
