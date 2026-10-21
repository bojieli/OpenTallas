`timescale 1ns/1ps
// QW-H16V 10-20 (safe32 head h16v): log-depth copies of the SEG fixed-issue path, used ONLY by the safe32 head
// (qfd_tt_ctlm_head_static_rk_safe32).  ot_qwen_fixed_issue_pw_ld / _seg_pw_ld / ot_qwen_fixed_issue_ld are the text of
// ot_qwen_fixed_issue_pw.sv / ot_qwen_fixed_issue_dense_pw.sv (seg_pw) / ot_qwen_fixed_issue.sv with the marked
// QW-H16V restructures (exact, 0 edges); the shared originals are unchanged.
// Actual synthesizable 47-bit calendar storage on the existing PW10x64 face.
// ME8 records [976..983], SU20 [984..1003], four XPF188 [1004..1015].
// PW1016 CAL1 begins ME; PW1018 CAL2 begins SU, each with its own stop32.
// PW1017 CALS {magic32,zero4,program_words10,stage6,su_count6,me_count6} seals it.
// All storage here is real FF state; physical parent must census/map it.
module ot_qwen_fixed_issue_pw_ld #(
 parameter integer DENSE_IMAGE=0,
 parameter integer OWN=1,
 parameter integer DEPTH=(OWN==1)?8:20,
 parameter integer BASE=(OWN==1)?976:984,
 parameter integer SREG=0,
 parameter integer SLATE=0,
 // SEG (QLB-C4b 10-18, opt-in, 0 = as built; DENSE_IMAGE 1 + OWN 1 only): per-segment calendar.  A start whose
 // start_base (the programme base of the segment start) is 0 runs the ME8 rows [976..983] exactly as built; a start at
 // the base named by the image's CALB word [993] runs the segment-G rows [984..991] with their own stop (CALG [992]).
 // Any other start_base is not a calendar start (the decode stage's later segments continue the base-0 calendar).
 // See ot_qwen_fixed_issue_seg_pw (ot_qwen_fixed_issue_dense_pw.sv).  start_base is ignored when SEG = 0.
 parameter integer SEG=0,
 // QW-H16X (10-20, default 0 = h16v; SEG only): pre-registered calendar row write decode (from pw_addr_pre = pw_addr one
 // edge earlier), g_present registered with gdesc_q, the next-row compare as a late select.  Exact, 0 edges.
 // QW-H16Y (10-21): H16X = 2 adds (a) the calendar start compares registered one edge early from start_base_pre
 // (start_base = start_base_pre delayed one edge, no reset), (b) the calendar read register q loaded every edge with a
 // late start/run select (q is consumed only on the edge after a read: pending), (c) the issue fault split in two sticky
 // halves.  Exact at every consumer, 0 edges.
 parameter integer H16X=0
)(
 input wire clk,input wire rst_n,
 input wire pw_v,input wire [9:0]pw_addr,input wire[63:0]pw_data,
 input wire [9:0]pw_addr_pre,
 input wire start,input wire[5:0]stage,
 input wire[11:0]start_base,
 input wire[11:0]start_base_pre,
 input wire candidate_v,input wire[11:0]candidate_pc,input wire[1:0]candidate_unit,
 input wire available,input wire end_ok,input wire cp_available,
 output wire issue_v,output wire end_v,output wire[55:0]cp_cmd,output wire cp_v,output wire[11:0]issue_pc,output wire[1:0]issue_unit,
 output wire active,output wire done,output wire[31:0]cycle,output wire image_ready,output wire fault
);
 generate if(SEG!=0)begin:g_seg
 if(DENSE_IMAGE==0||OWN!=1)begin:g_bad initial $error("ot_qwen_fixed_issue_pw SEG needs DENSE_IMAGE 1, OWN 1"); end
 ot_qwen_fixed_issue_seg_pw_ld #(.DEPTH(DEPTH),.BASE(BASE),.SREG(SREG),.SLATE(SLATE),.H16X(H16X))u_store(.*);
 end else if(DENSE_IMAGE!=0)begin:g_dense
 ot_qwen_fixed_issue_dense_pw #(.OWN(OWN),.DEPTH(DEPTH),.BASE(BASE),.SREG(SREG),.SLATE(SLATE))u_store(.*);
 end else begin:g_stream
 ot_qwen_fixed_issue_stream_pw #(.OWN(OWN),.DEPTH(DEPTH),.BASE(BASE),.SREG(SREG),.SLATE(SLATE))u_store(.*);
 end endgenerate
endmodule

module ot_qwen_fixed_issue_seg_pw_ld #(
 parameter integer DEPTH=8,
 parameter integer BASE=976,
 parameter integer SREG=0,
 parameter integer SLATE=0,
 parameter integer H16X=0
)(
 input wire clk,input wire rst_n,
 input wire pw_v,input wire [9:0]pw_addr,input wire[63:0]pw_data,
 input wire [9:0]pw_addr_pre,
 input wire start,input wire[5:0]stage,
 input wire[11:0]start_base,
 input wire[11:0]start_base_pre,
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
 reg gp_r;                                    // QW-H16X: gdesc_q[63:32]==CALB, loaded with gdesc_q (reset 0 = 0 != CALB)
 wire g_present=(H16X!=0)?gp_r:(gdesc_q[63:32]==32'h43414c42);
 // QW-H16X: the calendar row write decode one edge early (pw_addr = pw_addr_pre delayed one edge, no reset: u_isd), so
 // the 2 x 8 x 47 row registers take a registered one-hot write select (h16v: q_pw_addr -> decode -> 376 enables, -151 ps)
 reg[DEPTH-1:0] own_oh_r,g_oh_r;
 always @(posedge clk)begin:b_oh
  integer j;
  for(j=0;j<DEPTH;j=j+1)begin own_oh_r[j]<=pw_addr_pre==BASE+j; g_oh_r[j]<=pw_addr_pre==BASE+DEPTH+j; end
 end
`ifndef SYNTHESIS
 always @(posedge clk) if(H16X!=0&&rst_n)begin:b_ohchk
  integer j;
  for(j=0;j<DEPTH;j=j+1) if(own_oh_r[j]!==(pw_addr==BASE+j)||g_oh_r[j]!==(pw_addr==BASE+DEPTH+j))
   $fatal(1,"H16X calendar write decode %0d diverged",j);
  if(gp_r!==(gdesc_q[63:32]==32'h43414c42)) $fatal(1,"H16X g_present diverged");
 end
`endif
 wire[3:0]g_count=gdesc_q[27:24];
 wire[11:0]g_base=gdesc_q[11:0];
 // calendar start selection (registered start; the selection is combinational on that edge, as the core's first read)
 // QW-H16Y (H16X >= 2): start_base==0 and start_base==g_base (start_base != 0) registered one edge early: start_base is
 // start_base_pre delayed one edge (u_isd, IS 1); g_base's next state = the GDESC write of this edge (pw_v && !active &&
 // pw_addr == GDESC, the only writer; reset holds gdesc_q at 0 while these flops keep sampling).  h16x: g_base -> 12-b
 // compare -> start_cal -> sel_g / read enable fan-out -> q -227.9 ps TT.
 reg sbz_r,sbg_r;
 wire[11:0] g_base_n=(pw_v&&!active&&pw_addr==GDESC)?pw_data[11:0]:g_base;
 always @(posedge clk)begin sbz_r<=start_base_pre==12'd0; sbg_r<=start_base_pre!=12'd0&&start_base_pre==g_base_n; end
 wire sb_z=(H16X>=2)?sbz_r:(start_base==12'd0);
 wire sbm_g=(H16X>=2)?sbg_r:(start_base!=12'd0&&start_base==g_base);
 wire start_g=sealed&&g_present&&sbm_g;
 wire start_cal=start&&(sb_z||start_g);
 wire sel_g=(start_cal&&!active)?!sb_z:seg_q;
`ifndef SYNTHESIS
 always @(posedge clk) if(H16X>=2&&rst_n&&(sbz_r!==(start_base==12'd0)||sbg_r!==(start_base!=12'd0&&start_base==g_base)))
  $fatal(1,"H16Y early start compare diverged: %b/%b start_base %0d g_base %0d",sbz_r,sbg_r,start_base,g_base);
`endif
 integer k;reg seal_bad;
 // QW-H16V (10-20): copies = #{k < min(count,DEPTH) : rows[k][45:44]==3} enters seal_bad only as copies >= 1..4.  The
 // as-built loop accumulated it serially over the 8 rows after the k<count masks (h16t: count -> cfg_fault 35 levels,
 // -300 ps TT).  Here the thresholds of every row prefix (registered rows only, popcount trees) are precomputed and
 // count only selects the prefix (one-hot of min(count,DEPTH)).  Exact, 0 edges.
 if(DEPTH>8)begin:g_dbad initial $error("ot_qwen_fixed_issue_seg_pw_ld: DEPTH <= 8"); end
 wire[DEPTH-1:0] c3;
 genvar gj;
 for(gj=0;gj<DEPTH;gj=gj+1)begin:g_c3 assign c3[gj]=rows[gj][45:44]==3; end
 wire[4*(DEPTH+1)-1:0] pth;                   // pth[4*j+m-1] = popcount(c3[j-1:0]) >= m, m = 1..4
 for(gj=0;gj<=DEPTH;gj=gj+1)begin:g_pth
  wire[DEPTH-1:0] mk=c3&~({DEPTH{1'b1}}<<gj);
  wire[7:0] m8=8'(mk);                        // popcount tree (DEPTH <= 8): 4 x 2-bit, 2 x 3-bit, 1 x 4-bit
  wire[1:0] s2a=m8[0]+m8[1], s2b=m8[2]+m8[3], s2c=m8[4]+m8[5], s2d=m8[6]+m8[7];
  wire[2:0] s3a=s2a+s2b, s3b=s2c+s2d;
  wire[3:0] pc=s3a+s3b;
  assign pth[4*gj+:4]={pc>=4,pc>=3,pc>=2,pc>=1};
 end
 wire[DEPTH:0] csel;                          // one-hot min(count,DEPTH)
 for(gj=0;gj<=DEPTH;gj=gj+1)begin:g_csel assign csel[gj]=(gj==DEPTH)?(count>=DEPTH):(count==gj); end
 reg[4:1] cge;
 integer kj;
 always @*begin cge=0; for(kj=0;kj<=DEPTH;kj=kj+1) if(csel[kj]) cge=cge|pth[4*kj+:4]; end
 // seal_bad as a flat vector of independent terms OR-reduced as a balanced tree (the as-built procedural
 // "seal_bad=1" if-chain mapped to a 28-level NAND/AND chain).  Same terms, same function.
 (* keep *) wire[15:0] sb_misc;
 (* keep *) wire[DEPTH-1:0] sb_v, sb_r, sb_gv, sb_gr;
 (* keep *) wire[2:0] sb_cv, sb_cp;
 assign sb_misc={!loading,!stop_seen,!meta_seen,meta_q[63:32]!=32'h43414c53,meta_q[31:28]!=0,
                 meta_q[27:18]==0,meta_q[27:18]>=61,count==0,count>DEPTH,
                 pw_data[63:32]!=32'h58504631,pw_data[31:13]!=0,pw_data[1:0]!=2,
                 pw_data[11:6]!=meta_q[17:12],pw_data[5:2]==0,pw_data[5:2]>4,cge[4]};
 for(gj=0;gj<DEPTH;gj=gj+1)begin:g_sbk
  assign sb_v[gj]=!valid[gj];
  assign sb_r[gj]=(gj<count)?(rows[gj][46]!=(gj==count-1)):(rows[gj]!=0);
  assign sb_gv[gj]=!gvalid[gj];
  assign sb_gr[gj]=g_present?((gj<g_count)?(grows[gj][45]||grows[gj][46]!=(gj==g_count-1)):(grows[gj]!=0))
                            :(grows[gj]!=0);
 end
 for(gj=0;gj<3;gj=gj+1)begin:g_sbc
  assign sb_cv[gj]=!cp_valid[gj];
  assign sb_cp[gj]=cge[gj+1]?(!cp_rows[gj][0]||cp_rows[gj][55:49]==0||cp_rows[gj][55:49]>64):(cp_rows[gj]!=0);
 end
 (* keep *) wire sb_g=!gstop_seen||!gdesc_seen||
   (g_present?(gdesc_q[31:28]!=0||gdesc_q[23:12]!=0||g_base==0||g_count==0||g_count>DEPTH||
               gstop_q[63:32]!=32'h43414c47||gstop_q[31:0]==0)
             :(gdesc_q!=0||gstop_q!=0));
 always @* seal_bad=(|sb_misc)||(|sb_v)||(|sb_r)||(|sb_cv)||(|sb_cp)||sb_g||(|sb_gv)||(|sb_gr);
`ifndef SYNTHESIS
 // the as-built procedural form (reference)
 integer copies;reg seal_ref;
 always @*begin
  seal_ref=!loading||!stop_seen||!meta_seen||meta_q[63:32]!=32'h43414c53||meta_q[31:28]!=0||
           meta_q[27:18]==0||meta_q[27:18]>=61||count==0||count>DEPTH||
           pw_data[63:32]!=32'h58504631||pw_data[31:13]!=0||pw_data[1:0]!=2||
           pw_data[11:6]!=meta_q[17:12]||pw_data[5:2]==0||pw_data[5:2]>4;
  copies=0;
  for(k=0;k<DEPTH;k=k+1)begin
   if(!valid[k])seal_ref=1;
   if(k<count)begin
    if(rows[k][45:44]==3)copies=copies+1;
    if(rows[k][46]!=(k==count-1))seal_ref=1;
   end else if(rows[k]!=0)seal_ref=1;
  end
  if(copies>3)seal_ref=1;
  for(k=0;k<3;k=k+1)begin
   if(!cp_valid[k])seal_ref=1;
   if(k<copies)begin
    if(!cp_rows[k][0]||cp_rows[k][55:49]==0||cp_rows[k][55:49]>64)seal_ref=1;
   end else if(cp_rows[k]!=0)seal_ref=1;
  end
  if(!gstop_seen||!gdesc_seen)seal_ref=1;
  for(k=0;k<DEPTH;k=k+1)if(!gvalid[k])seal_ref=1;
  if(g_present)begin
   if(gdesc_q[31:28]!=0||gdesc_q[23:12]!=0||g_base==0||g_count==0||g_count>DEPTH||
      gstop_q[63:32]!=32'h43414c47||gstop_q[31:0]==0)seal_ref=1;
   for(k=0;k<DEPTH;k=k+1)
    if(k<g_count)begin
     if(grows[k][45]||grows[k][46]!=(k==g_count-1))seal_ref=1;
    end else if(grows[k]!=0)seal_ref=1;
  end else begin
   if(gdesc_q!=0||gstop_q!=0)seal_ref=1;
   for(k=0;k<DEPTH;k=k+1)if(grows[k]!=0)seal_ref=1;
  end
 end
 always @(posedge clk) if(rst_n&&pw_v&&!active&&pw_addr==1023&&seal_bad!==seal_ref)
  $fatal(1,"H16V seal_bad %b != reference %b",seal_bad,seal_ref);
`endif
 // QW-H16Y (H16X >= 2): q's next value as a late select.  Start edge (start_cal && !active: read address 0, segment
 // !sb_z) and run edges (segment seg_q, address read_addr_run = second_read ? 1 : index+2) are formed in parallel from
 // registered state; start_sel picks last.  q loads every edge: u_issue reads slot_q only when pending (= a read on the
 // previous edge), and on those edges q holds exactly the as-built read; read_fault keeps the as-built read-enable gate.
 wire start_sel=start_cal&&!active;
 wire ra_ok=read_addr_run<DEPTH;
 wire[46:0] r_run=rows[read_addr_run], g_run=grows[read_addr_run];
`ifdef OT_SEG_MUT
 wire[46:0] q_st=valid[0]?rows[0]:47'd0;
 wire f_st=!valid[0];
 wire[46:0] q_rn=(ra_ok&&valid[read_addr_run])?r_run:47'd0;
 wire f_rn=!(ra_ok&&valid[read_addr_run]);
`else
 wire[46:0] q_st=sb_z?(valid[0]?rows[0]:47'd0):(gvalid[0]?grows[0]:47'd0);
 wire f_st=sb_z?!valid[0]:!gvalid[0];
 wire[46:0] q_rn=seg_q?((ra_ok&&gvalid[read_addr_run])?g_run:47'd0):((ra_ok&&valid[read_addr_run])?r_run:47'd0);
 wire f_rn=seg_q?!(ra_ok&&gvalid[read_addr_run]):!(ra_ok&&valid[read_addr_run]);
`endif
 wire[46:0] q_d=start_sel?q_st:q_rn;
 wire rd_flt=start_sel?f_st:(read_en_run&&f_rn);
`ifndef SYNTHESIS
 reg[46:0] q_ref; reg pend_ref;               // the as-built enabled read register (reference)
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin q_ref<=0;pend_ref<=0;end
  else begin
   pend_ref<=read_en;
   if(read_en)begin
    if(sel_g)q_ref<=(read_addr<DEPTH&&gvalid[read_addr])?grows[read_addr]:47'd0;
    else q_ref<=(read_addr<DEPTH&&valid[read_addr])?rows[read_addr]:47'd0;
   end
  end
 always @(posedge clk) if(H16X>=2&&rst_n)begin
  if(read_en!==(start_sel||read_en_run)) $fatal(1,"H16Y read enable split diverged");
  if(!start_sel&&read_en&&read_addr!==read_addr_run) $fatal(1,"H16Y run read address diverged");
`ifndef OT_SEG_MUT
  if(pend_ref&&q!==q_ref) $fatal(1,"H16Y calendar read %h != as-built %h",q,q_ref);
`endif
 end
`endif
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin valid<=0;gvalid<=0;cp_valid<=0;q<=0;stop_q<=0;meta_q<=0;gstop_q<=0;gdesc_q<=0;gstop_seen<=0;gdesc_seen<=0;
   loading<=0;sealed<=0;stop_seen<=0;meta_seen<=0;cfg_fault<=0;read_fault<=0;seg_q<=0;gp_r<=0;end
  else begin
   if(H16X>=2)begin
    q<=q_d; if(rd_flt)read_fault<=1;
   end else if(read_en)begin
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
     if(H16X==0)rows[pw_addr-BASE]<=pw_data[46:0];valid[pw_addr-BASE]<=1;
    end else if(g_row)begin
     if(!loading||gvalid[pw_addr-GBASE]||pw_data[63:47]!=0)cfg_fault<=1;
     if(H16X==0)grows[pw_addr-GBASE]<=pw_data[46:0];gvalid[pw_addr-GBASE]<=1;
    end else if(pw_addr==GSTOP)begin
     if(!loading||gstop_seen)cfg_fault<=1;gstop_q<=pw_data;gstop_seen<=1;
    end else if(pw_addr==GDESC)begin
     if(!loading||gdesc_seen)cfg_fault<=1;gdesc_q<=pw_data;gdesc_seen<=1;gp_r<=pw_data[63:32]==32'h43414c42;
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
 // QW-H16X: the row data writes of the own_row / g_row branches above (reached iff pw_v && !active && the row decode;
 // pw_addr 0 / GSTOP / GDESC / 1016.. never decode to a row).  Row data carries no reset (as built: not in the reset branch;
 // pw_v is 0 under reset).
 generate if(H16X!=0)begin:g_rw
  genvar rk;
  for(rk=0;rk<DEPTH;rk=rk+1)begin:g_r
   always @(posedge clk)begin
    if(pw_v&&!active&&own_oh_r[rk])rows[rk]<=pw_data[46:0];
    if(pw_v&&!active&&g_oh_r[rk])grows[rk]<=pw_data[46:0];
   end
  end
 end endgenerate
 wire read_en_run;wire[RAW-1:0]read_addr_run;
 ot_qwen_fixed_issue_ld #(.ROW_AW(RAW),.OWN(1),.SREG(SREG),.SLATE(SLATE),.NRL(H16X))u_issue(
 .clk(clk),.rst_n(rst_n),.start(start_cal),.stop_cycle((start_base!=12'd0)?gstop_q[31:0]:stop_q),.slot_re(read_en),.slot_addr(read_addr),.slot_q(q),
 .slot_re_run(read_en_run),.slot_addr_run(read_addr_run),
 .candidate_v(candidate_v),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),.available(available),.end_ok(end_ok),.cp_available(cp_available),
 .issue_v(issue_v),.end_v(end_v),.cp_v(cp_v),.cp_index(cp_index),.issue_pc(issue_pc),.issue_unit(issue_unit),.active(active),.done(done),.cycle(cycle),.fault(core_fault));
 assign cp_cmd={(cp_index<3?cp_rows[cp_index][55:1]:55'd0),cp_v};
 assign image_ready=sealed&&!cfg_fault&&!read_fault;
 assign fault=cfg_fault||read_fault||core_fault;
endmodule

// Sparse fixed issue calendar consumer.  Synchronous calendar ROM has EXACT
// one-edge read latency.  Two records are fetched before production starts;
// every issue launches the read two records ahead.  Adjacent issues use the
// actual ROM response as a bypass, not a readiness-dependent wait.
//
// row[46] last; row[45:44] unit; row[43:32] actual PC; row[31:0] issue cycle.
// Candidate signals come from the actual source decoder (including DYN,
// embedding and full-vocabulary argmax state).  They are checked but NEVER
// gate issue.  Parent must replace its issue/fin equations with issue_v/end_v,
// and retain source command packing, arithmetic, and numeric folding state.
module ot_qwen_fixed_issue_ld #(
    parameter integer ROW_AW=12,
    parameter integer OWN=1,
    // SREG=1 (opt-in, TT head h8): 'scheduled' comes from a register loaded with the
    // exact next-state value of active && head_v && cycle==head[31:0]; bit-identical
    // to SREG=0 every cycle (0 edges), but the 32-bit compare no longer feeds the
    // controller fan-out in the same cycle.
    parameter integer SREG=0,
    // SLATE=1 (opt-in, Q-TTH15 h15 10-17; needs SREG): sched_q's next state as a late select -- the start case (start && !active:
    // head_v_n = 0, so 0) and the run case (the active branch's next state, computed without start) in parallel, start selecting
    // last (h14d: u_is1(h_start) -> start decode fo19 -> 32-b compare -> sched_q -86.9).  Exact, 0 edges.
    // OT_SLATE_MUT: the run case compares the current cycle (negative control)
    parameter integer SLATE=0,
    // NRL=1 (QW-H16X): next_row[31:0] > cycle as a late select of the two parallel compares (slot_q / tail), so the
    // pending_index==index+1 select no longer precedes the 32-bit compare (h16v index -> fault -282 ps).  Exact, 0 edges.
    parameter integer NRL=0
)(
    input wire clk, input wire rst_n,
    input wire start, input wire [31:0] stop_cycle,
    output wire slot_re, output wire [ROW_AW-1:0] slot_addr,
    output wire slot_re_run, output wire [ROW_AW-1:0] slot_addr_run,   // QW-H16Y: the read without the start case
    input wire [46:0] slot_q,
    input wire candidate_v, input wire [11:0] candidate_pc,
    input wire [1:0] candidate_unit,
    input wire available, input wire end_ok, input wire cp_available,
    output wire issue_v, output wire end_v, output wire cp_v, output reg[1:0]cp_index,
    output wire [11:0] issue_pc, output wire [1:0] issue_unit,
    output reg active, output reg done,
    output reg [31:0] cycle,
    output wire fault
);
    // QW-H16Y (NRL >= 2): the sticky fault in two halves -- fault_s (the slot_q / next-row checks: pending index, next
    // present / next row > cycle) and fault_c (everything else) -- both cleared on start, fault = fault_c | fault_s.
    // Every set is 'fault <= 1', so the OR equals the as-built register on every edge (h16x: q -> core_fault -153.6 ps).
    reg fault_c, fault_s;
    assign fault=fault_c|((NRL>=2)?fault_s:1'b0);
    reg [31:0] stop_q;
    reg [46:0] head, tail;
    reg head_v, tail_v;
    reg [ROW_AW-1:0] index;
    reg pending;
    reg [ROW_AW-1:0] pending_index;
    reg second_read;
    // QW-H16V (10-20): cycle+1 and the two cycle magnitude compares as Kogge-Stone (kept levels); h16t: the gate mapping
    // folded cycle+1 into a 30-AND ripple (cycle -> sched_q 36 levels, -344 ps TT).  Exact, 0 edges.
    wire [31:0] cycle_p1;
    ot_hdc_inc_ks #(.W(32)) u_cyc_inc (.a(cycle), .y(cycle_p1));
    wire cyc_gt_head, nrow_gt_cyc;
    ot_hdc_gt_ks #(.W(32)) u_cyc_gt (.a(cycle), .b(head[31:0]), .gt(cyc_gt_head));
    wire scheduled_c=active && head_v && cycle==head[31:0];
    reg  sched_q;
    wire scheduled=(SREG!=0) ? sched_q : scheduled_c;
    assign issue_unit=head[45:44];
    assign issue_pc=head[43:32];
    assign issue_v=scheduled && head[45:44]==OWN;
    assign end_v=scheduled && head[45:44]==0;
    assign cp_v=scheduled && OWN==1 && head[45:44]==3;
    wire next_from_rom=pending && pending_index==index+1'b1;
    wire next_present=tail_v || next_from_rom;
    wire [46:0] next_row=next_from_rom ? slot_q : tail;
    generate if(NRL!=0)begin:g_nrl
      wire gt_slot, gt_tail;
      ot_hdc_gt_ks #(.W(32)) u_slot_gt (.a(slot_q[31:0]), .b(cycle), .gt(gt_slot));
      ot_hdc_gt_ks #(.W(32)) u_tail_gt (.a(tail[31:0]), .b(cycle), .gt(gt_tail));
      assign nrow_gt_cyc=next_from_rom ? gt_slot : gt_tail;
    end else begin:g_nrow
      ot_hdc_gt_ks #(.W(32)) u_nrow_gt (.a(next_row[31:0]), .b(cycle), .gt(nrow_gt_cyc));
    end endgenerate
    // Exact next-state of active/cycle/head_v/head[31:0] (mirrors the always block).
    reg        active_n, head_v_n;
    reg [31:0] cycle_n, head_lo_n;
    always @* begin
      active_n=active; head_v_n=head_v; cycle_n=cycle; head_lo_n=head[31:0];
      if(start && !active) begin
        active_n=1'b1; cycle_n=32'd0; head_v_n=1'b0;
      end else if(active) begin
        cycle_n=cycle_p1;
        if(pending && pending_index==index) begin head_lo_n=slot_q[31:0]; head_v_n=1'b1; end
        if(scheduled) begin
          if(head[46]) begin active_n=1'b0; head_v_n=1'b0; end
          else begin head_lo_n=next_row[31:0]; head_v_n=next_present; end
        end
        if(cycle==stop_q) active_n=1'b0;
        if(&cycle) active_n=1'b0;
      end
    end
    // SLATE: the active branch of the next state above (start only matters when !active)
    reg        active_a, head_v_a;
    reg [31:0] cycle_a, head_lo_a;
    always @* begin
      active_a=active; head_v_a=head_v; head_lo_a=head[31:0];
`ifdef OT_SLATE_MUT
      cycle_a=cycle;
`else
      cycle_a=cycle_p1;
`endif
      if(pending && pending_index==index) begin head_lo_a=slot_q[31:0]; head_v_a=1'b1; end
      if(scheduled) begin
        if(head[46]) begin active_a=1'b0; head_v_a=1'b0; end
        else begin head_lo_a=next_row[31:0]; head_v_a=next_present; end
      end
      if(cycle==stop_q) active_a=1'b0;
      if(&cycle) active_a=1'b0;
    end
    wire s_start=1'b0;                                              // start && !active: head_v_n = 0
    wire s_run=active && active_a && head_v_a && cycle_a==head_lo_a; // !active && !start: active_n = 0
    wire sched_late=(start && !active) ? s_start : s_run;
    always @(posedge clk or negedge rst_n)
      if(!rst_n) sched_q<=1'b0;
      else if(SLATE!=0) sched_q<=sched_late;
`ifdef OT_SREG_MUT
      else sched_q<=active_n && head_v_n && cycle==head_lo_n;   // negative control: stale cycle
`else
      else sched_q<=active_n && head_v_n && cycle_n==head_lo_n;
`endif
`ifndef SYNTHESIS
`ifndef OT_SLATE_MUT
    always @(posedge clk) if(SREG!=0 && rst_n && sched_q!==scheduled_c)
      $fatal(1, "OT_SREG_MISMATCH t=%0t sched_q=%b ref=%b", $time, sched_q, scheduled_c);
`endif
`endif
    assign slot_re=(start && !active) || (active && second_read) || (scheduled && !head[46] && !(next_present && next_row[46]));
    assign slot_addr=(start && !active) ? {ROW_AW{1'b0}} :
                     second_read ? {{(ROW_AW-1){1'b0}},1'b1} : index+2'd2;
    assign slot_re_run=(active && second_read) || (scheduled && !head[46] && !(next_present && next_row[46]));
    assign slot_addr_run=second_read ? {{(ROW_AW-1){1'b0}},1'b1} : index+2'd2;
    wire fs_set=active && !(start && !active) && pending && (pending_index!=index) && !(pending_index==index+1'b1 && !scheduled)
                && (pending_index!=index+1'b1);
    wire fs_set2=active && scheduled && !head[46] && (!next_present || !nrow_gt_cyc);
    always @(posedge clk or negedge rst_n)
      if(!rst_n) fault_s<=1'b0;
      else if(start && !active) fault_s<=1'b0;
      else if(NRL>=2 && (fs_set || fs_set2)) fault_s<=1'b1;
    always @(posedge clk or negedge rst_n) begin
      if(!rst_n) begin
        active<=0;done<=0;cycle<=0;fault_c<=0;stop_q<=0;
        head<=0;tail<=0;head_v<=0;tail_v<=0;index<=0;
        pending<=0;pending_index<=0;second_read<=0;cp_index<=0;
      end else begin
        done<=0;
        pending<=slot_re;
        if(slot_re) pending_index<=slot_addr;
        if(start && active) fault_c<=1;
        if(start && !active) begin
          active<=1;cycle<=0;stop_q<=stop_cycle;fault_c<=0;
          head_v<=0;tail_v<=0;index<=0;second_read<=1;cp_index<=0;
        end else if(active) begin
          cycle<=cycle_p1;
          if(second_read) second_read<=0;
          if(pending) begin
            if(pending_index==index) begin head<=slot_q;head_v<=1;end
            else if(pending_index==index+1'b1 && !scheduled) begin tail<=slot_q;tail_v<=1;end
            else if(pending_index!=index+1'b1 && NRL<2) fault_c<=1;
          end
          if(head_v && cyc_gt_head) fault_c<=1;
          if(scheduled) begin
            if(!candidate_v || candidate_pc!=head[43:32] || candidate_unit!=(head[45:44]==3?2'd1:head[45:44])) fault_c<=1;
            if(head[45:44]==0 ? !end_ok : head[45:44]==3 ? !cp_available : !available) fault_c<=1;
            if(cp_v)begin cp_index<=cp_index+1'b1;if(cp_index==3)fault_c<=1;end
            if(head[45:44]!=0 && head[45:44]!=OWN && !(OWN==1&&head[45:44]==3)) fault_c<=1;
            if(head[46]) begin
              if(head[45:44]!=0 || cycle!=stop_q) fault_c<=1;
              active<=0;done<=1;head_v<=0;tail_v<=0;
            end else begin
              if((!next_present || !nrow_gt_cyc) && NRL<2) fault_c<=1;
              head<=next_row;head_v<=next_present;tail_v<=0;index<=index+1'b1;
              if(&index) fault_c<=1;
            end
          end
          if(cycle==stop_q) begin
            active<=0;done<=1;
            if(!head_v || head[31:0]!=stop_q || !head[46] || head[45:44]!=0) fault_c<=1;
          end
          if(&cycle) begin fault_c<=1;active<=0;done<=1;end
        end
      end
    end
endmodule
