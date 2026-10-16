`timescale 1ns/1ps
// Q-ATTN-RATE 2026-10-15: static P.V pair at 8 V rows per cycle (two pairs = 16 rows/cycle per TP8 rank).
//
// Reduction order (golden tools/hdc_golden.py attend(): matvec_il(V^T, bf16(e), s_pv=256)): chunk c' = t mod 256 is
// summed sequentially in increasing t from +0, then the 8-level pairwise tree over c' = 0..255. Pair p owns
// c' = 128p + c, c = 0..127, rows t = 256 n + 128 p + c. The pair splits c over 8 banks: bank l = c[6:4] holds the 16
// chains c = 16 l + a (a = c[3:0]) in ot_qwen_tp8_pv16_slice (the pv256 slice datapath byte-identical, 16 FP32 lanes, its 16 chain words in
// 4 actual ot_sram_1r1w_32x128_m1 macros, local address a). Each chain still adds its rows serially in t order (one step per 16-cycle round >= the 11-edge
// slice loop), so every leaf is bit-identical to the 1-row/cycle pair.
//   tree levels 1-4 (c bits 0-3): inside each slice, its own SRAM tree (TRA/TRB/TRADD, nodes 16 -> 1);
//   tree levels 5-7 (c bits 4-6 = bank bits 0-2): ((b0+b1)+(b2+b3))+((b4+b5)+(b6+b7)) per 16-lane column join;
//   level 8 (pair 0 + pair 1) and x 1/Z stay in ot_qwen_tp8_pv256_finalize_static_cal (unchanged).
// Walk (compiler-fixed, a pure function of T): issue cycle q = 16 r + a; bank l (h = l>>2) takes step n = r - h, i.e.
// the high half (c >= 64) runs one round behind, so in every cycle 4 rows come from HBM stack 2(n&1)+p of the low
// half and 4 from the other stack of the pair (balanced V bandwidth), and the 4 same-stack reads of one cycle sit on
// 4 distinct EP owners c[5:3] = {l[1:0], a[3]} (one e-read port per EP).
//
// PHYSICAL PARTITION: 32 x ot_qwen_tp8_pv_col (wires only; column S = head h, dims 16 gs..16 gs+15) = 8 x
// ot_qwen_tp8_pv_slice_t (the replicated leaf, 256 per pair) + 1 x ot_qwen_tp8_pv_join_t (32 per pair), EVERY tile port
// registered, + ot_qwen_tp8_pv_wide_ctl (calendar,
// arrival identity checks, slice/tree/join commands, V requests). The pair itself is wires only. Inputs arrive per V
// PORT (8 ports: stack PAIR lanes 0-3, stack PAIR+2 lanes 0-3); the column maps port -> bank by the round parity.
// Every arrival is checked against the calendar (valid, t, epoch); faults are sticky and never move a slot.
module ot_qwen_tp8_pv_wide_pair #(
 parameter integer PAIR=0,
 parameter integer CTL_RESET_PIN=0, // opt-in local reset capture; normal command timeline unchanged
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
 ot_qwen_tp8_pv_wide_ctl #(.FIRST_INPUT_AGE(FIRST_INPUT_AGE),.RESET_PIN(CTL_RESET_PIN)) u_ctl(.clk(col_clk[32]),.rst_n(rst_n),.pair_id(1'(PAIR)),.start(start),
  .context_len(context_len),.epoch(epoch),.in_valid(in_valid),.in_t(in_t),.in_epoch(in_epoch),
  .req_valid(req_valid),.req_t(req_t),.cmd(cmd),.col_valid(cv),.col_fault(cf),
  .out_epoch(out_epoch),.fault(ctl_fault),.busy(busy),.out_age(out_age));
 // the pair output pulse is column 0's own pinned y_valid; the control tile checks every column against its slot
 assign out_valid=cv[0];
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

// One P.V column (wires only): head H, dims 16 GS .. 16 GS + 15 of all 8 banks = 8 x ot_qwen_tp8_pv_slice_t (one
// hardened tile each: an ot_qwen_tp8_pv16_slice + its pin registers) and 1 x ot_qwen_tp8_pv_join_t (the 16-lane level
// 5-7 join, pin registers). Bank l reads V port l (even round) or its partner l^4 (odd round): both port words go to
// the bank tile, which selects by the command's round parity.
// cmd (60 b, from ot_qwen_tp8_pv_wide_ctl): [0] swap, [8:1] take per bank, [9] first_lo, [10] first_hi, [14:11] a,
//  [15] init, [19:16] init_c, [20] rd_leaf, [24:21] leaf_c, [25] red_issue, [26] red_capture, [27] red_last,
//  [30:28] red_dst, [31] join_go
module ot_qwen_tp8_pv_col #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire[1023:0] pv,input wire[127:0] pe,     // per V port k (0-3: stack PAIR lane k; 4-7: stack PAIR+2 lane k-4)
 input wire[59:0] cmd,
 output wire[511:0] y,output wire y_valid,output wire fault
);
 wire[4095:0] ts;wire[7:0] sf;
 genvar l;
 generate for(l=0;l<8;l=l+1)begin:g_bank
  localparam integer PA=l,PB=l^4;
  wire[22:0] bc={cmd[30:15],cmd[14:11],(l<4)?cmd[9]:cmd[10],cmd[1+l],cmd[0]};
  ot_qwen_tp8_pv_slice_t u_bank(.clk(clk),.rst_n(rst_n),.pv2({pv[128*PB+:128],pv[128*PA+:128]}),
   .pe2({pe[16*PB+:16],pe[16*PA+:16]}),.bc(bc),.ts(ts[512*l+:512]),.fault(sf[l]));
 end endgenerate
 ot_qwen_tp8_pv_join_t #(.MUT(MUT)) u_join(.clk(clk),.rst_n(rst_n),.ts0(ts[1023:0]),.ts1(ts[2047:1024]),.ts2(ts[3071:2048]),
  .ts3(ts[4095:3072]),.join_go(cmd[31]),.sf(sf),
  .y(y),.y_valid(y_valid),.fault(fault));
endmodule

// P.V bank slice tile (the replicated leaf, 512 per KV/system die): the 16 chains of one bank for one 16-dim x head
// column. Every port registered at the pin. bc = {red_dst[2:0], red_last, red_capture, red_issue, leaf_c[3:0],
// rd_leaf, init_c[3:0], init, a[3:0], first, take, swap}. Checks its own commit slots (feed take+11, tree issue+7)
// and the slice/adder flags; reports one registered sticky fault.
module ot_qwen_tp8_pv_slice_t(
 input wire clk,rst_n,input wire[255:0] pv2,input wire[31:0] pe2,input wire[22:0] bc,
 output reg[511:0] ts,output reg fault
);
 reg[255:0] v_r;reg[31:0] e_r;reg[22:0] c_r;
 always @(posedge clk)begin v_r<=pv2;e_r<=pe2;c_r<=bc;end
 wire swap=c_r[0],take=c_r[1],first=c_r[2];wire[3:0] a=c_r[6:3];wire init=c_r[7];wire[3:0] init_c=c_r[11:8];
 wire rd_leaf=c_r[12];wire[3:0] leaf_c=c_r[16:13];wire red_issue=c_r[17],red_capture=c_r[18],red_last=c_r[19];
 wire[2:0] red_dst=c_r[22:20];
 wire[511:0] tsum,raw;wire cv,sf;wire[6:0] cc;
 ot_qwen_tp8_pv16_slice u_slice(.clk(clk),.rst_n(rst_n),.take(take),.c({3'd0,a}),.first(first),.init_zero(init),
  .init_c({3'd0,init_c}),.v(swap?v_r[255:128]:v_r[127:0]),.e(swap?e_r[31:16]:e_r[15:0]),.read_leaf(rd_leaf),
  .leaf_c({3'd0,leaf_c}),.reduce_issue(red_issue),.reduce_capture(red_capture),.reduce_last(red_last),
  .reduce_dst({4'd0,red_dst}),.tree_sum(tsum),.leaf(raw),.commit(cv),.commit_c(cc),.fault(sf));
 reg[10:0] fc;reg[6:0] tc;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin fc<=0;tc<=0;fault<=0;end
  else begin
   fc<={fc[9:0],take};tc<={tc[5:0],red_issue};
   if(sf||(cv!=(fc[10]||tc[6])))fault<=1;
  end
 always @(posedge clk)ts<=tsum;
endmodule

// P.V column join tile (64 per KV/system die): ((b0+b1)+(b2+b3))+((b4+b5)+(b6+b7)) over the 8 bank tree sums of one
// column, 16 FP32 lanes, one adder set + two node registers on static slots from join_go. Every port registered.
module ot_qwen_tp8_pv_join_t #(parameter integer MUT=0, J_LAT=7)(
 input wire clk,rst_n,input wire[1023:0] ts0,ts1,ts2,ts3,   // bank tree sums {b1,b0}, {b3,b2}, {b5,b4}, {b7,b6} (one face each)
 input wire join_go,input wire[7:0] sf,
 output reg[511:0] y,output reg y_valid,output reg fault
);
 wire[4095:0] ts={ts3,ts2,ts1,ts0};
 localparam integer J_OUT=3*J_LAT+3;
 reg[4095:0] t_r;reg go_r;reg[7:0] sf_r;
 always @(posedge clk)t_r<=ts;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin go_r<=0;sf_r<=0;end else begin go_r<=join_go;sf_r<=sf;end
 wire[511:0] tb[0:7];
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_t assign tb[g]=t_r[512*g+:512]; end endgenerate
 reg jrun;reg[4:0] jage;reg[511:0] xr,yr;wire[511:0] ja,jb;
 wire[511:0] jy;wire[15:0] jv;wire[31:0] jerr;
 // Operand-select slot, decoded ONE edge ahead from the next (jrun, jage) and registered once PER LANE (kept copies):
 // the shared jage decode drove all 1,024 operand-mux bits (3,299 loads, gate 21:06); each copy now drives one lane's
 // 64 mux bits + its adder issue. Slot codes: 1..4 = L5 pairs, 5 = (xr,jy) at J_LAT+1 / J_LAT+3, 6 = (yr,jy) at 2J_LAT+3.
 wire nrun=go_r?1'b1:(jrun&&jage!=5'(J_OUT));
 wire[4:0] nage=go_r?5'd0:(jrun?jage+5'd1:jage);
 reg[2:0] nsel;
 always @*begin
  nsel=3'd0;
  if(nrun)case(nage)
   5'd0:nsel=3'd1;
   5'd1:nsel=3'd2;
   5'd2:nsel=3'd3;
   5'd3:nsel=3'd4;
   5'(J_LAT+1):nsel=3'd5;
   5'(J_LAT+3):nsel=3'd5;
   5'(2*J_LAT+3):nsel=3'd6;
   default:;
  endcase
 end
 wire[15:0] jissue;
 generate for(g=0;g<16;g=g+1)begin:g_join
  (* keep = "true", dont_touch = "true" *) reg[2:0] js;
  always @(posedge clk or negedge rst_n)if(!rst_n)js<=3'd0;else js<=nsel;
  assign jissue[g]=js!=3'd0;
  reg[31:0] la,lb;
  always @*begin
   la=32'd0;lb=32'd0;
   case(js)
    3'd1:begin la=tb[0][32*g+:32];lb=(MUT==1)?tb[2][32*g+:32]:tb[1][32*g+:32];end
    3'd2:begin la=(MUT==1)?tb[1][32*g+:32]:tb[2][32*g+:32];lb=tb[3][32*g+:32];end
    3'd3:begin la=tb[4][32*g+:32];lb=tb[5][32*g+:32];end
    3'd4:begin la=tb[6][32*g+:32];lb=tb[7][32*g+:32];end
    3'd5:begin la=xr[32*g+:32];lb=jy[32*g+:32];end
    3'd6:begin la=yr[32*g+:32];lb=jy[32*g+:32];end
    default:;
   endcase
  end
  assign ja[32*g+:32]=la;assign jb[32*g+:32]=lb;
  ot_hdc_fp32_add_lat #(.LAT(J_LAT),.DRST(0)) u_add(.clk(clk),.rst_n(rst_n),.valid_in(jissue[g]),
   .a(ja[32*g+:32]),.b(jb[32*g+:32]),.y(jy[32*g+:32]),.err(jerr[2*g+:2]),.valid_out(jv[g]));
 end endgenerate
 wire jexp=jrun&&(jage==J_LAT||jage==J_LAT+1||jage==J_LAT+2||jage==J_LAT+3||jage==2*J_LAT+1||jage==2*J_LAT+3||jage==J_OUT);
 wire bad=(|sf_r)||(jv!={16{jexp}})||(jexp&&(|jerr))||(go_r&&jrun);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin jrun<=0;jage<=0;y_valid<=0;fault<=0;end
  else begin
   if(bad)fault<=1;
   y_valid<=jrun&&jage==J_OUT;
   if(go_r)begin jrun<=1;jage<=0;end
   else if(jrun)begin jage<=jage+1'b1;if(jage==J_OUT)jrun<=0;end
  end
 end
 always @(posedge clk)begin
  if(jrun&&jage==J_LAT)xr<=jy;                      // L5_0
  if(jrun&&jage==J_LAT+2)xr<=jy;                    // L5_2
  if(jrun&&jage==2*J_LAT+1)yr<=jy;                  // L6_0
  if(jrun&&jage==J_OUT)y<=jy;
 end
endmodule

// Pair control tile: calendar walk, V requests, arrival identity per port, the column command word, output check.
// Every port is registered at the pin: inputs (start/context/epoch, arrival identities, column flags) one edge in,
// outputs (V requests, command word, flags, out_age) one edge out. Internal age 'pa' counts from the registered start.
module ot_qwen_tp8_pv_wide_ctl #(parameter integer FIRST_INPUT_AGE=20,parameter integer RESET_PIN=0)(
 input wire clk,rst_n,
 input wire pair_id,                            // die strap: one master serves both pairs
 input wire start,input wire[13:0] context_len,input wire[15:0] epoch,
 input wire[7:0] in_valid,input wire[111:0] in_t,input wire[127:0] in_epoch,
 output reg[7:0] req_valid,output reg[111:0] req_t,
 output reg[59:0] cmd,input wire[31:0] col_valid,input wire[31:0] col_fault,
 output reg[15:0] out_epoch,output reg fault,output reg busy,output reg[15:0] out_age
);
 wire local_rst_n;
 generate if(RESET_PIN)begin:g_reset_pin
  // The reset input ends at this pin flop. Cold release is one edge later;
  // production start and every scheduled data edge are unchanged.
  (* keep *)reg rst_q;
  always @(posedge clk)rst_q<=rst_n;
  assign local_rst_n=rst_q;
 end else begin:g_reset_legacy
  assign local_rst_n=rst_n;
 end endgenerate

 localparam IDLE=0,FEED=1,DRAIN=2,TRA=3,TRB=4,TRADD=5,TRDRAIN=6,JOIN=7;
 localparam integer FIRSTI=FIRST_INPUT_AGE+1;      // + the request pin register: arrival pa of q = 0
 localparam integer JGO=2;                       // join_go 2 edges into JOIN: bank tree sums cross the bank out + join in pin regs
 localparam integer COL_LAT=JGO+3+3*7+3+1;      // JOIN -> column y_valid: + cmd reg, join pin reg, jrun start, J_OUT 24, y reg
 // ---- input pin registers ----
 reg start_r;reg[13:0] ctx_r;reg[15:0] epoch_r;reg[7:0] iv_r;reg[111:0] it_r;reg[127:0] ie_r;reg[31:0] cv_r,cf_r;
 reg pid;                                         // pair_id strap, registered (constant; the gate saw pair_id -> wage 15 levels)
 always @(posedge clk)pid<=pair_id;
 always @(posedge clk or negedge local_rst_n)
  if(!local_rst_n)begin start_r<=0;iv_r<=0;cv_r<=0;cf_r<=0;end
  else begin start_r<=start;iv_r<=in_valid;cv_r<=col_valid;cf_r<=col_fault;end
 always @(posedge clk)begin ctx_r<=context_len;epoch_r<=epoch;it_r<=in_t;ie_r<=in_epoch;end
 reg[3:0] state;reg[15:0] age;reg[15:0] ep;reg[13:0] lim;reg[15:0] nq;reg flt;
 reg[4:0] nodes;reg[2:0] ti;reg[3:0] drain_left,reduce_left;reg[5:0] wage;
 wire[15:0] pa=age+16'd1;                         // cycles since the registered start
 // checks: the registered arrival seen at pa arrived at pa-1, i.e. q = pa - 1 - FIRSTI
 wire[15:0] qc=pa-16'd1-16'(FIRSTI);
 wire chk_window=(state!=IDLE)&&pa>=16'(FIRSTI+1)&&qc<nq;
 wire[11:0] rc=qc[15:4];wire[3:0] ac=qc[3:0];
 // slice takes: the command word for the arrival at pa+1 (cmd reg + column pin reg = 2 edges, payload 1 edge)
 wire[15:0] qn=pa+16'd1-16'(FIRSTI);
 wire next_window=(state==FEED)&&pa+16'd1>=16'(FIRSTI)&&qn<nq;
 wire[11:0] rn=qn[15:4];wire[3:0] an=qn[3:0];
 reg[7:0] exp_take,pexp_v;reg[13:0] pexp_t[0:7];
 integer l,wn,wt,wp;                          // loop temporaries (blocking, combinational only; no automatic decls for yosys)
 always @*begin
  exp_take=0;pexp_v=0;wn=0;wt=0;wp=0;
  for(l=0;l<8;l=l+1)pexp_t[l]=0;
  // per PORT (constant index): port wp carries bank l = (wp&3) + 4h of step n = rc - h with n&1 == wp>>2, i.e.
  // h = (rc ^ (wp>>2)) & 1 -- the same (bank, step) -> port map as before, without a runtime-indexed write
  for(wp=0;wp<8;wp=wp+1)begin
   l=(wp&3)+4*((int'(rc)^(wp>>2))&1);
   wn=int'(rc)-(l>>2);
   wt=256*wn+128*int'(pid)+16*l+int'(ac);
   if(chk_window&&wn>=0&&wt<int'(lim))begin pexp_v[wp]=1'b1;pexp_t[wp]=14'(wt);end
  end
  for(l=0;l<8;l=l+1)begin
   wn=int'(rn)-(l>>2);
   wt=256*wn+128*int'(pid)+16*l+int'(an);
   if(next_window&&wn>=0&&wt<int'(lim))exp_take[l]=1'b1;
  end
 end
 wire[7:0] rq;wire[111:0] rqt;
 ot_qwen_tp8_vrow_wide u_req(.clk(clk),.rst_n(local_rst_n),.pair_id(pid),.start(start_r),.context_len(ctx_r),
  .req_valid(rq),.req_t(rqt),.fault());
 always @(posedge clk or negedge local_rst_n)if(!local_rst_n)req_valid<=0;else req_valid<=rq;
 always @(posedge clk)req_t<=rqt;
 reg cbad;integer k;
 wire out_slot=(state==JOIN)&&wage==6'(COL_LAT+1);
 always @*begin
  cbad=0;
  if(state!=IDLE&&iv_r!=pexp_v)cbad=1;
  for(k=0;k<8;k=k+1)if(iv_r[k]&&(it_r[14*k+:14]!=pexp_t[k]||ie_r[16*k+:16]!=ep))cbad=1;
  if(|cf_r)cbad=1;
  if(cv_r!={32{cv_r[0]}})cbad=1;
  if(state!=IDLE&&cv_r[0]!=out_slot)cbad=1;
 end
 // column command word, registered at this tile's output pin (the column registers it again at its input pin)
 wire n0_lo=(rn==0),n0_hi=(rn==1);
 always @(posedge clk or negedge local_rst_n)
  if(!local_rst_n)cmd<=0;
  else begin
   cmd<=0;
   cmd[0]<=rn[0];cmd[8:1]<=exp_take&{8{!flt}};cmd[9]<=n0_lo;cmd[10]<=n0_hi;cmd[14:11]<=an;
   cmd[15]<=(state==FEED)&&pa>=1&&pa<=16;cmd[19:16]<=4'(pa-1);
   cmd[20]<=(state==TRA)||(state==TRB);cmd[24:21]<={ti,1'b0}+4'(state==TRB);
   cmd[25]<=state==TRADD;cmd[26]<=state==TRB;cmd[27]<=nodes==2;cmd[30:28]<=ti;
   cmd[31]<=(state==JOIN)&&wage==6'(JGO);
  end
 // output pin registers: flags and the static output age (service cycles after start_pv: + the start pin register)
 always @(posedge clk or negedge local_rst_n)
  if(!local_rst_n)begin fault<=0;busy<=0;out_age<=0;out_epoch<=0;end
  else begin
   fault<=flt;busy<=state!=IDLE;out_epoch<=ep;
   out_age<=16'd1+16'(FIRSTI)+nq-16'd1+16'd13+16'd73+16'(COL_LAT);
  end
 always @(posedge clk or negedge local_rst_n)begin
  if(!local_rst_n)begin state<=IDLE;flt<=0;age<=0;ep<=0;lim<=0;nq<=0;nodes<=0;ti<=0;drain_left<=0;reduce_left<=0;wage<=0;end
  else if((start_r&&state!=IDLE)||(state!=IDLE&&cbad))begin state<=IDLE;flt<=1;end
  else begin
   if(state!=IDLE)age<=age+1'b1;
   case(state)
    IDLE:if(start_r)begin
     ep<=epoch_r;lim<=ctx_r;age<=0;
     nq<=(ctx_r>14'(128*int'(pid)))?16'(16*(((int'(ctx_r)-128*int'(pid)+255)>>8)+1)):16'd0;
     if(ctx_r==0||ctx_r>8192)flt<=1;else state<=FEED;
    end
    FEED:if(pa>=16'(FIRSTI)+nq-16'd1&&pa>=16'd16)begin state<=DRAIN;drain_left<=12;end
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
    JOIN:begin wage<=wage+1'b1;if(wage==6'(COL_LAT+1))state<=IDLE;end
    default:;
   endcase
  end
 end
endmodule

// Per-pair V request calendar (the same walk as the pair): port order {stack PAIR lanes 0-3, stack PAIR+2 lanes 0-3}.
// Bank l issues on lane l&3 of stack 2(n&1)+PAIR; the low and high half always hit different stacks in one cycle.
module ot_qwen_tp8_vrow_wide (
 input wire clk,rst_n,pair_id,start,input wire[13:0] context_len,
 output reg[7:0] req_valid,output reg[111:0] req_t,output reg fault
);
 reg active;reg[15:0] q;reg[15:0] nq;reg[13:0] lim;
 integer l,wn,wt,wp;                          // loop temporaries (blocking, combinational only; no automatic decls for yosys)
 always @*begin
  req_valid=0;req_t=0;wn=0;wt=0;wp=0;
  if(active&&q<nq)for(wp=0;wp<8;wp=wp+1)begin      // per PORT, constant index (see ot_qwen_tp8_pv_wide_ctl)
   l=(wp&3)+4*((int'(q>>4)^(wp>>2))&1);
   wn=int'(q>>4)-(l>>2);
   wt=256*wn+128*int'(pair_id)+16*l+int'(q&15);
   if(wn>=0&&wt<int'(lim))begin req_valid[wp]=1'b1;req_t[14*wp+:14]=14'(wt);end
  end
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin active<=0;q<=0;nq<=0;lim<=0;fault<=0;end
  else if(start)begin
   if(active&&q<nq)fault<=1;
   active<=1;q<=0;lim<=context_len;
   nq<=(context_len>14'(128*int'(pair_id)))?16'(16*(((int'(context_len)-128*int'(pair_id)+255)>>8)+1)):16'd0;
  end else if(active)begin
   if(q<nq)q<=q+1'b1;else active<=0;
  end
endmodule
