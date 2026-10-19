`timescale 1ns/1ps
// SH storage successor for ot_link_afifo, same ports and write/Gray/credit law.
// Registered SRAM head requires one additional empty-to-nonempty read edge;
// every nonempty pop still advances one word per read clock. Gray stage2 alone
// authorizes reads. No first-stage synchronizer output enters functional logic.
module ot_dsdv_host_afifo_sram #(parameter integer W=514, AW=4, SYNC=2) (
 input wire wclk,wrst_n,wr,input wire [W-1:0] wdata,
 output wire wfull,output reg [AW:0] wfreed,output reg ovf,
 input wire rclk,rrst_n,rd,output wire rempty,
 output wire [W-1:0] rdata,output wire [AW:0] rcount
);
 localparam integer D=1<<AW;
 initial if(W>546||AW>4||AW<2||SYNC<2) $fatal(1,"SH SRAM FIFO unsupported shape");
 function automatic [AW:0] g2b(input [AW:0] g);
  integer k;begin g2b[AW]=g[AW];for(k=AW-1;k>=0;k=k-1)g2b[k]=g2b[k+1]^g[k];end
 endfunction
 reg [AW:0] wbin,wgray,rbin_seen,rbin,rgray;
 (* async_reg="true" *) reg [AW:0] rgray_s[0:SYNC-1],wgray_s[0:SYNC-1];
 wire [AW:0] rgray_w=rgray_s[SYNC-1],wgray_r=wgray_s[SYNC-1];
 wire [AW:0] wbin_n=wbin+1'b1,wgray_n=wbin_n^(wbin_n>>1),rbin_w=g2b(rgray_w);
 assign wfull=(wgray=={~rgray_w[AW:AW-1],rgray_w[AW-2:0]});
 wire push=wr&&!wfull;
 integer i;
 always @(posedge wclk or negedge wrst_n)
  if(!wrst_n) begin
   wbin<=0;wgray<=0;ovf<=0;rbin_seen<=0;wfreed<=0;
   for(i=0;i<SYNC;i=i+1)rgray_s[i]<=0;
  end else begin
   rgray_s[0]<=rgray;for(i=1;i<SYNC;i=i+1)rgray_s[i]<=rgray_s[i-1];
   wfreed<=rbin_w-rbin_seen;rbin_seen<=rbin_w;
   if(wr&&wfull)ovf<=1;
   if(push)begin wbin<=wbin_n;wgray<=wgray_n;end
  end
 reg empty;
 wire pop=rd&&!empty;
 wire [AW:0] rbin_n=rbin+{{AW{1'b0}},pop};
 wire [AW:0] rgray_n=rbin_n^(rbin_n>>1);
 wire have_next=(rgray_n!=wgray_r);
 always @(posedge rclk or negedge rrst_n)
  if(!rrst_n)begin
   rbin<=0;rgray<=0;empty<=1;
   for(i=0;i<SYNC;i=i+1)wgray_s[i]<=0;
  end else begin
   wgray_s[0]<=wgray;for(i=1;i<SYNC;i=i+1)wgray_s[i]<=wgray_s[i-1];
   rbin<=rbin_n;rgray<=rgray_n;empty<=!have_next;
  end
 assign rempty=empty;
 assign rcount=g2b(wgray_r)-rbin;
`ifdef S81SH_SRAM_MUT_CURRENT
 wire [3:0] ra={{(4-AW){1'b0}},rbin[AW-1:0]};
`else
 wire [3:0] ra={{(4-AW){1'b0}},rbin_n[AW-1:0]};
`endif
`ifdef S81SH_SRAM_MUT_EMPTYREAD
 wire re=rrst_n;
`else
 wire re=rrst_n&&have_next;
`endif
 wire we=wrst_n&&push;
 wire [3:0] wa={{(4-AW){1'b0}},wbin[AW-1:0]};
 wire [545:0] q;
 ot_sram_1r1w2c_16x546_m1 u_mem(.wclk(wclk),.rclk(rclk),.r_ce_in(re),.r_addr_in(ra),.rd_out(q),
  .w_ce_in(we),.w_addr_in(wa),.wd_in({{(546-W){1'b0}},wdata}),.w_mask_in({546{1'b1}}));
 assign rdata=q[W-1:0];
`ifndef SYNTHESIS
 always @(posedge wclk or posedge rclk)
  if(wrst_n&&rrst_n&&we&&re&&wa==ra)$fatal(1,"SH_SRAM_FIFO_COLLISION addr%0d",ra);
`endif
endmodule
