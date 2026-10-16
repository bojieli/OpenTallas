`timescale 1ns/1ps
// Q-ATTN-RATE 2026-10-15: static P.V pair at 8 V rows per cycle (two pairs = 16 rows/cycle per TP8 rank).
//
// Reduction order (golden tools/hdc_golden.py attend(): matvec_il(V^T, bf16(e), s_pv=256)): chunk c' = t mod 256 is
// summed sequentially in increasing t from +0, then the 8-level pairwise tree over c' = 0..255. Pair p owns
// c' = 128p + c, c = 0..127, rows t = 256 n + 128 p + c. This pair splits c over 8 banks: bank l = c[6:4] holds the 16
// chains c = 16 l + a (a = c[3:0]) in the unchanged ot_qwen_tp8_pv256_slice (32 slices x 16 FP32 lanes, actual
// 128x256 SRAM macros, local address a). Each chain still adds its rows serially in t order (one step per 16-cycle
// round >= the 11-edge slice loop), so every leaf is bit-identical to the 1-row/cycle pair.
//   tree levels 1-4 (c bits 0-3): inside each bank, the slice's own SRAM tree (TRA/TRB/TRADD, nodes 16 -> 1);
//   tree levels 5-7 (c bits 4-6 = bank bits 0-2): one 512-lane FP32 join ((b0+b1)+(b2+b3))+((b4+b5)+(b6+b7));
//   level 8 (pair 0 + pair 1) and x 1/Z stay in ot_qwen_tp8_pv256_finalize_static_cal (unchanged).
// Walk (compiler-fixed, a pure function of T): issue cycle q = 16 r + a; bank l (h = l>>2) takes step n = r - h, i.e.
// the high half (c >= 64) runs one round behind, so in every cycle 4 rows come from HBM stack 2(n&1)+p of the low
// half and 4 from the other stack of the pair (balanced V bandwidth), and the 4 same-stack reads of one cycle sit on
// 4 distinct EP owners c[5:3] = {l[1:0], a[3]} (one e-read port per EP).
// Every arrival is checked against the calendar (valid, t, epoch); faults are sticky and never move a slot.
module ot_qwen_tp8_pv_wide_pair #(
 parameter integer PAIR=0,
 parameter integer FIRST_INPUT_AGE=20,   // pair cycle (after the start cycle) of the q = 0 arrival = 1 + V return latency
 parameter integer MUT=0                 // bench negative control: 1 = level-5 join pairs (b0+b2),(b1+b3),... (wrong order)
)(
 input wire clk,rst_n,start,input wire[255:0] slice_clk,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire[7:0] in_valid,input wire[8191:0] in_v,input wire[511:0] in_e,input wire[111:0] in_t,input wire[127:0] in_epoch,
 output wire out_valid,output wire[16383:0] out_leaf,output wire[15:0] out_epoch,
 output reg fault,output reg[31:0] accepted,output wire busy,output wire[15:0] out_age
);
 localparam IDLE=0,FEED=1,DRAIN=2,TRA=3,TRB=4,TRADD=5,TRDRAIN=6,JOIN=7;
 reg[3:0] state;reg[15:0] age;reg[15:0] ep;reg[13:0] lim;reg[15:0] nq;
 reg[4:0] nodes;reg[2:0] ti;reg[3:0] drain_left,reduce_left;reg[4:0] jage;
 wire[15:0] pa=age+16'd1;                         // cycles since the start cycle
 // ---- calendar: expected arrival per bank ----
 wire[15:0] q=pa-16'(FIRST_INPUT_AGE);
 wire in_window=(state==FEED)&&pa>=16'(FIRST_INPUT_AGE)&&q<nq;
 wire[11:0] r=q[15:4];wire[3:0] a=q[3:0];
 reg[7:0] exp_v;reg[13:0] exp_t[0:7];reg[7:0] exp_first;
 integer l;
 always @*begin
  for(l=0;l<8;l=l+1)begin
   automatic integer n=int'(r)-(l>>2);
   automatic integer t=256*n+128*PAIR+16*l+int'(a);
   exp_v[l]=in_window&&n>=0&&t<int'(lim);
   exp_t[l]=14'(t);exp_first[l]=(n==0);
  end
 end
 // ---- banks ----
 wire[7:0] bank_take=in_valid&exp_v&{8{!fault&&(state==FEED)}};
 wire init=(state==FEED)&&pa>=1&&pa<=16;
 wire[6:0] init_c=7'(pa-1);
 wire rd_leaf=(state==TRA)||(state==TRB);
 wire[6:0] leaf_c={3'd0,ti,1'b0}+7'(state==TRB);
 wire[255:0] sf,cv;wire[6:0] cc[0:255];wire[16383:0] ts[0:7];wire[16383:0] raw[0:7];
 reg[10:0] feed_commit[0:7];reg[6:0] tree_commit;
 reg bad_in;
 genvar gb,gh,gs;
 generate for(gb=0;gb<8;gb=gb+1)begin:g_bank
  wire[3:0] ca=in_t[14*gb+:4];
  for(gh=0;gh<4;gh=gh+1)begin:gh_
   for(gs=0;gs<8;gs=gs+1)begin:gs_
    localparam integer S=gh*8+gs;
    ot_qwen_tp8_pv256_slice u_slice(.clk(slice_clk[32*gb+S]),.rst_n(rst_n),.take(bank_take[gb]),.c({3'd0,ca}),
     .first(exp_first[gb]),.init_zero(init),.init_c(init_c),
     .v(in_v[1024*gb+128*gs+:128]),.e(in_e[64*gb+16*gh+:16]),.read_leaf(rd_leaf),.leaf_c(leaf_c),
     .reduce_issue(state==TRADD),.reduce_capture(state==TRB),.reduce_last(nodes==2),.reduce_dst({4'd0,ti}),
     .tree_sum(ts[gb][512*S+:512]),.leaf(raw[gb][512*S+:512]),.commit(cv[32*gb+S]),.commit_c(cc[32*gb+S]),.fault(sf[32*gb+S]));
   end
  end
 end endgenerate
 // ---- level 5-7 join: one 512-lane adder, two node registers, static slots ----
 wire[16383:0] jy;wire[511:0] jv;wire[1023:0] jerr;reg[16383:0] xr,yr;
 reg[16383:0] ja,jb;reg jissue;
 localparam integer J_LAT=7;
 // join slots (jage = cycles in JOIN): issue L5 at 0..3, L5 results at 7..10, L6 issues at 8 (x=L5_0) and 10 (x=L5_2),
 // L6 results at 15 / 17, L7 issue at 17 (y=L6_0), L7 result (pair partial) at 24
 localparam integer J_OUT=3*J_LAT+3;
 always @*begin
  ja=0;jb=0;jissue=0;
  if(state==JOIN)case(jage)
   5'd0:begin jissue=1;ja=ts[0];jb=(MUT==1)?ts[2]:ts[1];end
   5'd1:begin jissue=1;ja=(MUT==1)?ts[1]:ts[2];jb=ts[3];end
   5'd2:begin jissue=1;ja=ts[4];jb=ts[5];end
   5'd3:begin jissue=1;ja=ts[6];jb=ts[7];end
   5'(J_LAT+1):begin jissue=1;ja=xr;jb=jy;end
   5'(J_LAT+3):begin jissue=1;ja=xr;jb=jy;end
   5'(2*J_LAT+3):begin jissue=1;ja=yr;jb=jy;end
   default:;
  endcase
 end
 genvar gl;
 generate for(gl=0;gl<512;gl=gl+1)begin:g_join
  ot_hdc_fp32_add_lat #(.LAT(J_LAT)) u_add(.clk(slice_clk[gl>>1]),.rst_n(rst_n),.valid_in(jissue&&!fault),
   .a(ja[32*gl+:32]),.b(jb[32*gl+:32]),.y(jy[32*gl+:32]),.err(jerr[2*gl+:2]),.valid_out(jv[gl]));
 end endgenerate
 wire jexp=(state==JOIN)&&(jage==J_LAT||jage==J_LAT+1||jage==J_LAT+2||jage==J_LAT+3||jage==2*J_LAT+1||jage==2*J_LAT+3||jage==J_OUT);
 assign out_valid=(state==JOIN)&&jage==J_OUT&&!fault;
 assign out_leaf=jy;assign out_epoch=ep;
 assign busy=state!=IDLE;
 // static output age (pair cycles after the start cycle): FIRST + NQ - 1 (last arrival) + 13 (drain) + 73 (tree 16->1)
 // + J_OUT; the compiler calendar (P0/P1) must equal it, the finalize faults otherwise
 assign out_age=16'(FIRST_INPUT_AGE)+nq-16'd1+16'd13+16'd73+16'(J_OUT);
 // ---- control ----
 integer k;
 reg cbad;
 always @*begin
  cbad=0;
  for(k=0;k<8;k=k+1)if(cv[32*k+:32]!={32{feed_commit[k][10]||tree_commit[6]}})cbad=1;
  if(|sf)cbad=1;
  if((in_valid!=exp_v)&&(state==FEED))cbad=1;
  if((state!=FEED)&&(|in_valid))cbad=1;
  for(k=0;k<8;k=k+1)if(in_valid[k]&&exp_v[k]&&(in_t[14*k+:14]!=exp_t[k]||in_epoch[16*k+:16]!=ep))cbad=1;
  if(jv!={512{jexp}})cbad=1;
  if(|jerr && jexp)cbad=1;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;fault<=0;age<=0;ep<=0;lim<=0;nq<=0;nodes<=0;ti<=0;drain_left<=0;reduce_left<=0;jage<=0;
   accepted<=0;tree_commit<=0;xr<=0;yr<=0;for(k=0;k<8;k=k+1)feed_commit[k]<=0;end
  else if((start&&state!=IDLE)||(state!=IDLE&&cbad))begin state<=IDLE;fault<=1;end
  else begin
   if(state!=IDLE)age<=age+1'b1;
   for(k=0;k<8;k=k+1)feed_commit[k]<={feed_commit[k][9:0],bank_take[k]};
   tree_commit<={tree_commit[5:0],state==TRADD};
   accepted<=accepted+32'($countones(bank_take));
   case(state)
    IDLE:if(start)begin
     ep<=epoch;lim<=context_len;age<=0;accepted<=0;
     nq<=(context_len>14'(128*PAIR))?16'(16*(((int'(context_len)-128*PAIR+255)>>8)+1)):16'd0;
     if(context_len==0||context_len>8192)fault<=1;else state<=FEED;
    end
    FEED:if(pa>=16'(FIRST_INPUT_AGE)+nq-16'd1&&pa>=16'd16)begin state<=DRAIN;drain_left<=12;end
    DRAIN:begin
     drain_left<=drain_left-1'b1;
     if(drain_left<=1)begin nodes<=16;ti<=0;state<=TRA;end
    end
    TRA:state<=TRB;
    TRB:state<=TRADD;
    TRADD:begin reduce_left<=7;if(5'(ti)+1==nodes/2)state<=TRDRAIN;else begin ti<=ti+1'b1;state<=TRA;end end
    TRDRAIN:begin
     reduce_left<=reduce_left-1'b1;
     if(reduce_left==1)begin
      if(nodes==2)begin state<=JOIN;jage<=0;end else begin nodes<=nodes/2;ti<=0;state<=TRA;end
     end
    end
    JOIN:begin
     jage<=jage+1'b1;
     if(jage==J_LAT)xr<=jy;                      // L5_0
     if(jage==J_LAT+2)xr<=jy;                    // L5_2
     if(jage==2*J_LAT+1)yr<=jy;                  // L6_0
     if(jage==J_OUT)state<=IDLE;
    end
    default:;
   endcase
  end
 end
endmodule

// Per-pair V request calendar (the same walk as the pair): port order {stack PAIR lanes 0-3, stack PAIR+2 lanes 0-3}.
// Bank l issues on lane l&3 of stack 2(n&1)+PAIR; the low and high half always hit different stacks in one cycle.
module ot_qwen_tp8_vrow_wide #(parameter integer PAIR=0)(
 input wire clk,rst_n,start,input wire[13:0] context_len,
 output reg[7:0] req_valid,output reg[111:0] req_t,output reg fault
);
 reg active;reg[15:0] q;reg[15:0] nq;reg[13:0] lim;
 integer l;
 always @*begin
  req_valid=0;req_t=0;
  if(active&&q<nq)for(l=0;l<8;l=l+1)begin
   automatic integer n=int'(q>>4)-(l>>2);
   automatic integer t=256*n+128*PAIR+16*l+int'(q&15);
   automatic integer port=4*(n&1)+(l&3);
   if(n>=0&&t<int'(lim))begin req_valid[port]=1'b1;req_t[14*port+:14]=14'(t);end
  end
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin active<=0;q<=0;nq<=0;lim<=0;fault<=0;end
  else if(start)begin
   if(active&&q<nq)fault<=1;
   active<=1;q<=0;lim<=context_len;
   nq<=(context_len>14'(128*PAIR))?16'(16*(((int'(context_len)-128*PAIR+255)>>8)+1)):16'd0;
  end else if(active)begin
   if(q<nq)q<=q+1'b1;else active<=0;
  end
endmodule
