`default_nettype none
// HBM-NEXT-UNITS-IDXN 2026-10-19: N-row IDX.INDEX issuer for ONE key stream (successor of ot_hnx_idx_calendar_rows).
// The programme SRAM holds ONE row frame (length F <= 2048 instructions, d4g instruction format unchanged:
// [31]weight [30]query [29]heademit [28]keybeat [27:20]index [19:16]selop [15:14]pass [13:6]seladdr [5]linkflush
// [4]linkemit [3:0]linkgroup; [5]&[4] = link row clear). Row r (0 .. N-1) is the frame launched r x pitch edges after
// start on stream r mod K (K <= 8 issue streams). The rows are PIPELINED (pitch ~ F / 6), so up to K rows are in flight.
// Streams share ONE frame SRAM: stream k owns the read port on edges t = k mod 8 and keeps a 4-row (32-instruction)
// window; rows 0..3 are captured at programme load (head) and copied in at launch, so every stream issues instruction 0
// three edges after its launch exactly as ot_hbm_idx_calendar_static (N = 1 with the d4g programme = the d4g issuer).
// Each stream fetches its next row in its own slot (it needs one row per 8 edges and gets one slot per 8 edges).
// The streams' instructions are NOT OR-ed: every field class is routed to its unit from the ONE stream that owns it on
// that edge, tagged with that stream's row; two streams in one class on one edge = collision = FAULT (static schedule,
// no arbitration, no ready/credit):
//   OPR  weight/query operand slots + index[26:20]      (one operand reader)
//   QEM  query head emit + index[24:20]                 (one query unit)
//   KEY  key beat + index[27:20] + row                  (scorers; row 0 = live HBM key line, row >= 1 = replay buffer)
//   PRE  key beat of row >= 1 one edge ahead (lookahead from the issue stage-1) = replay-buffer read slot
//   SEL  selector op/pass/addr, routed to selector (row mod S): one class per selector
//   LIN  link row clear / flush + row (link ingest side)    LOUT  link emit + group + row (link TX side)
// QUERY-RELOAD HAZARD (checked, = fault): the hslices hold ONE query and use it up to 27 edges after a key (block 3 at
// +14, head weight at +27), so a head emit (next row's query) less than G2MIN issue slots after the last key beat FAULTS.
// CW=1 COMPACT WINDOWS (HBM-NEXT-UNITS-QCTL 2026-10-19, opt-in; CW=0 = the structure above, unchanged): the 4-row head
// copy per stream (8 x 1,024 b + 1,024 b head = 9,216 flops, hnx_idxq_qctl gate: clock pin-flop spread 104 ps > 80) is
// replaced by ONE shared head row 0 (256 b, read by every stream while pc < 8) and a 2-row ring per stream (512 b):
// row f (f >= 1) is fetched in the stream's own TDM slot while the stream issues row f - 1 (exactly one slot falls in
// those 8 edges), into ring slot f mod 2 (row f - 2: finished); a fetch on the last edge of row f - 1 lands on the
// edge that reads row f's first word, which then reads the SRAM output word directly (bypass). Same instruction on
// every edge as CW=0 (4,352 flops instead of 9,216; no 1,024-b head copy at launch). Only the read port slots change.
// CW=2 NO-BYPASS COMPACT WINDOWS (HBM-NEXT-UNITS IDXQ 2026-10-19; qctl gate 4: CW=1's landing bypass put the frame SRAM
// read data (clk_mem) combinationally in front of the stream instruction register, cross-clock setup -15.7 ps): shared head
// rows 0 AND 1 (512 b) and a 3-row ring per stream (768 b): row f (f >= 2) is fetched while the stream issues row f - 2
// (one TDM slot in those 8 edges), so it lands no later than the first edge of row f - 1 and the SRAM output only ever
// feeds ring registers (as CW=0's window); ring slot = row mod 3 (row f - 3 finished). 6,656 instead of 9,216 flops.
module ot_hnx_idxn_calendar #(parameter integer K=8,S=4,G2MIN=23,CW=0)(
 input wire clk,clk_mem,rst_n,
 input wire program_we,input wire[7:0]program_addr,input wire[255:0]program_data,
 input wire start,input wire[11:0]length,input wire[4:0]n_rows,input wire[11:0]pitch,
 output wire row_start,
 output wire opr_weight,opr_query,output wire[6:0]opr_index,
 output wire qem_v,output wire[4:0]qem_head,
 output wire key_v,output wire[7:0]key_index,output wire[4:0]key_row,
 output wire pre_v,output wire[7:0]pre_index,
 output wire[4*S-1:0]sel_op,output wire[2*S-1:0]sel_pass,output wire[8*S-1:0]sel_addr,
 output wire lin_clear,lin_flush,output wire[4:0]lin_row,
 output wire lout_emit,output wire[3:0]lout_group,output wire[4:0]lout_row,
 output wire done,output reg fault
);
 // ---- head rows 0..3 (captured at programme load) and the shared frame SRAM (TDM read port)
 reg[1023:0]head;
 if(CW==0)begin:ghead
  always @(posedge clk)if(program_we&&program_addr<8'd4)head[program_addr[1:0]*256+:256]<=program_data;
 end else begin:ghead0
  if(CW==1)begin:gh1
   always @(posedge clk)if(program_we&&program_addr==8'd0)head[255:0]<=program_data;   // row 0 only (shared)
   always @* head[1023:256]=768'd0;
  end else begin:gh2
   always @(posedge clk)if(program_we&&program_addr<8'd2)head[program_addr[0]*256+:256]<=program_data; // rows 0, 1 (shared)
   always @* head[1023:512]=512'd0;
  end
 end
 wire[31:0]raw_w[0:7];wire[31:0]head_w[0:7];
 for(genvar j=0;j<8;j=j+1)begin:gw assign raw_w[j]=raw[j*32+:32];assign head_w[j]=head[j*32+:32];end
 reg[2:0]tdm;
 always @(posedge clk or negedge rst_n)if(!rst_n)tdm<=0;else tdm<=tdm+3'd1;
 wire[K-1:0]want;wire[9*K-1:0]fnext;
 wire rd_ce=want[tdm];wire[7:0]rd_addr=fnext[int'(tdm)*9+:8];
 wire[255:0]raw;
 ot_sram_1r1w_256x256_m2_r2c2 store(.clk(clk_mem),.r_ce_in(rd_ce),.r_addr_in(rd_addr),.rd_out(raw),
  .w_ce_in(program_we),.w_addr_in(program_addr),.wd_in(program_data),.w_mask_in({256{1'b1}}),
  .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 // ---- row launches
 reg[4:0]rows_left,next_row,dones_left;reg[11:0]timer;reg[5:0]since_key;
 wire launch=!start&&rows_left!=0&&timer==pitch;
 assign row_start=start||launch;
 wire[4:0]go_row=start?5'd0:next_row;
 // ---- streams
 wire[K-1:0]sv,s1v,sd,sbusy;wire[32*K-1:0]si,s1i;wire[5*K-1:0]srow;
 function automatic [3*K-1:0] selmap(input [5*K-1:0]r);
  for(integer k=0;k<K;k=k+1)selmap[k*3+:3]=3'(int'(r[k*5+:5])%S);
 endfunction
 wire[3*K-1:0]sel_of=selmap(srow);            // selector of each stream's row (one wire: the bench forces it for MUT 22)
 for(genvar k=0;k<K;k=k+1)begin:gs
  wire go=row_start&&(go_row%K)==k;
  reg act;reg[11:0]pc,lim;reg[4:0]row;reg[8:0]f;reg fp;reg[1:0]fslot;
  reg v1,last1;reg[31:0]i1;reg iv,dn;reg[31:0]ins;
  // CW=0: rows 0..3 from the launch copy, prefetch up to 4 rows ahead; CW=1: row f fetched while issuing row f - 1
  assign want[k]=act&&f<9'd256&&{f,3'd0}<{1'b0,lim}&&f<{1'b0,pc[11:3]}+(CW==0?9'd4:CW==1?9'd2:9'd3);
  assign fnext[k*9+:9]=f;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin act<=0;pc<=0;lim<=0;row<=0;f<=0;fp<=0;fslot<=0;v1<=0;last1<=0;iv<=0;dn<=0;end
   else begin
    v1<=act;last1<=pc+12'd1==lim;iv<=v1;dn<=v1&&last1;
    fp<=0;
    if(go)begin act<=1;pc<=0;lim<=length;row<=go_row;f<=(CW==0?9'd4:CW==1?9'd1:9'd2);end
    else begin
     if(act)begin pc<=pc+12'd1;if(pc+12'd1==lim)act<=0;end
     if(tdm==3'(k)&&want[k])begin f<=f+9'd1;fp<=1;fslot<=f[1:0];end
    end
   end
  end
  if(CW==0)begin:gwin
   reg[1023:0]win;
   always @(posedge clk)begin
    i1<=win[pc[4:3]*256+pc[2:0]*32+:32];ins<=v1?i1:32'd0;
    if(go)win<=head;
    else if(fp)win[fslot*256+:256]<=raw;
   end
  end else if(CW==2)begin:gring3
   reg[31:0]ring[0:23];reg[1:0]rs,ws,wl;      // 3 rows x 8 words; rs = (issued row) mod 3, ws = (next fetched row) mod 3
   always @(posedge clk)begin
    i1<=(pc[11:4]==8'd0)?head[pc[3:0]*32+:32]:ring[rs*8+int'(pc[2:0])];ins<=v1?i1:32'd0;
    if(go)begin rs<=0;ws<=2'd2;end
    else begin
     if(act&&pc[2:0]==3'd7)rs<=(rs==2'd2)?2'd0:rs+2'd1;
     if(tdm==3'(k)&&want[k])begin wl<=ws;ws<=(ws==2'd2)?2'd0:ws+2'd1;end
    end
    if(fp)for(integer j=0;j<8;j=j+1)ring[wl*8+j]<=raw_w[j];
   end
  end else begin:gring
   reg[31:0]ring[0:15];                       // 2 rows x 8 words; slot = row parity
   wire byp=fp&&pc[11:3]==f-9'd1;              // the row landing on this edge is the row read on this edge
   always @(posedge clk)begin
    i1<=(pc[11:3]==9'd0)?head_w[pc[2:0]]:byp?raw_w[pc[2:0]]:ring[pc[3:0]];ins<=v1?i1:32'd0;
    if(fp)for(integer j=0;j<8;j=j+1)if(fslot[0])ring[8+j]<=raw_w[j];else ring[j]<=raw_w[j];
   end
  end
  assign sbusy[k]=act||v1||iv;
  assign sv[k]=iv;assign si[k*32+:32]=ins;assign sd[k]=dn;assign srow[k*5+:5]=row;
  assign s1v[k]=v1;assign s1i[k*32+:32]=i1;
 end
 // ---- class routing: each class from the ONE stream that owns it on this edge (OR of one), collision = fault
 function automatic integer cnt(input [K-1:0]h);cnt=$countones(h);endfunction
 wire[K-1:0]h_opr,h_qem,h_key,h_pre,h_lin,h_out;
 for(genvar k=0;k<K;k=k+1)begin:gh
  wire[31:0]w=si[k*32+:32],w1=s1i[k*32+:32];
  assign h_opr[k]=sv[k]&&(w[31]||w[30]);
  assign h_qem[k]=sv[k]&&w[29];
  assign h_key[k]=sv[k]&&w[28];
  assign h_pre[k]=s1v[k]&&w1[28]&&srow[k*5+:5]!=0;
  assign h_lin[k]=sv[k]&&w[5];
  assign h_out[k]=sv[k]&&w[4]&&!w[5];
 end
 reg[31:0]x_opr,x_qem,x_key,x_pre,x_lin,x_out;reg[4:0]r_key,r_lin,r_out;
 reg[4*S-1:0]x_op;reg[2*S-1:0]x_ps;reg[8*S-1:0]x_ad;reg sel_coll;integer n;
 always @*begin
  x_opr=0;x_qem=0;x_key=0;x_pre=0;x_lin=0;x_out=0;r_key=0;r_lin=0;r_out=0;x_op=0;x_ps=0;x_ad=0;sel_coll=0;
  for(integer k=0;k<K;k=k+1)begin
   if(h_opr[k])x_opr=x_opr|si[k*32+:32];
   if(h_qem[k])x_qem=x_qem|si[k*32+:32];
   if(h_key[k])begin x_key=x_key|si[k*32+:32];r_key=r_key|srow[k*5+:5];end
   if(h_pre[k])x_pre=x_pre|s1i[k*32+:32];
   if(h_lin[k])begin x_lin=x_lin|si[k*32+:32];r_lin=r_lin|srow[k*5+:5];end
   if(h_out[k])begin x_out=x_out|si[k*32+:32];r_out=r_out|srow[k*5+:5];end
  end
  for(integer s=0;s<S;s=s+1)begin
   n=0;
   for(integer k=0;k<K;k=k+1)if(sv[k]&&si[k*32+6+:14]!=0&&int'(sel_of[k*3+:3])==s)begin
    n=n+1;x_op[s*4+:4]=x_op[s*4+:4]|si[k*32+16+:4];x_ps[s*2+:2]=x_ps[s*2+:2]|si[k*32+14+:2];x_ad[s*8+:8]=x_ad[s*8+:8]|si[k*32+6+:8];
   end
   if(n>1)sel_coll=1;
  end
 end
 assign opr_weight=x_opr[31];assign opr_query=x_opr[30];assign opr_index=x_opr[26:20];
 assign qem_v=|h_qem;assign qem_head=x_qem[24:20];
 assign key_v=|h_key;assign key_index=x_key[27:20];assign key_row=r_key;
 assign pre_v=|h_pre;assign pre_index=x_pre[27:20];
 assign sel_op=x_op;assign sel_pass=x_ps;assign sel_addr=x_ad;
 assign lin_clear=(|h_lin)&&x_lin[4];assign lin_flush=(|h_lin)&&!x_lin[4];assign lin_row=r_lin;
 assign lout_emit=|h_out;assign lout_group=x_out[3:0];assign lout_row=r_out;
 wire coll=cnt(h_opr)>1||cnt(h_qem)>1||cnt(h_key)>1||cnt(h_pre)>1||cnt(h_lin)>1||cnt(h_out)>1||sel_coll;
 // ---- record control
 assign done=(|sd)&&dones_left==5'd1;          // the last row's last issue edge (= the d4g done edge at N = 1)
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rows_left<=0;next_row<=0;timer<=0;dones_left<=0;fault<=0;since_key<=0;end
  else begin
   if(start)since_key<=0;else if(key_v)since_key<=6'd1;else if(since_key!=0&&since_key!=6'd63)since_key<=since_key+6'd1;
   if(qem_v&&since_key!=0&&int'(since_key)<G2MIN)fault<=1;
   if(start)begin
    rows_left<=n_rows-5'd1;next_row<=5'd1;timer<=12'd1;dones_left<=n_rows;
    if(n_rows==0||n_rows>16||(n_rows>1&&pitch==0)||rows_left!=0||dones_left!=0||length==0||length>2048)fault<=1;
   end else begin
    timer<=launch?12'd1:timer+12'd1;
    if(launch)begin rows_left<=rows_left-5'd1;next_row<=next_row+5'd1;end
   end
   if((|sd)&&dones_left!=0&&!start)dones_left<=dones_left-5'(cnt(sd));
   if(row_start&&sbusy[int'(go_row)%K])fault<=1;          // launch onto a busy stream
   if(program_we&&(|sbusy))fault<=1;
   if(coll)fault<=1;
  end
 end
endmodule
`default_nettype wire
