// Opt-in CAPTURE-COLLAR successor, 2026-10-10. Adds one bank-local capture edge
// before raw_q; request, credit, identity and exact data contracts remain intact.
// Every cap_q must be anchored beside its own macro rd_out pin by rx_capture_at_macros.tcl.
// The registered bank output transports to raw_q after the local macro clk->q capture.
module ot_ha2_truecredit_receiver_s #(
 parameter integer W=544, INJ=2, AW=6, TAGW=16, MUTANT=0,
 parameter integer CREDIT=1, CRD=8
)(input wire clk,rst_n,
 input wire[INJ-1:0] arrival_v,receiver_ready,
 input wire[INJ*W-1:0] arrival_data,
 input wire[INJ*TAGW-1:0] arrival_tag,
 output reg[INJ-1:0] send_v,return_v,
 output reg[INJ*W-1:0] send_data,
 output reg[INJ*TAGW-1:0] return_tag,
 output reg quiet,fault);
 initial if(TAGW<=AW)$fatal(1,"HA2 truecredit tags must exceed slot address width");
 initial if(AW!=6)$fatal(1,"HA2 SRAM receiver: 64-deep queue (ot_sram_1r1w_64x512) only");
 initial if(CREDIT!=1)$fatal(1,"HA2 SRAM receiver: credit ready only (CREDIT=1)");
 initial if(CRD<1)$fatal(1,"HA2 truecredit receiver CRD must be >= 1");
 localparam integer D=1<<AW;
 localparam integer FW=W+TAGW;
 localparam integer NM=(FW+511)/512;
 localparam integer CRW=$clog2(CRD+2)+1;
 localparam integer CR0=CRD+((MUTANT==5)?1:0);
 wire[INJ-1:0] bads,idle;
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  reg rst_l;
  always @(posedge clk or negedge rst_n)if(!rst_n)rst_l<=1'b0;else rst_l<=1'b1;
  // pin capture
  reg av_q;
  reg[TAGW-1:0] tag_q;
  reg[W-1:0] data_q;
  always @(posedge clk or negedge rst_n)if(!rst_n)av_q<=1'b0;else av_q<=arrival_v[i];
  always @(posedge clk)begin tag_q<=arrival_tag[i*TAGW+:TAGW];data_q<=arrival_data[i*W+:W];end
  reg[TAGW-1:0] expect_arrival,expect_retire;
  reg bad,ovf;
  reg[AW:0] wp,rp,wp_q;
  wire empty=wp==rp;
  wire full=(wp[AW]!=rp[AW])&&(wp[AW-1:0]==rp[AW-1:0]);
  wire readable=((MUTANT==7)?wp:wp_q)!=rp;
  wire valid_arrival=av_q&&tag_q==expect_arrival&&!bad;
  // credit counter (registered cr_ok, as receiver_p CREDIT=1)
  reg cr_q,cr_ok,home_r,cr_ovf;
  reg[CRW-1:0] cred;
  wire fetch=readable&&cr_ok&&!bad;
  wire cr_in=(MUTANT==8)?1'b0:cr_q;
  wire[CRW-1:0] cred_n=cred+CRW'(cr_in)-CRW'(fetch);
  always @(posedge clk or negedge rst_l)
   if(!rst_l)begin cr_q<=1'b0;cred<=CRW'(CR0);cr_ok<=1'b1;home_r<=1'b1;cr_ovf<=1'b0;end
   else begin
    cr_q<=receiver_ready[i];cred<=cred_n;cr_ok<=cred_n!=0;home_r<=cred_n==CRW'(CR0);
    if(cr_in&&!fetch&&cred==CRW'(CR0))cr_ovf<=1'b1;
   end
  wire cr_home=home_r&&!cr_q;
  // WREG write side: slot wp, registered at the macro inputs
  reg w_ce_q;reg[AW-1:0] w_addr_q;reg[NM*512-1:0] wd_q;
  always @(posedge clk or negedge rst_l)if(!rst_l)w_ce_q<=1'b0;else w_ce_q<=av_q&&!full;
  always @(posedge clk)begin
   w_addr_q<=wp[AW-1:0];wd_q<={{(NM*512-FW){1'b0}},tag_q,data_q};
  end
  // storage: NM x 64x512 1R1W macros
  wire[AW-1:0] r_addr=(MUTANT==4)?(rp[AW-1:0]+1'b1):rp[AW-1:0];
  reg r_ce_q;reg[AW-1:0] r_addr_q;                          // RREG: read request registered at the macro inputs
  always @(posedge clk or negedge rst_l)if(!rst_l)r_ce_q<=1'b0;else r_ce_q<=fetch;
  always @(posedge clk)r_addr_q<=r_addr;
  wire[NM*512-1:0] ram_q, cap_bus;
  for(genvar m=0;m<NM;m=m+1)begin:g_ram
   ot_sram_1r1w_64x512_m1_r2c2 storage(.clk(clk),.r_ce_in(r_ce_q),.r_addr_in(r_addr_q),.rd_out(ram_q[m*512+:512]),
    .w_ce_in(w_ce_q),.w_addr_in(w_addr_q),.wd_in(wd_q[m*512+:512]),.w_mask_in({512{1'b1}}),
    .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
   localparam integer CBITS=((FW-m*512)>512)?512:(FW-m*512);
   (* keep = 1 *) reg[CBITS-1:0] cap_q;
   always @(posedge clk) cap_q<=ram_q[m*512+:CBITS];
   assign cap_bus[m*512+:512]={{(512-CBITS){1'b0}},cap_q};
  end
  // read pipeline: v0 = request at the macro inputs, v1 = macro output valid this edge, v2 = raw_q holds the item
  reg v0,v1,v2,v3;reg[FW-1:0] raw_q;
  always @(posedge clk)raw_q<=cap_bus[FW-1:0];
  wire[TAGW-1:0] raw_tag=raw_q[W+:TAGW];
  wire deliver=v3&&!bad;
  assign bads[i]=bad||ovf||cr_ovf;
  assign idle[i]=empty&&!av_q&&!w_ce_q&&!v0&&!v1&&!v2&&!v3&&!send_v[i]&&!return_v[i]&&cr_home;
  always @(posedge clk or negedge rst_l)
   if(!rst_l)begin
    expect_arrival<=0;expect_retire<=0;bad<=0;ovf<=0;wp<=0;rp<=0;wp_q<=0;v0<=0;v1<=0;v2<=0;v3<=0;
    send_v[i]<=0;return_v[i]<=0;return_tag[i*TAGW+:TAGW]<=0;
   end else begin
    wp_q<=wp;v0<=fetch;v1<=v0;v2<=v1;v3<=(MUTANT==9)?v1:v2;
    send_v[i]<=deliver;return_v[i]<=deliver;
    if(av_q&&!valid_arrival)bad<=1;
    if(valid_arrival)begin
     expect_arrival<=expect_arrival+1'b1;
     if(full)ovf<=1'b1;else wp<=wp+1'b1;
    end
    if(fetch)rp<=rp+1'b1;
    if(deliver)begin
     if(raw_tag!=expect_retire)bad<=1;
     return_tag[i*TAGW+:TAGW]<=raw_tag ^ ((MUTANT==2)?TAGW'(1):TAGW'(0));
     expect_retire<=expect_retire+1'b1;
    end
   end
  always @(posedge clk)send_data[i*W+:W]<=raw_q[W-1:0];
 end
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin quiet<=1'b1;fault<=1'b0;end
  else begin quiet<=&idle;fault<=|bads;end
endmodule
