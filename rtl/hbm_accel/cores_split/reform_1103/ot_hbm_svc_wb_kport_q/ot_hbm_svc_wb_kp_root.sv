`default_nettype none
// DIE-HBM-62/KPORT 2026-11-03: RE-FORM of ot_hbm_svc_wb_kport_q (hard core, OWNER conservative form).  One payload root of
// the quadrant write-back block: 8 of the 32 payload lanes (SRAM + W286x4 CDC FIFO), one master, four replicas per
// quadrant (root id = strap_bsel, tied at the parent).  Fill side and copy side as ot_hbm_svc_wb_cutthrough_cdc g_root,
// with the copy control coming registered from the hub.
//  FILL: runs from the fill_start / wd pins directly (the hub repeats the checks and faults; a sector is never eligible for
//        copy before the hub's committed watermark, which lags this write by at least the seam).
//  COPY: c_active/c_bank/c_base/c_committed/c_fault arrive as one frame from the hub; c_active low clears the lane rows.
//  K SIDE: hbm-clock head of each lane -> one of 4 ports; port j carries only PCs with pc[1:0]==j, lowest lane first, and
//        sends on credit (port_credit: one pulse per sector the hub popped, DEPTH = hub port FIFO depth).
// MUT (bench only): 1 credit counter starts one too high (hub port FIFO must overflow -> sector lost, bench FAIL),
//                   2 lane sector ignores the root id.
module ot_hbm_svc_wb_kp_root #(parameter integer DEPTH=4, parameter integer MUT=0)(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire [1:0] strap_bsel,
 // fill side (stream_clk, pins)
 input wire wb_fill_start,wb_fill_bank,
 input wire [2047:0] wd_data,input wire [7:0] wd_v,
 // copy frame from the hub (stream_clk)
 input wire c_active,c_bank,c_fault,input wire [29:0] c_base,input wire [11:0] c_committed,
 output wire root_ready,
 // K side to the hub (hbm_clk)
 output reg [3:0] port_v,output wire [7:0] port_pc,output wire [29:0] port_addr0,port_addr1,port_addr2,port_addr3,
 output wire [255:0] port_data0,port_data1,port_data2,port_data3,
 input wire [3:0] port_credit
);
 wire reset_both=stream_rst_n&&hbm_rst_n;
 wire srst,hrst;
 ot_reset_sync u_stream_reset(.clk(stream_clk),.async_rst_n(reset_both),.sync_rst_n(srst));
 ot_reset_sync u_hbm_reset(.clk(hbm_clk),.async_rst_n(reset_both),.sync_rst_n(hrst));
 assign root_ready=srst;
 reg filling,fill_bank;reg [10:0] ordinal;
 always @(posedge stream_clk or negedge srst)
  if(!srst)begin filling<=0;fill_bank<=0;ordinal<=0;end
  else if(wb_fill_start)begin filling<=1;fill_bank<=wb_fill_bank;ordinal<=0;end
  else if(filling&&(|wd_v))ordinal<=ordinal+11'd8;
 wire [7:0] fifo_full,fifo_empty,fifo_re;reg [7:0] fifo_pop;
 wire [285:0] fifo_head[0:7];wire [255:0] mem_data[0:7];
 reg [6:0] copy_row[0:7];reg [5:0] pending_row[0:7];reg [7:0] read_pending;
 wire [7:0] fifo_we,mem_read;
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_lane
  wire [4:0] lane=(MUT==2)?5'(g):{strap_bsel,3'(g)};
  wire [6:0] row=copy_row[g];
  wire [29:0] sector=c_base+{18'b0,pending_row[g],5'b0}+30'(lane);
  wire [11:0] row_ord={row[6:0],5'b0}+12'(lane);
  assign fifo_we[g]=c_active&&read_pending[g]&&!fifo_full[g]&&!c_fault;
  assign mem_read[g]=c_active&&(!read_pending[g]||fifo_we[g])&&row_ord<c_committed&&!c_fault;
  ot_hbm_accel_cdc_fifo #(.W(286),.AW(2)) u_fifo(
   .wclk(stream_clk),.wrst_n(srst),.we(fifo_we[g]),.wdata({sector,mem_data[g]}),.full(fifo_full[g]),.rd_freed(),
   .rclk(hbm_clk),.rrst_n(hrst),.re(fifo_re[g]),.rdata(fifo_head[g]),.empty(fifo_empty[g]));
  ot_sram_1r1w_128x256_m1_r2c2 u_payload(
   .clk(stream_clk),.r_ce_in(mem_read[g]),.r_addr_in({c_bank,row[5:0]}),.rd_out(mem_data[g]),
   .w_ce_in(filling&&wd_v[g]&&ordinal[4:3]==strap_bsel),
   .w_addr_in({fill_bank,ordinal[10:5]}),.wd_in(wd_data[256*g+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 integer s;
 always @(posedge stream_clk or negedge srst)
  if(!srst)begin read_pending<=0;for(s=0;s<8;s=s+1)begin copy_row[s]<=0;pending_row[s]<=0;end end
  else if(!c_active)begin read_pending<=0;for(s=0;s<8;s=s+1)begin copy_row[s]<=0;pending_row[s]<=0;end end
  else for(s=0;s<8;s=s+1)begin
   if(fifo_we[s])read_pending[s]<=0;
   if(mem_read[s])begin read_pending[s]<=1;pending_row[s]<=copy_row[s][5:0];copy_row[s]<=copy_row[s]+1'b1;end
  end
 // ---------------------------------------------------------------- K side: lanes -> 4 ports on credit
 function automatic [3:0] sector_pc(input [29:0] a);sector_pc=a[5:2]^a[9:6]^a[14:11];endfunction
 reg [2:0] credit[0:3];reg [2:0] pick[0:3];
 integer j,l;
 always @*begin
  port_v=0;fifo_pop=0;
  for(j=0;j<4;j=j+1)begin
   pick[j]=0;
   for(l=7;l>=0;l=l-1)if(!fifo_empty[l]&&sector_pc(fifo_head[l][285:256])%4==j)begin
    pick[j]=3'(l);
    if(credit[j]!=0)port_v[j]=1;
   end
   if(port_v[j])fifo_pop[pick[j]]=1;
  end
 end
 assign fifo_re=fifo_pop;
 wire [285:0] h0=fifo_head[pick[0]],h1=fifo_head[pick[1]],h2=fifo_head[pick[2]],h3=fifo_head[pick[3]];
 assign port_addr0=h0[285:256];assign port_data0=h0[255:0];
 assign port_addr1=h1[285:256];assign port_data1=h1[255:0];
 assign port_addr2=h2[285:256];assign port_data2=h2[255:0];
 assign port_addr3=h3[285:256];assign port_data3=h3[255:0];
 wire [3:0] pc0=sector_pc(h0[285:256]),pc1=sector_pc(h1[285:256]),pc2=sector_pc(h2[285:256]),pc3=sector_pc(h3[285:256]);
 assign port_pc={pc3[3:2],pc2[3:2],pc1[3:2],pc0[3:2]};
 integer c;
 always @(posedge hbm_clk or negedge hrst)
  if(!hrst)for(c=0;c<4;c=c+1)credit[c]<=(MUT==1)?3'(DEPTH+1):3'(DEPTH);
  else for(c=0;c<4;c=c+1)
   case({port_v[c],port_credit[c]})
    2'b10:credit[c]<=credit[c]-3'd1;
    2'b01:credit[c]<=credit[c]+3'd1;
    default:begin end
   endcase
endmodule
`default_nettype wire
