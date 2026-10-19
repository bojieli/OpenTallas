`default_nettype none
// HBM-NEXT-UNITS-IDX 2026-10-19: N-row IDX.INDEX microprogram issuer (successor of ot_hbm_idx_calendar_static for the
// HGI-1R row field). The programme SRAM holds ONE row frame (length F <= 2048 instructions, the d4g instruction format
// unchanged: [31]weight [30]query [29]heademit [28]keybeat [27:20]index [19:16]selop [15:14]pass [13:6]seladdr
// [5]linkflush [4]linkemit [3:0]linkgroup; NEW: [5]&[4] together = link clear, never emitted by the d4g compiler).
// Row r (r = 0 .. N-1) is the same frame launched r x pitch edges after start (pitch = compiled row II + rgap, from the
// record): instruction(t) = OR over the active rows of frame[t - r*pitch]. Two streams (row parity) with two copies of
// the frame SRAM (both written by the programme load) -> at most 2 rows overlap: the compiler guarantees
// pitch >= ceil(F / 2); a launch onto a busy stream FAULTS. Every edge on which both streams issue is checked for a
// field-class collision (index/flag field, selector field, link field): collision = fault (static schedule, no
// arbitration, no ready/credit). Stream timing is the d4g issuer's exactly (start -> first issue 3 edges), so N = 1 with
// the d4g programme reproduces ot_hbm_idx_calendar_static edge for edge.
// row_start = start | launch(r>0): the per-row frame start, at the same relative edge the d4g parent saw `start`.
module ot_hnx_idx_calendar_rows(
 input wire clk,clk_mem,rst_n,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,input wire[4:0]n_rows,input wire[11:0]pitch,
 output wire issue_v,output wire[31:0]instruction,output wire row_start,output wire done,output reg fault
);
 reg[4:0]rows_left;reg[11:0]timer;reg launch_par;
 wire launch=!start&&rows_left!=0&&timer==pitch;
 assign row_start=start||launch;
 wire[1:0]go={launch&&launch_par,start||(launch&&!launch_par)};
 wire[1:0]sv;wire[63:0]si;wire[1:0]sd,sf;
 for(genvar s=0;s<2;s=s+1)begin:gs
  reg active;reg[11:0]pc,limit;reg read_v,read_last;reg[2:0]word_index;reg iv,dn,ft;reg[31:0]ins;
  wire[255:0]raw;
  ot_sram_1r1w_256x256_m2_r2c2 store(.clk(clk_mem),.r_ce_in(active),.r_addr_in(pc[10:3]),.rd_out(raw),
   .w_ce_in(program_we),.w_addr_in(program_addr),.wd_in(program_data),.w_mask_in({256{1'b1}}),
   .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin active<=0;pc<=0;limit<=0;read_v<=0;read_last<=0;word_index<=0;iv<=0;ins<=0;dn<=0;ft<=0;end
   else begin
    iv<=read_v;dn<=read_v&&read_last;ins<=raw[word_index*32+:32];
    read_v<=active;word_index<=pc[2:0];read_last<=pc+1==limit;
    if(go[s])begin active<=1;pc<=0;limit<=length;if(active||read_v||length==0||length>2048)ft<=1;end
    else if(active)begin pc<=pc+1;if(pc+1==limit)active<=0;end
    if(program_we&&(active||read_v))ft<=1;
   end
  end
  assign sv[s]=iv;assign si[s*32+:32]=iv?ins:32'd0;assign sd[s]=dn;assign sf[s]=ft;
 end
 assign issue_v=|sv;
 assign instruction=si[31:0]|si[63:32];
 wire[31:0]a=si[31:0],b=si[63:32];
 wire collide=(&sv)&&(((|a[31:28])&&(|b[31:28]))||((|a[19:6])&&(|b[19:6]))||((|a[5:0])&&(|b[5:0])));
 reg[4:0]dones_left;
 assign done=(|sd)&&dones_left==5'd1;          // the last row's last issue edge (= the d4g done edge at N = 1)
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rows_left<=0;timer<=0;launch_par<=0;dones_left<=0;fault<=0;end
  else begin
   if(start)begin
    rows_left<=n_rows-5'd1;timer<=12'd1;launch_par<=1'b1;dones_left<=n_rows;
    if(n_rows==0||n_rows>16||(n_rows>1&&pitch==0)||rows_left!=0||dones_left!=0)fault<=1;
   end else begin
    timer<=launch?12'd1:timer+12'd1;
    if(launch)begin rows_left<=rows_left-5'd1;launch_par<=!launch_par;end
   end
   if((|sd)&&dones_left!=0&&!start)dones_left<=dones_left-5'(int'(sd[0])+int'(sd[1]));
   if((|sf)||collide)fault<=1;
  end
 end
endmodule
`default_nettype wire
