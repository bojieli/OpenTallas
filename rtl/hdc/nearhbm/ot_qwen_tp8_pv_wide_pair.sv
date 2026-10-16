`timescale 1ns/1ps
// Q-ATTN-RATE 2026-10-15: static P.V pair at 8 V rows per cycle (two pairs = 16 rows/cycle per TP8 rank).
//
// Reduction order (golden tools/hdc_golden.py attend(): matvec_il(V^T, bf16(e), s_pv=256)): chunk c' = t mod 256 is
// summed sequentially in increasing t from +0, then the 8-level pairwise tree over c' = 0..255. Pair p owns
// c' = 128p + c, c = 0..127, rows t = 256 n + 128 p + c. The pair splits c over 8 banks: bank l = c[6:4] holds the 16
// chains c = 16 l + a (a = c[3:0]) in the unchanged ot_qwen_tp8_pv256_slice (16 FP32 lanes, actual 128x256 SRAM macros,
// local address a). Each chain still adds its rows serially in t order (one step per 16-cycle round >= the 11-edge
// slice loop), so every leaf is bit-identical to the 1-row/cycle pair.
//   tree levels 1-4 (c bits 0-3): inside each slice, its own SRAM tree (TRA/TRB/TRADD, nodes 16 -> 1);
//   tree levels 5-7 (c bits 4-6 = bank bits 0-2): ((b0+b1)+(b2+b3))+((b4+b5)+(b6+b7)) per 16-lane column;
//   level 8 (pair 0 + pair 1) and x 1/Z stay in ot_qwen_tp8_pv256_finalize_static_cal (unchanged).
// Walk (compiler-fixed, a pure function of T): issue cycle q = 16 r + a; bank l (h = l>>2) takes step n = r - h, i.e.
// the high half (c >= 64) runs one round behind, so in every cycle 4 rows come from HBM stack 2(n&1)+p of the low
// half and 4 from the other stack of the pair (balanced V bandwidth), and the 4 same-stack reads of one cycle sit on
// 4 distinct EP owners c[5:3] = {l[1:0], a[3]} (one e-read port per EP).
//
// PHYSICAL PARTITION (one replicated master): 32 x ot_qwen_tp8_pv_col (column S = head h, dims 16 gs..16 gs+15: the 8
// bank slices of that column + its 16-lane level 5-7 join; EVERY port registered) + ot_qwen_tp8_pv_wide_ctl (calendar,
// arrival identity checks, slice/tree/join commands, V requests). The pair itself is wires only. Inputs arrive per V
// PORT (8 ports: stack PAIR lanes 0-3, stack PAIR+2 lanes 0-3); the column maps port -> bank by the round parity.
// Every arrival is checked against the calendar (valid, t, epoch); faults are sticky and never move a slot.
module ot_qwen_tp8_pv_wide_pair #(
 parameter integer PAIR=0,
 parameter integer FIRST_INPUT_AGE=20,   // pair cycle (after the start cycle) of the q = 0 arrival = 1 + V return latency
 parameter integer MUT=0                 // bench negative control: 1 = level-5 join pairs (b0+b2),(b1+b3) (wrong order)
)(
 input wire clk,rst_n,start,input wire[32:0] col_clk,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire[7:0] in_valid,input wire[8191:0] in_v,input wire[511:0] in_e,input wire[111:0] in_t,input wire[127:0] in_epoch,
 output wire[7:0] req_valid,output wire[111:0] req_t,
 output wire out_valid,output wire[16383:0] out_leaf,output wire[15:0] out_epoch,
 output wire fault,output wire busy,output wire[15:0] out_age
);
 wire[59:0] cmd;wire[31:0] cf,cv;wire ctl_fault;
 ot_qwen_tp8_pv_wide_ctl #(.PAIR(PAIR),.FIRST_INPUT_AGE(FIRST_INPUT_AGE)) u_ctl(.clk(col_clk[32]),.rst_n(rst_n),.start(start),
  .context_len(context_len),.epoch(epoch),.in_valid(in_valid),.in_t(in_t),.in_epoch(in_epoch),
  .req_valid(req_valid),.req_t(req_t),.cmd(cmd),.col_valid(cv),.col_fault(cf),
  .out_valid(out_valid),.out_epoch(out_epoch),.fault(ctl_fault),.busy(busy),.out_age(out_age));
 genvar s;
 generate for(s=0;s<32;s=s+1)begin:g_col
  localparam integer H=s/8,GS=s%8;
  wire[1023:0] v;wire[127:0] e;
  genvar k;
  for(k=0;k<8;k=k+1)begin:g_port
   assign v[128*k+:128]=in_v[1024*k+128*GS+:128];
   assign e[16*k+:16]=in_e[64*k+16*H+:16];
  end
  ot_qwen_tp8_pv_col #(.MUT(MUT)) u_col(.clk(col_clk[s]),.rst_n(rst_n),.pv(v),.pe(e),.cmd(cmd),
   .y(out_leaf[512*s+:512]),.y_valid(cv[s]),.fault(cf[s]));
 end endgenerate
 assign fault=ctl_fault;
endmodule

// One P.V column: head H, dims 16 GS .. 16 GS + 15 of all 8 banks (8 x ot_qwen_tp8_pv256_slice, 16 SRAM macros) and the
// 16-lane level 5-7 join. Every input and output port is registered at the pin (one edge each way); the column checks
// its own slices (commit slots, adder flags) and reports one sticky fault.
// cmd (60 b, from ot_qwen_tp8_pv_wide_ctl, all broadcast): {join_go, reduce_dst[2:0], reduce_last, reduce_capture,
//  reduce_issue, leaf_c[3:0], rd_leaf, init_c[3:0], init, a[3:0], first_hi, first_lo, take[7:0], swap, epoch_rsv...}
module ot_qwen_tp8_pv_col #(parameter integer MUT=0, J_LAT=7)(
 input wire clk,rst_n,
 input wire[1023:0] pv,input wire[127:0] pe,     // per V port k (0-3: stack PAIR lane k; 4-7: stack PAIR+2 lane k-4)
 input wire[59:0] cmd,
 output reg[511:0] y,output reg y_valid,output reg fault
);
 localparam integer J_OUT=3*J_LAT+3;
 // ---- pin registers ----
 reg[1023:0] v_r;reg[127:0] e_r;reg[59:0] c_r;
 always @(posedge clk)begin v_r<=pv;e_r<=pe;end
 always @(posedge clk or negedge rst_n)if(!rst_n)c_r<=0;else c_r<=cmd;
 wire swap=c_r[0];wire[7:0] take=c_r[8:1];wire first_lo=c_r[9],first_hi=c_r[10];wire[3:0] a=c_r[14:11];
 wire init=c_r[15];wire[3:0] init_c=c_r[19:16];wire rd_leaf=c_r[20];wire[3:0] leaf_c=c_r[24:21];
 wire red_issue=c_r[25],red_capture=c_r[26],red_last=c_r[27];wire[2:0] red_dst=c_r[30:28];wire join_go=c_r[31];
 // ---- 8 bank slices; port -> bank: bank l<4 takes port l (even round) or l+4 (odd), bank l>=4 the other one ----
 wire[7:0] sf,cv;wire[6:0] cc[0:7];wire[511:0] ts[0:7];
 reg[10:0] feed_commit[0:7];reg[6:0] tree_commit;
 genvar l;
 generate for(l=0;l<8;l=l+1)begin:g_bank
  localparam integer P0=l,P1=(l<4)?l+4:l-4;
  wire[127:0] bv=swap?v_r[128*P1+:128]:v_r[128*P0+:128];
  wire[15:0] be=swap?e_r[16*P1+:16]:e_r[16*P0+:16];
  wire[511:0] raw;
  ot_qwen_tp8_pv256_slice u_slice(.clk(clk),.rst_n(rst_n),.take(take[l]),.c({3'd0,a}),
   .first((l<4)?first_lo:first_hi),.init_zero(init),.init_c({3'd0,init_c}),
   .v(bv),.e(be),.read_leaf(rd_leaf),.leaf_c({3'd0,leaf_c}),
   .reduce_issue(red_issue),.reduce_capture(red_capture),.reduce_last(red_last),.reduce_dst({4'd0,red_dst}),
   .tree_sum(ts[l]),.leaf(raw),.commit(cv[l]),.commit_c(cc[l]),.fault(sf[l]));
 end endgenerate
 // ---- level 5-7 join (16 lanes), two node registers, static slots from join_go ----
 reg jrun;reg[4:0] jage;reg[511:0] xr,yr,ja,jb;reg jissue;
 wire[511:0] jy;wire[15:0] jv;wire[31:0] jerr;
 always @*begin
  ja=0;jb=0;jissue=0;
  if(jrun)case(jage)
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
 genvar g;
 generate for(g=0;g<16;g=g+1)begin:g_join
  ot_hdc_fp32_add_lat #(.LAT(J_LAT)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(jissue),
   .a(ja[32*g+:32]),.b(jb[32*g+:32]),.y(jy[32*g+:32]),.err(jerr[2*g+:2]),.valid_out(jv[g]));
 end endgenerate
 wire jexp=jrun&&(jage==J_LAT||jage==J_LAT+1||jage==J_LAT+2||jage==J_LAT+3||jage==2*J_LAT+1||jage==2*J_LAT+3||jage==J_OUT);
 // ---- integrity: commit slots of every slice (feed take+11, tree issue+7), slice faults, join flags ----
 reg bad;integer k;
 always @*begin
  bad=|sf;
  for(k=0;k<8;k=k+1)if(cv[k]!=(feed_commit[k][10]||tree_commit[6]))bad=1;
  if(jv!={16{jexp}})bad=1;
  if(jexp&&(|jerr))bad=1;
  if(join_go&&jrun)bad=1;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin jrun<=0;jage<=0;xr<=0;yr<=0;y_valid<=0;fault<=0;tree_commit<=0;for(k=0;k<8;k=k+1)feed_commit[k]<=0;end
  else begin
   for(k=0;k<8;k=k+1)feed_commit[k]<={feed_commit[k][9:0],take[k]};
   tree_commit<={tree_commit[5:0],red_issue};
   if(bad)fault<=1;
   y_valid<=jrun&&jage==J_OUT;
   if(join_go)begin jrun<=1;jage<=0;end
   else if(jrun)begin
    jage<=jage+1'b1;
    if(jage==J_LAT)xr<=jy;                      // L5_0
    if(jage==J_LAT+2)xr<=jy;                    // L5_2
    if(jage==2*J_LAT+1)yr<=jy;                  // L6_0
    if(jage==J_OUT)jrun<=0;
   end
  end
 end
 always @(posedge clk)if(jrun&&jage==J_OUT)y<=jy;
endmodule

// Pair control tile: calendar walk, V requests, arrival identity per port, the column command word, output check.
module ot_qwen_tp8_pv_wide_ctl #(parameter integer PAIR=0,FIRST_INPUT_AGE=20)(
 input wire clk,rst_n,start,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire[7:0] in_valid,input wire[111:0] in_t,input wire[127:0] in_epoch,
 output wire[7:0] req_valid,output wire[111:0] req_t,
 output reg[59:0] cmd,input wire[31:0] col_valid,input wire[31:0] col_fault,
 output wire out_valid,output wire[15:0] out_epoch,output reg fault,output wire busy,output wire[15:0] out_age
);
 localparam IDLE=0,FEED=1,DRAIN=2,TRA=3,TRB=4,TRADD=5,TRDRAIN=6,JOIN=7;
 localparam integer COL_LAT=3+3*7+3+1;          // ctl JOIN -> column y_valid: cmd reg, column pin reg, jrun start, J_OUT 24, y reg
 reg[3:0] state;reg[15:0] age;reg[15:0] ep;reg[13:0] lim;reg[15:0] nq;
 reg[4:0] nodes;reg[2:0] ti;reg[3:0] drain_left,reduce_left;reg[5:0] wage;
 wire[15:0] pa=age+16'd1;                         // cycles since the start cycle
 wire[15:0] q=pa-16'(FIRST_INPUT_AGE);
 wire in_window=(state==FEED)&&pa>=16'(FIRST_INPUT_AGE)&&q<nq;
 wire[11:0] r=q[15:4];wire[3:0] a=q[3:0];
 wire[15:0] qn=q+16'd1;wire next_window=(state==FEED)&&pa+16'd1>=16'(FIRST_INPUT_AGE)&&qn<nq;
 wire[11:0] rn=qn[15:4];wire[3:0] an=qn[3:0];
 // expected arrival per bank, mapped onto the V port it uses (port 4*(n&1)+(l&3))
 reg[7:0] exp_take,pexp_v;reg[13:0] pexp_t[0:7];
 integer l;
 always @*begin
  exp_take=0;pexp_v=0;
  for(l=0;l<8;l=l+1)pexp_t[l]=0;
  for(l=0;l<8;l=l+1)begin
   automatic integer n=int'(r)-(l>>2);
   automatic integer t=256*n+128*PAIR+16*l+int'(a);
   automatic integer port=4*(n&1)+(l&3);
   if(in_window&&n>=0&&t<int'(lim))begin pexp_v[port]=1'b1;pexp_t[port]=14'(t);end
 end
  // the slice take of the NEXT arrival cycle: the command word is registered here and at the column pin (2 edges),
  // the V/e payload only at the column pin (1 edge), so the command leads its data by one cycle
  for(l=0;l<8;l=l+1)begin
   automatic integer n=int'(rn)-(l>>2);
   automatic integer t=256*n+128*PAIR+16*l+int'(an);
   if(next_window&&n>=0&&t<int'(lim))exp_take[l]=1'b1;
  end
 end
 ot_qwen_tp8_vrow_wide #(.PAIR(PAIR)) u_req(.clk(clk),.rst_n(rst_n),.start(start),.context_len(context_len),
  .req_valid(req_valid),.req_t(req_t),.fault());
 reg cbad;integer k;
 always @*begin
  cbad=0;
  if(in_valid!=(pexp_v&{8{state==FEED}}))cbad=1;
  for(k=0;k<8;k=k+1)if(in_valid[k]&&(in_t[14*k+:14]!=pexp_t[k]||in_epoch[16*k+:16]!=ep))cbad=1;
  if(|col_fault)cbad=1;
  if(col_valid!={32{col_valid[0]}})cbad=1;
  if(col_valid[0]!=out_valid_slot)cbad=1;
 end
 assign busy=state!=IDLE;assign out_epoch=ep;
 // static output age (pair cycles after the start cycle): FIRST + NQ - 1 (last arrival) + 13 (drain) + 73 (tree)
 // + COL_LAT (column join behind its pin registers); the compiler calendar (P0/P1) must equal it
 assign out_age=16'(FIRST_INPUT_AGE)+nq-16'd1+16'd13+16'd73+16'(COL_LAT);
 wire out_valid_slot=(state==JOIN)&&wage==6'(COL_LAT);
 assign out_valid=out_valid_slot&&!fault;
 // column command word, registered at this tile's output pin (the column registers it again at its input pin)
 wire n0_lo=(rn==0),n0_hi=(rn==1);
 always @(posedge clk or negedge rst_n)
  if(!rst_n)cmd<=0;
  else begin
   cmd<=0;
   cmd[0]<=rn[0];cmd[8:1]<=exp_take&{8{!fault}};cmd[9]<=n0_lo;cmd[10]<=n0_hi;cmd[14:11]<=an;
   cmd[15]<=(state==FEED)&&pa>=1&&pa<=16;cmd[19:16]<=4'(pa-1);
   cmd[20]<=(state==TRA)||(state==TRB);cmd[24:21]<={ti,1'b0}+4'(state==TRB);
   cmd[25]<=state==TRADD;cmd[26]<=state==TRB;cmd[27]<=nodes==2;cmd[30:28]<=ti;
   cmd[31]<=(state==JOIN)&&wage==0;
  end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin state<=IDLE;fault<=0;age<=0;ep<=0;lim<=0;nq<=0;nodes<=0;ti<=0;drain_left<=0;reduce_left<=0;wage<=0;end
  else if((start&&state!=IDLE)||(state!=IDLE&&cbad))begin state<=IDLE;fault<=1;end
  else begin
   if(state!=IDLE)age<=age+1'b1;
   case(state)
    IDLE:if(start)begin
     ep<=epoch;lim<=context_len;age<=0;
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
      if(nodes==2)begin state<=JOIN;wage<=0;end else begin nodes<=nodes/2;ti<=0;state<=TRA;end
     end
    end
    JOIN:begin wage<=wage+1'b1;if(wage==6'(COL_LAT))state<=IDLE;end
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
