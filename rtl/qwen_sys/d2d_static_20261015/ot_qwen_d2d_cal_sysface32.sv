`timescale 1ns/1ps
// Generic source-bounded SAFE7 calendar. Keep ot_qwen_syscal32_and as a
// non-flattened synthesis module, and KEEP the duplicated parent producers.
// NE is 16, 32 or 64. The largest indexed table is exactly 2048 bits.
// All externally replicated controls denote the SAME original cycle/value.
// No execution edge, configuration edge, or first-entry prefetch changes.
(* keep_hierarchy="yes" *) module ot_qwen_syscal32_and(input wire a,b, output wire y);
  assign y=a&b;
endmodule

module ot_qwen_d2d_cal_sysface32 #(
  parameter integer NE=32, AW=$clog2(NE), G=NE/16, NB=(NE+31)/32,
  parameter integer MUT=0
) (
  input wire ck,
  // reset 0: control+rep/bcur <=32FF; 1:cur32FF; 2:cnt14FF;
  // reset 3+2g / 4+2g: the two 16-bit pointer-select groups.
  input wire [3+2*G-1:0] rst_n,
  input wire cfg_we,
  input wire [AW:0] cfg_addr,
  // Each independent 32-bit producer supplies at most 32 table words.
  input wire [NB*32-1:0] cfg_data_k,
  // Three independent segment decoder producers per 16-entry group,
  // followed by the binary segment-base producer.
  input wire [(3*G+1)*AW-1:0] cfg_seg_k,
  // 0:curhi14,1:curmid8,2:curlo10,3:rep/bcur10,4:cnt14,5:control,
  // 6+2g / 7+2g: the two pointer-select groups, each16bits.
  input wire [6+2*G-1:0] start_k, halt_k,
  // 0:firsthi14,1:firstmid8,2:firstlo10,3:binarybase,
  // 4+g: pointer-start group16.
  input wire [4+G-1:0] seg_k,
  output reg ev_v,
  output reg [2:0] ev_port,
  output reg [3:0] ev_kind,
  output reg [4:0] ev_beat,
  output reg running, fault
);
  localparam integer WGROUPS=NE/8;
  wire cwn=cfg_we&&!running;
  wire we_t=cwn&&!cfg_addr[AW];
  wire [WGROUPS*4-1:0] wg;
  wire [NE*32-1:0] tblf;
  genvar q,c,i,g;
  for(q=0;q<WGROUPS;q=q+1) begin:g_wq
    wire qm=cfg_addr[AW-1:3]==q;
    for(c=0;c<4;c=c+1) begin:g_lane
      ot_qwen_syscal32_and u_group(.a(we_t),.b(qm),.y(wg[q*4+c]));
    end
  end
  for(i=0;i<NE;i=i+1) begin:g_tbl
    wire am=cfg_addr[2:0]==(i%8);
    for(c=0;c<4;c=c+1) begin:g_lane
      (* keep="true" *) reg [7:0] word_q;
      wire wen;
      wire lane_match=(MUT==5 && c==2)?(cfg_addr[2:0]==((i%8)^1)):am;
      ot_qwen_syscal32_and u_enable(.a(wg[(i/8)*4+c]),.b(lane_match),.y(wen));
      always @(posedge ck) if(wen) word_q<=cfg_data_k[(i/32)*32+c*8+:8];
      assign tblf[i*32+c*8+:8]=word_q;
    end
  end
  wire [3*G:0] ws;
  for(i=0;i<3*G+1;i=i+1) begin:g_ws
    ot_qwen_syscal32_and u_enable(.a(cwn),.b(cfg_addr[AW]),.y(ws[i]));
  end
  (* keep="true" *) reg [AW-1:0] seg1;
  (* keep="true" *) reg [NE-1:0] s1oh,s1oh_b,s1p1oh;
  for(g=0;g<G;g=g+1) begin:g_segment
    wire [NE-1:0] d0={{(NE-1){1'b0}},1'b1}<<cfg_seg_k[(3*g)*AW+:AW];
    wire [NE-1:0] db={{(NE-1){1'b0}},1'b1}<<cfg_seg_k[(3*g+1)*AW+:AW];
    wire [AW-1:0] next_seg=cfg_seg_k[(3*g+2)*AW+:AW]+1'b1;
    wire [NE-1:0] d1={{(NE-1){1'b0}},1'b1}<<next_seg;
    always @(posedge ck) if(ws[3*g]) s1oh[16*g+:16]<=d0[16*g+:16];
    always @(posedge ck) if(ws[3*g+1]) s1oh_b[16*g+:16]<=db[16*g+:16];
    always @(posedge ck) if(ws[3*g+2]) s1p1oh[16*g+:16]<=d1[16*g+:16];
  end
  always @(posedge ck) if(ws[3*G]) seg1<=cfg_seg_k[3*G*AW+:AW];
  (* keep="true" *) reg [NE-1:0] oh,oh_b;
  reg [31:0] t1,tn;
  integer j;
  always @* begin
    t1=0;tn=0;
    for(j=0;j<NE;j=j+1) begin
      t1[15:0]=t1[15:0]|(s1oh[j]?tblf[j*32+:16]:16'd0);
      t1[31:16]=t1[31:16]|(s1oh_b[j]?tblf[j*32+16+:16]:16'd0);
      tn[15:0]=tn[15:0]|(oh[j]?tblf[j*32+:16]:16'd0);
      tn[31:16]=tn[31:16]|(oh_b[j]?tblf[j*32+16+:16]:16'd0);
    end
  end
  reg [31:0] first0_q,first1_q;
  reg cfg_recent;
  always @(posedge ck) begin
    first0_q<=tblf[31:0]; first1_q<=t1; cfg_recent<=cfg_we;
  end
  wire [31:0] first={seg_k[0]?first1_q[31:18]:first0_q[31:18],
    seg_k[1]?first1_q[17:10]:first0_q[17:10],seg_k[2]?first1_q[9:0]:first0_q[9:0]};
  wire [31:0] nxt=tn;
  wire [AW-1:0] sb=seg_k[3]?seg1:{AW{1'b0}};
  wire [NE-1:0] oh_start;
  wire [NE-1:0] segment_next=(MUT==2)?s1oh:s1p1oh;
  for(g=0;g<G;g=g+1) begin:g_start_pointer
    localparam [NE-1:0] ONE_NEXT=2;
    assign oh_start[g*16+:16]=seg_k[4+g]?segment_next[g*16+:16]:ONE_NEXT[g*16+:16];
  end
  reg [31:0] cur;
  reg [13:0] cnt;
  reg [4:0] rep,bcur;
  reg [AW:0] ptr;
  wire fire=running&&cnt==14'd1;
  wire step=rep==0&&!cur[17];
  wire [5+2*G-1:0] adv;
  for(i=0;i<5+2*G;i=i+1) begin:g_advance
    ot_qwen_syscal32_and u_advance(.a(fire),.b(step),.y(adv[i]));
  end
  always @(posedge ck or negedge rst_n[0]) begin
    if(!rst_n[0]) begin
      running<=0;ev_v<=0;ev_port<=0;ev_kind<=0;ev_beat<=0;ptr<=0;fault<=0;
    end else begin
      ev_v<=0;
      if(cfg_we&&running) fault<=1;
      if(halt_k[5]) running<=0;
      else if(start_k[5]) begin
        if(running||cfg_we||cfg_recent) fault<=1;
        running<=1;ptr<={1'b0,sb}+1'b1;
        if(first[31:18]==0||{1'b0,first[9:5]}+{1'b0,first[4:0]}>31) fault<=1;
      end else if(fire) begin
        ev_v<=1;ev_port<=cur[16:14];ev_kind<=cur[13:10];ev_beat<=bcur;
        if(rep!=0) begin end
        else if(cur[17]) running<=0;
        else begin
          if(ptr==NE) fault<=1;
          if(nxt[31:18]==0||{1'b0,nxt[9:5]}+{1'b0,nxt[4:0]}>31) fault<=1;
          ptr<=ptr+1'b1;
        end
      end
    end
  end
  always @(posedge ck or negedge rst_n[1])
    if(!rst_n[1]) cur[31:18]<=0;
    else if(!halt_k[0]&&start_k[0]) cur[31:18]<=first[31:18];
    else if(!halt_k[0]&&adv[0]) cur[31:18]<=nxt[31:18];
  always @(posedge ck or negedge rst_n[1])
    if(!rst_n[1]) cur[17:10]<=0;
    else if(!halt_k[1]&&start_k[1]) cur[17:10]<=first[17:10];
    else if(!halt_k[1]&&adv[1]) cur[17:10]<=nxt[17:10];
  always @(posedge ck or negedge rst_n[1])
    if(!rst_n[1]) cur[9:0]<=0;
    else if(!halt_k[2]&&start_k[2]) cur[9:0]<=first[9:0];
    else if(!halt_k[2]&&adv[2]) cur[9:0]<=nxt[9:0];
  always @(posedge ck or negedge rst_n[2])
    if(!rst_n[2]) cnt<=0;
    else if(!halt_k[4]&&start_k[4]) cnt<=first[31:18];
    else if(!halt_k[4]&&adv[4]) cnt<=nxt[31:18];
    else if(!halt_k[4]&&running&&cnt!=1) cnt<=cnt-1'b1;
  always @(posedge ck or negedge rst_n[0])
    if(!rst_n[0]) begin rep<=0;bcur<=0;end
    else if(!halt_k[3]&&start_k[3]) begin rep<=first[4:0];bcur<=first[9:5];end
    else if(!halt_k[3]&&fire&&rep!=0) begin rep<=rep-1'b1;bcur<=bcur+1'b1;end
    else if(!halt_k[3]&&adv[3]) begin rep<=nxt[4:0];bcur<=nxt[9:5];end
  wire [NE-1:0] oh_rot={oh[NE-2:0],oh[NE-1]};
  wire [NE-1:0] ohb_rot=(MUT==4)?{oh_b[0],oh_b[NE-1:1]}:{oh_b[NE-2:0],oh_b[NE-1]};
  for(g=0;g<G;g=g+1) begin:g_pointer
    localparam [NE-1:0] INIT=1;
    always @(posedge ck or negedge rst_n[3+2*g])
      if(!rst_n[3+2*g]) oh[g*16+:16]<=INIT[g*16+:16];
      else if(!halt_k[6+2*g]&&start_k[6+2*g]) oh[g*16+:16]<=oh_start[g*16+:16];
      else if(!halt_k[6+2*g]&&adv[5+2*g]) oh[g*16+:16]<=oh_rot[g*16+:16];
    always @(posedge ck or negedge rst_n[4+2*g])
      if(!rst_n[4+2*g]) oh_b[g*16+:16]<=INIT[g*16+:16];
      else if(!halt_k[7+2*g]&&start_k[7+2*g]) oh_b[g*16+:16]<=oh_start[g*16+:16];
      else if(!halt_k[7+2*g]&&adv[6+2*g]) oh_b[g*16+:16]<=ohb_rot[g*16+:16];
  end
endmodule
