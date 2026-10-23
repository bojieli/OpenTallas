`timescale 1ns/1ps
// Actual synthesizable 47-bit calendar storage on the existing PW10x64 face.
// ME8 records [976..983], SU20 [984..1003], four XPF188 [1004..1015].
// PW0 clears. CAL1/CAL2 carry per-owner stop32; CALS carries counts/stage.
// PW1023 validated dense footer seals after all records and CP payloads.
// All storage here is real FF state; physical parent must census/map it.
module ot_qwen_fixed_issue_dense_pw #(
 parameter integer OWN=1,
 parameter integer DEPTH=(OWN==1)?8:20,
 parameter integer BASE=(OWN==1)?976:984,
 parameter integer SREG=0,
 parameter integer SLATE=0
)(
 input wire clk,input wire rst_n,
 input wire pw_v,input wire [9:0]pw_addr,input wire[63:0]pw_data,
 input wire start,input wire[5:0]stage,
 input wire candidate_v,input wire[11:0]candidate_pc,input wire[1:0]candidate_unit,
 input wire available,input wire end_ok,input wire cp_available,
 output wire issue_v,output wire end_v,output wire[55:0]cp_cmd,output wire cp_v,output wire[11:0]issue_pc,output wire[1:0]issue_unit,
 output wire active,output wire done,output wire[31:0]cycle,output wire image_ready,output wire fault
);
 // Dense profile: PW0 clears; ascending full1024 image, footer1023 seals.
 localparam integer RAW=(DEPTH>1)?$clog2(DEPTH):1;
 reg[46:0]rows[0:DEPTH-1];reg[DEPTH-1:0]valid;
 reg[55:0]cp_rows[0:2];reg[2:0]cp_valid;wire[1:0]cp_index;
 reg[46:0]q;reg[31:0]stop_q;reg[63:0]meta_q;
 reg loading,sealed,stop_seen,meta_seen,cfg_fault,read_fault;
 wire read_en;wire[RAW-1:0]read_addr;wire core_fault;
 wire own_row=pw_addr>=BASE&&pw_addr<BASE+DEPTH;
 wire cp_row=OWN==1&&pw_addr>=1019&&pw_addr<=1021;
 wire[5:0]count=(OWN==1)?meta_q[5:0]:meta_q[11:6];
 integer k,copies;reg seal_bad;
 always @*begin
  seal_bad=!loading||!stop_seen||!meta_seen||meta_q[63:32]!=32'h43414c53||meta_q[31:28]!=0||
           meta_q[27:18]==0||meta_q[27:18]>=61||count==0||count>DEPTH||
           pw_data[63:32]!=32'h58504631||pw_data[31:13]!=0||pw_data[1:0]!=2||
           pw_data[11:6]!=meta_q[17:12]||pw_data[5:2]==0||pw_data[5:2]>4;
  copies=0;
  for(k=0;k<DEPTH;k=k+1)begin
   if(!valid[k])seal_bad=1;
   if(k<count)begin
    if(rows[k][45:44]==3)copies=copies+1;
    if(rows[k][46]!=(k==count-1))seal_bad=1;
   end else if(rows[k]!=0)seal_bad=1;
  end
  if(copies>3||(OWN!=1&&copies!=0))seal_bad=1;
  if(OWN==1)for(k=0;k<3;k=k+1)begin
   if(!cp_valid[k])seal_bad=1;
   if(k<copies)begin
    if(!cp_rows[k][0]||cp_rows[k][55:49]==0||cp_rows[k][55:49]>64)seal_bad=1;
   end else if(cp_rows[k]!=0)seal_bad=1;
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin valid<=0;cp_valid<=0;q<=0;stop_q<=0;meta_q<=0;loading<=0;sealed<=0;stop_seen<=0;meta_seen<=0;cfg_fault<=0;read_fault<=0;end
  else begin
   if(read_en)begin
    if(read_addr<DEPTH&&valid[read_addr])q<=rows[read_addr];else begin q<=0;read_fault<=1;end
   end
   if(pw_v)begin
    if(active)cfg_fault<=1;
    else if(pw_addr==0)begin
     if(loading)cfg_fault<=1;
     else begin valid<=0;cp_valid<=0;loading<=1;sealed<=0;stop_seen<=0;meta_seen<=0;cfg_fault<=0;read_fault<=0;end
    end else if(own_row)begin
     if(!loading||valid[pw_addr-BASE]||pw_data[63:47]!=0)cfg_fault<=1;
     rows[pw_addr-BASE]<=pw_data[46:0];valid[pw_addr-BASE]<=1;
    end else if(pw_addr==((OWN==1)?1016:1018))begin
     if(!loading||stop_seen||pw_data[63:32]!=((OWN==1)?32'h43414c31:32'h43414c32)||pw_data[31:0]==0)cfg_fault<=1;
     stop_q<=pw_data[31:0];stop_seen<=1;
    end else if(pw_addr==1017)begin
     if(!loading||meta_seen)cfg_fault<=1;meta_q<=pw_data;meta_seen<=1;
    end else if(cp_row)begin
     if(!loading||cp_valid[pw_addr-1019]||pw_data[63:56]!=0)cfg_fault<=1;
     cp_rows[pw_addr-1019]<=pw_data[55:0];cp_valid[pw_addr-1019]<=1;
    end else if(pw_addr==1023)begin
     if(seal_bad||cfg_fault)cfg_fault<=1;
     else begin sealed<=1;loading<=0;end
    end
   end
   if(cp_v&&(cp_index>=3||!cp_valid[cp_index]))cfg_fault<=1;
   if(start&&(!sealed||meta_q[17:12]!=stage))cfg_fault<=1;
  end
 end
 ot_qwen_fixed_issue #(.ROW_AW(RAW),.OWN(OWN),.SREG(SREG),.SLATE(SLATE))u_issue(
 .clk(clk),.rst_n(rst_n),.start(start),.stop_cycle(stop_q),.slot_re(read_en),.slot_addr(read_addr),.slot_q(q),
 .candidate_v(candidate_v),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),.available(available),.end_ok(end_ok),.cp_available(cp_available),
 .issue_v(issue_v),.end_v(end_v),.cp_v(cp_v),.cp_index(cp_index),.issue_pc(issue_pc),.issue_unit(issue_unit),.active(active),.done(done),.cycle(cycle),.fault(core_fault));
 assign cp_cmd=OWN==1?{(cp_index<3?cp_rows[cp_index][55:1]:55'd0),cp_v}:56'd0;
 assign image_ready=sealed&&!cfg_fault&&!read_fault;
 assign fault=cfg_fault||read_fault||core_fault;
endmodule

`timescale 1ns/1ps
// QLB-C4b (10-18): the dense OWN 1 calendar with a second, base-selected segment calendar (ot_qwen_fixed_issue_pw SEG 1).
// Gap closed: the head armed its fixed-issue calendar only for a start at programme base 0 and held ONE ME8 calendar
// per image, so an ME programme started at another base (the LM-head programme, stage LAST_STAGE, LOCAL SEG start) had
// no calendar: its ME issues and END could not fire on any compiled cycle.
// Image (dense profile, ascending; the SU20 region [984..1003] is free on the DV head, which has no OWN 2 consumer):
//   [976..983]  ME8 rows of segment 0 (base 0) -- unchanged, CAL1 [1016] stop, CALS [1017] counts / stage
//   [984..991]  ME8 rows of segment G {last [46], unit [45:44] (0 / 1 only), pc [43:32] ABSOLUTE, cycle [31:0]}
//   [992]       CALG {32'h43414c47, stop32 (!= 0)}
//   [993]       CALB {32'h43414c42, 4'b0, count4 [27:24] (1..8), 12'b0, base12 [11:0] (!= 0)}
//   (G absent: [984..993] all zero.)  [994..1003] belong to the DV XPF segment-G loader (qfd_tt_ctlm_dv).
// Start: start_base 0 -> segment 0 exactly as ot_qwen_fixed_issue_dense_pw (every rule, every edge); start_base == CALB
// base with G sealed -> segment G (rows read from [984..], its own stop); any other base -> no calendar start (a decode
// stage's later segments run on the base-0 calendar).  Cycle c of a segment is the c-th edge after its accepted start,
// both segments; PCs stay absolute (candidate_pc = base + pc).  Nothing waits: a G start while active FAULTS (core).
// SMUT (bench negative control, `OT_SEG_MUT): segment G reads the segment-0 rows (no row selection).
module ot_qwen_fixed_issue_seg_pw #(
 parameter integer DEPTH=8,
 parameter integer BASE=976,
 parameter integer SREG=0,
 parameter integer SLATE=0
)(
 input wire clk,input wire rst_n,
 input wire pw_v,input wire [9:0]pw_addr,input wire[63:0]pw_data,
 input wire start,input wire[5:0]stage,
 input wire[11:0]start_base,
 input wire candidate_v,input wire[11:0]candidate_pc,input wire[1:0]candidate_unit,
 input wire available,input wire end_ok,input wire cp_available,
 output wire issue_v,output wire end_v,output wire[55:0]cp_cmd,output wire cp_v,output wire[11:0]issue_pc,output wire[1:0]issue_unit,
 output wire active,output wire done,output wire[31:0]cycle,output wire image_ready,output wire fault
);
 localparam integer RAW=(DEPTH>1)?$clog2(DEPTH):1;
 localparam integer GBASE=BASE+DEPTH;          // 984
 localparam integer GSTOP=GBASE+DEPTH;         // 992 CALG
 localparam integer GDESC=GSTOP+1;             // 993 CALB
 reg[46:0]rows[0:DEPTH-1];reg[DEPTH-1:0]valid;
 reg[46:0]grows[0:DEPTH-1];reg[DEPTH-1:0]gvalid;
 reg[55:0]cp_rows[0:2];reg[2:0]cp_valid;wire[1:0]cp_index;
 reg[46:0]q;reg[31:0]stop_q;reg[63:0]meta_q;
 reg[63:0]gstop_q,gdesc_q;reg gstop_seen,gdesc_seen;
 reg loading,sealed,stop_seen,meta_seen,cfg_fault,read_fault;
 reg seg_q;                                   // the running segment (1 = G)
 wire read_en;wire[RAW-1:0]read_addr;wire core_fault;
 wire own_row=pw_addr>=BASE&&pw_addr<BASE+DEPTH;
 wire g_row=pw_addr>=GBASE&&pw_addr<GBASE+DEPTH;
 wire cp_row=pw_addr>=1019&&pw_addr<=1021;
 wire[5:0]count=meta_q[5:0];
 wire g_present=gdesc_q[63:32]==32'h43414c42;
 wire[3:0]g_count=gdesc_q[27:24];
 wire[11:0]g_base=gdesc_q[11:0];
 // calendar start selection (registered start; the selection is combinational on that edge, as the core's first read)
 wire start_g=sealed&&g_present&&start_base!=12'd0&&start_base==g_base;
 wire start_cal=start&&(start_base==12'd0||start_g);
 wire sel_g=(start_cal&&!active)?(start_base!=12'd0):seg_q;
 integer k,copies;reg seal_bad;
 always @*begin
  seal_bad=!loading||!stop_seen||!meta_seen||meta_q[63:32]!=32'h43414c53||meta_q[31:28]!=0||
           meta_q[27:18]==0||meta_q[27:18]>=61||count==0||count>DEPTH||
           pw_data[63:32]!=32'h58504631||pw_data[31:13]!=0||pw_data[1:0]!=2||
           pw_data[11:6]!=meta_q[17:12]||pw_data[5:2]==0||pw_data[5:2]>4;
  copies=0;
  for(k=0;k<DEPTH;k=k+1)begin
   if(!valid[k])seal_bad=1;
   if(k<count)begin
    if(rows[k][45:44]==3)copies=copies+1;
    if(rows[k][46]!=(k==count-1))seal_bad=1;
   end else if(rows[k]!=0)seal_bad=1;
  end
  if(copies>3)seal_bad=1;
  for(k=0;k<3;k=k+1)begin
   if(!cp_valid[k])seal_bad=1;
   if(k<copies)begin
    if(!cp_rows[k][0]||cp_rows[k][55:49]==0||cp_rows[k][55:49]>64)seal_bad=1;
   end else if(cp_rows[k]!=0)seal_bad=1;
  end
  // segment G: every word written; present = CALB magic with a nonzero base, a 1..DEPTH count, a CALG stop; rows 0 /
  // 1 units only (no CP copy in G), last bit on the final row, zero rows after it.  Absent = every G word zero.
  if(!gstop_seen||!gdesc_seen)seal_bad=1;
  for(k=0;k<DEPTH;k=k+1)if(!gvalid[k])seal_bad=1;
  if(g_present)begin
   if(gdesc_q[31:28]!=0||gdesc_q[23:12]!=0||g_base==0||g_count==0||g_count>DEPTH||
      gstop_q[63:32]!=32'h43414c47||gstop_q[31:0]==0)seal_bad=1;
   for(k=0;k<DEPTH;k=k+1)
    if(k<g_count)begin
     if(grows[k][45]||grows[k][46]!=(k==g_count-1))seal_bad=1;
    end else if(grows[k]!=0)seal_bad=1;
  end else begin
   if(gdesc_q!=0||gstop_q!=0)seal_bad=1;
   for(k=0;k<DEPTH;k=k+1)if(grows[k]!=0)seal_bad=1;
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin valid<=0;gvalid<=0;cp_valid<=0;q<=0;stop_q<=0;meta_q<=0;gstop_q<=0;gdesc_q<=0;gstop_seen<=0;gdesc_seen<=0;
   loading<=0;sealed<=0;stop_seen<=0;meta_seen<=0;cfg_fault<=0;read_fault<=0;seg_q<=0;end
  else begin
   if(read_en)begin
`ifdef OT_SEG_MUT
    if(read_addr<DEPTH&&valid[read_addr])q<=rows[read_addr];else begin q<=0;read_fault<=1;end
`else
    if(sel_g)begin
     if(read_addr<DEPTH&&gvalid[read_addr])q<=grows[read_addr];else begin q<=0;read_fault<=1;end
    end else begin
     if(read_addr<DEPTH&&valid[read_addr])q<=rows[read_addr];else begin q<=0;read_fault<=1;end
    end
`endif
   end
   if(start_cal&&!active)seg_q<=start_base!=12'd0;
   if(pw_v)begin
    if(active)cfg_fault<=1;
    else if(pw_addr==0)begin
     if(loading)cfg_fault<=1;
     else begin valid<=0;gvalid<=0;cp_valid<=0;loading<=1;sealed<=0;stop_seen<=0;meta_seen<=0;gstop_seen<=0;gdesc_seen<=0;
      cfg_fault<=0;read_fault<=0;end
    end else if(own_row)begin
     if(!loading||valid[pw_addr-BASE]||pw_data[63:47]!=0)cfg_fault<=1;
     rows[pw_addr-BASE]<=pw_data[46:0];valid[pw_addr-BASE]<=1;
    end else if(g_row)begin
     if(!loading||gvalid[pw_addr-GBASE]||pw_data[63:47]!=0)cfg_fault<=1;
     grows[pw_addr-GBASE]<=pw_data[46:0];gvalid[pw_addr-GBASE]<=1;
    end else if(pw_addr==GSTOP)begin
     if(!loading||gstop_seen)cfg_fault<=1;gstop_q<=pw_data;gstop_seen<=1;
    end else if(pw_addr==GDESC)begin
     if(!loading||gdesc_seen)cfg_fault<=1;gdesc_q<=pw_data;gdesc_seen<=1;
    end else if(pw_addr==1016)begin
     if(!loading||stop_seen||pw_data[63:32]!=32'h43414c31||pw_data[31:0]==0)cfg_fault<=1;
     stop_q<=pw_data[31:0];stop_seen<=1;
    end else if(pw_addr==1017)begin
     if(!loading||meta_seen)cfg_fault<=1;meta_q<=pw_data;meta_seen<=1;
    end else if(cp_row)begin
     if(!loading||cp_valid[pw_addr-1019]||pw_data[63:56]!=0)cfg_fault<=1;
     cp_rows[pw_addr-1019]<=pw_data[55:0];cp_valid[pw_addr-1019]<=1;
    end else if(pw_addr==1023)begin
     if(seal_bad||cfg_fault)cfg_fault<=1;
     else begin sealed<=1;loading<=0;end
    end
   end
   if(cp_v&&(cp_index>=3||!cp_valid[cp_index]))cfg_fault<=1;
   if(start_cal&&(!sealed||meta_q[17:12]!=stage))cfg_fault<=1;
  end
 end
 ot_qwen_fixed_issue #(.ROW_AW(RAW),.OWN(1),.SREG(SREG),.SLATE(SLATE))u_issue(
 .clk(clk),.rst_n(rst_n),.start(start_cal),.stop_cycle((start_base!=12'd0)?gstop_q[31:0]:stop_q),.slot_re(read_en),.slot_addr(read_addr),.slot_q(q),
 .candidate_v(candidate_v),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),.available(available),.end_ok(end_ok),.cp_available(cp_available),
 .issue_v(issue_v),.end_v(end_v),.cp_v(cp_v),.cp_index(cp_index),.issue_pc(issue_pc),.issue_unit(issue_unit),.active(active),.done(done),.cycle(cycle),.fault(core_fault));
 assign cp_cmd={(cp_index<3?cp_rows[cp_index][55:1]:55'd0),cp_v};
 assign image_ready=sealed&&!cfg_fault&&!read_fault;
 assign fault=cfg_fault||read_fault||core_fault;
endmodule
