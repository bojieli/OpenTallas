`timescale 1ns/1ps
module tb_s81_pq_sequenced_pins;
`ifdef OT_PQ_CTL_CALCAP
 localparam integer DONE_EDGE=36;   // ctl pin-captures calendar/go/i_*: the PQ timeline moves +1 edge
`else
 localparam integer DONE_EDGE=35;
`endif
 reg clk=0;always #3 clk=~clk;
 reg ckv=0;always #4 ckv=~ckv;
 reg ingest_h=0,ingest_i=0;integer phase_h=0,phase_i=0,ingress_words=0,ingress_pops=0;
 initial begin if(!$value$plusargs("phase_h=%d",phase_h))phase_h=0;#(phase_h);forever #3 ingest_h=~ingest_h;end
 initial begin if(!$value$plusargs("phase_i=%d",phase_i))phase_i=0;#(phase_i);forever #3 ingest_i=~ingest_i;end
 always @(posedge ingest_h)if(rst_n&&host.u_h.h_v)ingress_words=ingress_words+1;
 always @(posedge ingest_i)if(rst_n&&host.u_h.host.u_hi.hx_pop)ingress_pops=ingress_pops+1;
 reg rst_n=0;wire[84:0]cmd;wire[35:0]desc;wire prime,start;
 wire[11:0]calendar_base;wire[12:0]calendar_length;
 reg[514:0]host_in=0;wire[76:0]host_out;wire[35:0]host_pw,host_pq;wire[7:0]plen;
 wire[5:0]seq_status;wire[53:0]kit_done;reg[52:0]ks=0;
 wire[291:0]hw;wire[84:0]unused_cmd[0:12];
 dsfd_host_c #(.NS(1)) host(.ck(clk),.rst(rst_n),.ckv(ckv),.rsv(rst_n),
  .f_collective(host_in),.t_collective(host_out),.f_lf(4'b0101),.t_sseq_pw(host_pw),
  .ck_ingest({ingest_i,ingest_h}),.t_pq_pw(host_pq),.t_sseq_plen(plen),.f_sseq_st(seq_status),.f_wfc_ft(4'd0),.hw(hw),.hc(9'd0));
 dsfd_stage_seq_static_c9 #(.NOPS(128),.STAGE(7)) seq(.ck(clk),.rst(rst_n),.ckv(ckv),.rsv(rst_n),
  .f_ks(ks),.t_kd(kit_done),.f_pw(host_pw),.f_plen(plen),.t_st(seq_status),
  .f_pq_pw(host_pq),.t_pq_desc_pw(desc),.calendar_prime(prime),.stage_start(start),
  .calendar_base(calendar_base),.calendar_length(calendar_length),.pq_image_sealed(sealed),
  .pq_calendar_primed(primed),.pq_calendar_fault(calendar_fault),.c13(cmd),.d13(done),.s13(command_status),
  .d0(9'd0),.d1(9'd0),.d2(9'd0),.d3(9'd0),.d4(9'd0),.d5(9'd0),.d6(9'd0),.d7(9'd0),.d12(9'd0),
  .s0(2'd2),.s1(2'd2),.s2(2'd2),.s3(2'd2),.s4(2'd2),.s5(2'd2),.s6(2'd2),.s7(2'd2),.s12(2'd2));
 reg[511:0]host_words[0:2047];reg[31:0]host_cycles[0:2047];
 integer packet_count=0,packet_index=0,serial=-1,fast=-1,launch_edge=-1,cmd_edge=-1,done_edge=-1;
 integer nstarts=0,ncommands=0,ndone=0,nkits=0,boot_seen=0,prime_seen=0;
 initial begin
  $readmemh("host_words.hex",host_words);$readmemh("host_cycles.hex",host_cycles);
  if(!$value$plusargs("packets=%d",packet_count))$fatal(1,"missing actual image count");
  #30;rst_n=1;
 end
 always @(negedge clk)begin
  host_in=0;
  if(packet_index<packet_count&&fast+1==host_cycles[packet_index])begin
   host_in={2'd0,host_words[packet_index],1'b1};packet_index=packet_index+1;
  end
 end
 always @(posedge ckv)begin serial=serial+1;#0.1;if(kit_done[53])nkits=nkits+1;end
 always @(negedge ckv)begin ks=0;if(serial==1003||serial==1048||serial==1093)ks={1'b1,10'd37,21'd21946,21'd1048575};end
 always @(posedge clk)begin
  fast=fast+1;
  if(start)begin launch_edge=fast;nstarts=nstarts+1;end
  if(desc[35])boot_seen=boot_seen+1;
  if(prime)prime_seen=prime_seen+1;
  #0.1;
  if(cmd[84])begin
   ncommands=ncommands+1;cmd_edge=fast;
   if(fast!=launch_edge+1||cmd[30:7]!=0||cmd[6:0]!=0)$fatal(1,"SEQUENCED FAIL actual engine13 issue/payload");
  end
  if(done[8])begin ndone=ndone+1;done_edge=fast;end
  if(xw[0])begin
   valids=valids+1;
   if(xw[561:552]!==10'd514||!xw[551])$fatal(1,"SEQUENCED FAIL native PHW10 payload");
  end
  if(fast==1650)begin
   $display("S81_PQ_SEQUENCED host=%0d boot=%0d prime=%0d start=%0d cmd=%0d done=%0d KIT=%0d valid=%0d J=%0d C=%0d D=%0d seq=%h endpoint=%h cal=%b core=%b hostfault=%b",packet_index,boot_seen,prime_seen,nstarts,ncommands,ndone,nkits,valids,launch_edge,cmd_edge,done_edge,seq_status,command_status,calendar_fault,status[2],host_out[75]);
   if(ingress_words!=12||ingress_pops!=12)$fatal(1,"SEQUENCED FAIL actual ingest clock FIFO phase h=%0d i=%0d words=%0d pops=%0d",phase_h,phase_i,ingress_words,ingress_pops);
   if(packet_index!=packet_count||boot_seen!=7||prime_seen!=4||nstarts!=3||ncommands!=3||ndone!=3||nkits!=3||valids!=3||done_edge!=cmd_edge+37||seq_status[5]||calendar_fault||command_status[0]||status[2]||host_out[75])$fatal(1,"SEQUENCED FAIL real host->c9->PHW10/mappedROM timeline");
   $display("INGEST_PHASE PASS h=%0d i=%0d actual_native_FIFO_words=%0d/pops=%0d",phase_h,phase_i,ingress_words,ingress_pops);
   $display("S81_PQ_SEQUENCED PASS actual host CSR->asyncFIFO->c9 mailbox->engine13->PQ mapped memory; component data zero ROM");$finish;
  end
 end
 wire[8:0]done;wire[1:0]command_status;wire sealed,primed,calendar_fault;
 reg[116:0]descriptor;integer page,valids,completed;
 wire[38:0] status;wire[19:0]vm;wire[11:0]ra0,ra1;
`ifdef DSFD_PQ_ROM4
 wire[11:0]ra2;wire[3:0]rc2;   // the DUT owns the bank select: four real macros, per-macro enable, 4 x 48-bit rd_out
`else
 wire[13:0]ra2;
`endif
 wire[1100:0]xw,xe;wire[457:0]cfg;
 wire[71:0]raw0,raw1,raw2[0:3];reg[1:0]bank;
`ifdef DSFD_PQ_ROM4
 wire[191:0]sq={raw2[3][47:0],raw2[2][47:0],raw2[1][47:0],raw2[0][47:0]};
`else
 wire[47:0]sq=raw2[bank][47:0];
`endif
 integer phase,c,checks=0;
 // These are the actual target ROM functional macros. The immutable images
 // are deliberately zero here: this test qualifies widths/registered routing,
 // not canonical operand/matrix numerical content.
 ot_rom_4096x72_m8 u_phase0(.clk(clk),.ce_in(1'b1),.addr_in(ra0[11:0]),.rd_out(raw0));
 ot_rom_4096x72_m8 u_phase1(.clk(clk),.ce_in(1'b1),.addr_in(ra1[11:0]),.rd_out(raw1));
 for(genvar b=0;b<4;b=b+1)begin:g_stream
`ifdef DSFD_PQ_ROM4
 ot_rom_4096x72_m8 u_stream(.clk(clk),.ce_in(rc2[b]),.addr_in(ra2[11:0]),.rd_out(raw2[b]));
`else
 ot_rom_4096x72_m8 u_stream(.clk(clk),.ce_in(1'b1),.addr_in(ra2[11:0]),.rd_out(raw2[b]));
`endif
 end
`ifndef DSFD_PQ_ROM4
 always @(posedge clk)bank<=ra2[13:12];
`endif
 dsfd_sp_pq_produced dut(.ck_ctl(clk),.ck_qb(clk),.ck_qb_align(clk),.ck_fault(clk),.ck_qb_aux({4{clk}}),.ck_aq({2{clk}}),
 .ck_aq_aux({16{clk}}),.ck_ix({4{clk}}),.ck_ix_read({32{clk}}),.ck_bc({16{clk}}),.ck_lane(clk),
 .rst(rst_n),.ck_cmd(clk),.ck_calendar(clk),.c_cmd(cmd),.f_desc_pw(desc),.c_done(done),.c_st(command_status),.image_sealed(sealed),.calendar_prime(prime),.stage_start(start),.calendar_base(calendar_base),.calendar_length(calendar_length),.calendar_primed(primed),.calendar_fault(calendar_fault),.t_iss(status),.t_vm(vm),.f_vm(2049'd0),
 .ra0(ra0),.ra1(ra1),.ra2(ra2),.rc0(),.rc1(),
`ifdef DSFD_PQ_ROM4
 .rc2(rc2),
`else
 .rc2(),
`endif
.rq0(raw0[63:0]),.rq1(raw1[63:0]),.rq2(sq),
 .t_cnt(cfg),.f_cnt(204'd0),.xw(xw),.xe(xe),.xws(3'b011),.xes(3'b011));

 initial begin valids=0;#12000;$fatal(1,"SEQUENCED FAIL timeout");end
endmodule
