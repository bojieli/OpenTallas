// Default-off timing cut: model56a97f0af. Existing credit/tag protocol unchanged.
module ot_ha2_truecredit_receiver_segmented_cx #(
 parameter integer W=544, INJ=2, AW=6, TAGW=16, MUTANT=0,
 parameter integer CREDIT=0, CRD=8, SEGMENTED=0
)(input wire clk,rst_n,
 input wire[INJ-1:0] arrival_v,receiver_ready,
 input wire[INJ*W-1:0] arrival_data,
 input wire[INJ*TAGW-1:0] arrival_tag,
 output reg[INJ-1:0] send_v,return_v,
 output reg[INJ*W-1:0] send_data,
 output reg[INJ*TAGW-1:0] return_tag,
 output reg quiet,fault);
 generate if(SEGMENTED==0)begin:g_original
  ot_ha2_truecredit_receiver_p #(.W(W),.INJ(INJ),.AW(AW),.TAGW(TAGW),.MUTANT(MUTANT),.CREDIT(CREDIT),.CRD(CRD)) u_original
   (.*);
 end else begin:g_segmented
 initial if(TAGW<=AW)$fatal(1,"HA2 truecredit tags must exceed slot address width");
 localparam integer D=1<<AW;
 localparam integer FW=W+TAGW;
 localparam integer GROUPS=8, RG=D/GROUPS;
 initial if(D<8 || D%8)$fatal(1,"segmented receiver needs eight equal row groups");
 wire[INJ-1:0] bads,idle;
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  // 6. local reset release
  reg rst_l;
  always @(posedge clk or negedge rst_n)if(!rst_n)rst_l<=1'b0;else rst_l<=1'b1;
  // 1. pin capture
  reg av_q;
  reg[TAGW-1:0] tag_q;
  reg[W-1:0] data_q;
  always @(posedge clk or negedge rst_n)if(!rst_n)av_q<=1'b0;else av_q<=arrival_v[i];
  always @(posedge clk)begin tag_q<=arrival_tag[i*TAGW+:TAGW];data_q<=arrival_data[i*W+:W];end
  // queue state
  reg[TAGW-1:0] expect_arrival,expect_retire;
  reg bad,ovf;
  reg[AW:0] wp,rp;
  reg[D-1:0] wr_oh,rd_oh;
  reg[FW-1:0] mem[0:D-1];
  wire empty=wp==rp;
  wire full=(wp[AW]!=rp[AW])&&(wp[AW-1:0]==rp[AW-1:0]);
  wire valid_arrival=av_q&&tag_q==expect_arrival&&!bad;
  // credit ready (CREDIT=1) or the same-cycle ready (CREDIT=0)
  localparam integer CRW=$clog2(CRD+2)+1;
  localparam integer CR0=CRD+((MUTANT==5)?1:0);
  wire cr_ok,cr_home,cr_ovf;
  wire pop=!empty&&cr_ok&&!bad;
  if(CREDIT!=0)begin:g_credit
   initial if(CRD<1)$fatal(1,"HA2 truecredit receiver CRD must be >= 1");
   reg cr_q,cr_ok_r,home_r,ovf_r;
   reg[CRW-1:0] cred;
   wire[CRW-1:0] cred_n=cred+CRW'(cr_q)-CRW'(pop);
   always @(posedge clk or negedge rst_l)
    if(!rst_l)begin cr_q<=1'b0;cred<=CRW'(CR0);cr_ok_r<=1'b1;home_r<=1'b1;ovf_r<=1'b0;end
    else begin
     cr_q<=receiver_ready[i];cred<=cred_n;cr_ok_r<=cred_n!=0;home_r<=cred_n==CRW'(CR0);
     if(cr_q&&!pop&&cred==CRW'(CR0))ovf_r<=1'b1;
    end
   assign cr_ok=cr_ok_r;assign cr_home=home_r&&!cr_q;assign cr_ovf=ovf_r;
  end else begin:g_ready
   assign cr_ok=receiver_ready[i];assign cr_home=1'b1;assign cr_ovf=1'b0;
  end
  // 3. AND-OR read mux over the registered one-hot read ring
  wire[D-1:0] rd_sel=(MUTANT==4)?{rd_oh[D-2:0],rd_oh[D-1]}:rd_oh;
  wire[FW-1:0] partial[0:GROUPS-1];
  reg[FW-1:0] partial_q[0:GROUPS-1];
  for(genvar g=0;g<GROUPS;g=g+1)begin:g_read
   reg[FW-1:0] part;
   always @* begin
    part=0;
    for(integer r=0;r<RG;r=r+1)part=part|({FW{rd_sel[g*RG+r]}}&mem[g*RG+r]);
   end
   assign partial[g]=part;
   always @(posedge clk)partial_q[g]<=partial[g];
  end
  reg[FW-1:0] head;
  always @* begin
   head=0;
   for(integer g=0;g<GROUPS;g=g+1)head=head|partial_q[g];
  end
  reg pop_q;
  always @(posedge clk or negedge rst_l)if(!rst_l)pop_q<=0;else pop_q<=pop;
  wire[TAGW-1:0] head_tag=head[W+:TAGW];
  // 2. write enable: registered arrival present, not full, one-hot slot
  wire wr=av_q&&!full;
  for(genvar r=0;r<D;r=r+1)begin:g_slot
   always @(posedge clk)if(wr&&wr_oh[r])mem[r]<={tag_q,data_q};
  end
  assign bads[i]=bad||ovf||cr_ovf;
  assign idle[i]=empty&&!av_q&&!pop_q&&!send_v[i]&&!return_v[i]&&cr_home;
  always @(posedge clk or negedge rst_l)
   if(!rst_l)begin
    expect_arrival<=0;expect_retire<=0;bad<=0;ovf<=0;wp<=0;rp<=0;
    wr_oh<={{(D-1){1'b0}},1'b1};rd_oh<={{(D-1){1'b0}},1'b1};
    send_v[i]<=0;return_v[i]<=0;return_tag[i*TAGW+:TAGW]<=0;
   end else begin
    send_v[i]<=pop_q;return_v[i]<=pop_q;
    if(av_q&&!valid_arrival)bad<=1;
    if(valid_arrival)begin
     expect_arrival<=expect_arrival+1'b1;
     if(full)ovf<=1'b1;
     else begin wp<=wp+1'b1;wr_oh<={wr_oh[D-2:0],wr_oh[D-1]};end
    end
    if(pop)begin
     rp<=rp+1'b1;rd_oh<={rd_oh[D-2:0],rd_oh[D-1]};
    end
    if(pop_q)begin
     if(head_tag!=expect_retire)bad<=1;
     return_tag[i*TAGW+:TAGW]<=head_tag ^ ((MUTANT==2)?TAGW'(1):TAGW'(0));
     expect_retire<=expect_retire+1'b1;
    end
   end
  // 4. head loads every cycle
  always @(posedge clk)send_data[i*W+:W]<=head[W-1:0];
 end
 // 5. registered status
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin quiet<=1'b1;fault<=1'b0;end
  else begin quiet<=&idle;fault<=|bads;end
 end endgenerate
endmodule
