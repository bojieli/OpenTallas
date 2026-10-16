`timescale 1ns/1ps
`default_nettype none
// Additive HC programme source. One actual via ROM holds eleven72-bit words
// per actual command op7. The source command itself is retained, never rebuilt
// from an expected result. Bundle layout, low to high: y_tag32, scalar_age32,
// ss_age32, done_age32, POST_AGES640, reserved24. All eleven reads and both
// delivery edges are fixed. Faults diagnose and never delay/retry execution.
// Required related-clock epoch: stream first active edge and serial first
// active edge coincide; periods are3:4, and commands arrive on stream phase0.
// Source P -> ROM rows launch P..P+10, capture P+2..P+12; lease P+16..P+20.
// Serial phase2 captures once, at P+56/3 stream periods = P+14 serial periods.
// Exact phase/clock arrival and pin placement must be measured before adoption.
module ot_s81_hc_programme_source #(
 parameter string IMAGE="", parameter integer MUT=0, RAW_ROM_CLOCK=0
)(
 input wire stream_ck,stream_rst_n,serial_ck,serial_rst_n,rom_ck,
 input wire command_v,input wire[83:0]command_d,
 output reg hc_v,output reg[83:0]hc_d,
 output reg[31:0]hc_done_age,hc_ss_age,hc_scalar_age,hc_y_tag,
 output reg[639:0]hc_post_ages,
 output wire fault
);
 reg[1:0]sp,dp;reg active,lease;reg[4:0]age;
 reg[11:0]base,rom_addr;wire[71:0]rom_word;
 reg[791:0]assembled;reg[83:0]saved_command;
 wire macro_ck = RAW_ROM_CLOCK!=0 ? rom_ck : stream_ck;
 reg stream_fault,serial_fault;
 assign fault=stream_fault|serial_fault;
 ot_rom_4096x72_m8 #(.VIAMAP(IMAGE),.INSTANCE("hc_programme"))u_rom(
  .clk(macro_ck),.ce_in(1'b1),.addr_in(rom_addr),.rd_out(rom_word));
 always @(posedge stream_ck or negedge stream_rst_n)begin
  if(!stream_rst_n)begin
   sp<=0;active<=0;lease<=0;age<=0;base<=0;rom_addr<=0;
   assembled<=0;saved_command<=0;stream_fault<=0;
  end else begin
   sp<=sp+1'b1;
   if(active)begin
    age<=age+1'b1;
    if(age<10)rom_addr<=base+age+1'b1;
    if(age>=1&&age<=11)assembled[(age-1)*72+:72]<=rom_word;
    if(age==15)begin
     lease<=1;
     if(assembled[791:768]!=0)stream_fault<=1;
    end
    if(age==19)begin lease<=0;active<=0;end
   end
   if(command_v)begin
    if(active||sp!=0)stream_fault<=1;
    // Even a bad programme executes at its fixed edge and raises fault.
    active<=1;age<=0;lease<=0;
    base<=12'(command_d[6:0]*11);rom_addr<=12'(command_d[6:0]*11);
    saved_command<=command_d;
   end
  end
 end
 always @(posedge serial_ck or negedge serial_rst_n)begin
  if(!serial_rst_n)begin
   dp<=0;hc_v<=0;hc_d<=0;hc_done_age<=0;hc_ss_age<=0;
   hc_scalar_age<=0;hc_y_tag<=0;hc_post_ages<=0;serial_fault<=0;
  end else begin
   dp<=dp==2?0:dp+1'b1;hc_v<=0;
   if(dp==(MUT==1?1:2)&&lease)begin
    hc_v<=1;hc_d<=saved_command;
    {hc_post_ages,hc_done_age,hc_ss_age,hc_scalar_age,hc_y_tag}<=assembled[767:0];
    if(MUT==2)hc_y_tag<=assembled[31:0]^32'd1;
   end
  end
 end
endmodule
`default_nettype wire
