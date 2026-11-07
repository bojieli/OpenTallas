`timescale 1ns/1ps
`default_nettype none
// HBM-CONS-2/KSH 2026-11-06 (COORD RULINGS 22:01 (5)): safe forms of ot_hbm_svc_vm_kshare_splitstrap for view __v8e478a.
// Same logic as ot_hbm_svc_vm_kshare_splitstrap (the master keeps its design comment), restructured as one control block plus
// one module per lane so the same RTL builds as ONE tile (..._f1, same pin list) or as TWO tiles (ot_hbm_svc_vmks_t0 / _t1).
// Changes against the master:
//   PTR_SKID   ot_hbm_svc_pin_skid2_ptr: pointer slices per 64 data bits (enable and select fanout <=64, no data movement),
//              same ports and edges as ot_hbm_svc_pin_skid2 (form of HBM-REFORM-B9).
//   FILL_STAGE one register before the VM CDC FIFO write (form kshare4c of DIE-HBM-66, COORD 11-04 15:36): PIN CYCLES fill_* +1.
//   WCNT_STAGE one more stream stage in the WB lane count (sm_s -> wq3 was the worst path of kshare_v8 i3): PIN CYCLES wbw_* +1.
//   GUARD      two-tile form only: all_norm is blind for GUARD hbm edges after a take, because the far lanes' norm comes back
//              over a registered seam (face flops, +1 out +1 in).  Far lanes start a window +2 hbm edges after the near lanes.
// Added bench mutants (the master's MUT 1..8 keep their meaning):
//   MUT 9  fill stage overwrites a stalled entry; MUT 10 skid overwrites a stalled head; MUT 11 wrong tail count in the WB lane count;
//   MUT 12 no seam guard (t0 only); MUT 13 far lanes get the window command one edge late (bench seam, tb only).
module ot_hbm_svc_pin_skid2_ptr #(parameter integer WIDTH=1,MUT=0,SL=64)(
 input wire clk,rst_n,input wire in_v,output wire in_r,
 input wire [WIDTH-1:0]in_data,output wire out_v,input wire out_r,
 output wire [WIDTH-1:0]out_data
);
 localparam integer NS=(WIDTH+SL-1)/SL;
 reg [1:0]cnt;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)cnt<=2'd0;
  else cnt<=cnt+{1'b0,in_v&&cnt!=2'd2}-{1'b0,cnt!=2'd0&&out_r};
 assign in_r=cnt!=2'd2;assign out_v=cnt!=2'd0;
 genvar s;
 generate for(s=0;s<NS;s=s+1)begin:g_sl
  localparam integer LO=s*SL;
  localparam integer W=(LO+SL>WIDTH)?(WIDTH-LO):SL;
  (* keep *) reg [1:0]cnt_k;(* keep *) reg wp_k,rp_k;
  reg [W-1:0]e0,e1;
  wire push=in_v&&cnt_k!=2'd2,pop=cnt_k!=2'd0&&out_r;
  assign out_data[LO+:W]=rp_k?e1:e0;
  always @(posedge clk or negedge rst_n)
   if(!rst_n)begin cnt_k<=2'd0;wp_k<=1'b0;rp_k<=1'b0;end
   else begin
    cnt_k<=cnt_k+{1'b0,push}-{1'b0,pop};
    if(push)wp_k<=!wp_k;
    if(pop)rp_k<=!rp_k;
   end
  always @(posedge clk)begin
   if(push&&!wp_k)e0<=in_data[LO+:W];
   if(push&&wp_k)e1<=in_data[LO+:W];
   if(MUT!=0&&push&&cnt_k!=2'd0&&!out_r)begin if(rp_k)e1<=in_data[LO+:W];else e0<=in_data[LO+:W];end
  end
 end endgenerate
endmodule

// One K-port lane: request skids, window FSM, response skids, VM CDC FIFO, stream-side fill flops.
module ot_hbm_svc_vmks_lane #(parameter integer LANE=0,MUT=0,KRL1=1,PTR_SKID=1,FILL_STAGE=1)(
 input wire hbm_clk,stream_clk,hrst_q,srst_q,input wire[2:0]sm_h,
 input wire take_cmd,take_wb,input wire[35:0]cmd_q,input wire[7:0]wn,input wire[29:0]wc_base,input wire[30:0]wend_q,
 input wire g_k_v,output wire g_k_rdy,input wire[29:0]g_k_addr,input wire[3:0]g_k_len,input wire[16:0]g_k_tag,
 input wire g_k_we,input wire[255:0]g_k_wdata,input wire[31:0]g_k_wstrb,output reg g_k_wr_done,
 output wire g_kr_v,input wire g_kr_rdy,output wire[16:0]g_kr_tag,output wire[3:0]g_kr_beat,output wire[255:0]g_kr_data,
 output wire c_k_v,input wire c_k_rdy,output wire[29:0]c_k_addr,output wire[3:0]c_k_len,output wire[16:0]c_k_tag,
 output wire c_k_we,output wire[255:0]c_k_wdata,output wire[31:0]c_k_wstrb,input wire c_k_wr_done,
 input wire c_kr_v,output wire c_kr_rdy,input wire[16:0]c_kr_tag,input wire[3:0]c_kr_beat,input wire[255:0]c_kr_data,
 input wire w_k_v,output wire w_k_rdy,input wire[29:0]w_k_addr,input wire[255:0]w_k_wdata,output reg w_k_wr_done,
 output reg fill_v,fill_bank,output reg[5:0]fill_slot,output reg[15:0]fill_epoch,output reg[255:0]fill_data,
 output wire norm,hfault
);
 localparam integer KW=1+30+4+17+32+256,RW=17+4+256,FW=1+16+6+256;
 localparam[2:0]NORM=0,PEND=1,ISSUE=2,WAIT=3,WPEND=4,WB=5;
 localparam integer SKM=(MUT==10)?1:0;
 wire cm_bank=cmd_q[35];wire[15:0]cm_epoch=cmd_q[34:19];wire[14:0]cm_row=cmd_q[18:4];wire[3:0]cm_col=cmd_q[3:0];
 wire[4:0]P={sm_h,2'(LANE)};
 wire a_v,a_r;wire[KW-1:0]a_d;
 wire e_v,e_r;wire[285:0]e_d;
 wire b_in_v,b_in_r,b_v;wire[KW-1:0]b_in_d,b_d;
 wire c_v,c_r;wire[RW-1:0]c_d;
 wire d_r;
 wire[KW-1:0]a_in={g_k_we,g_k_addr,g_k_len,g_k_tag,g_k_wstrb,g_k_wdata};
 wire[RW-1:0]d_out;
 assign {g_kr_tag,g_kr_beat,g_kr_data}=d_out;
 wire vm_phase;
 generate if(PTR_SKID!=0)begin:g_ptr
  ot_hbm_svc_pin_skid2_ptr #(.WIDTH(KW),.MUT(SKM)) u_a(.clk(hbm_clk),.rst_n(hrst_q),.in_v(g_k_v),.in_r(g_k_rdy),.in_data(a_in),.out_v(a_v),.out_r(a_r),.out_data(a_d));
  ot_hbm_svc_pin_skid2_ptr #(.WIDTH(286)) u_e(.clk(hbm_clk),.rst_n(hrst_q),.in_v(w_k_v),.in_r(w_k_rdy),.in_data({w_k_addr,w_k_wdata}),.out_v(e_v),.out_r(e_r),.out_data(e_d));
  ot_hbm_svc_pin_skid2_ptr #(.WIDTH(KW)) u_b(.clk(hbm_clk),.rst_n(hrst_q),.in_v(b_in_v),.in_r(b_in_r),.in_data(b_in_d),.out_v(b_v),.out_r(c_k_rdy),.out_data(b_d));
  ot_hbm_svc_pin_skid2_ptr #(.WIDTH(RW)) u_d(.clk(hbm_clk),.rst_n(hrst_q),.in_v(c_v&&!vm_phase),.in_r(d_r),.in_data(c_d),.out_v(g_kr_v),.out_r(g_kr_rdy),.out_data(d_out));
 end else begin:g_plain
  ot_hbm_svc_pin_skid2 #(.WIDTH(KW)) u_a(.clk(hbm_clk),.rst_n(hrst_q),.in_v(g_k_v),.in_r(g_k_rdy),.in_data(a_in),.out_v(a_v),.out_r(a_r),.out_data(a_d));
  ot_hbm_svc_pin_skid2 #(.WIDTH(286)) u_e(.clk(hbm_clk),.rst_n(hrst_q),.in_v(w_k_v),.in_r(w_k_rdy),.in_data({w_k_addr,w_k_wdata}),.out_v(e_v),.out_r(e_r),.out_data(e_d));
  ot_hbm_svc_pin_skid2 #(.WIDTH(KW)) u_b(.clk(hbm_clk),.rst_n(hrst_q),.in_v(b_in_v),.in_r(b_in_r),.in_data(b_in_d),.out_v(b_v),.out_r(c_k_rdy),.out_data(b_d));
  ot_hbm_svc_pin_skid2 #(.WIDTH(RW)) u_d(.clk(hbm_clk),.rst_n(hrst_q),.in_v(c_v&&!vm_phase),.in_r(d_r),.in_data(c_d),.out_v(g_kr_v),.out_r(g_kr_rdy),.out_data(d_out));
 end endgenerate
 reg[2:0]st;reg[3:0]j;reg[6:0]got;reg[7:0]g_rd_out;reg[5:0]g_wr_out;reg hf;reg[7:0]wsent,wdone;
 wire wb_st=st==WB;
 wire w_more=wb_st&&wsent!=wn;
 wire[29:0]e_a=e_d[285:256];
 wire[29:0]w_addr=(MUT==4)?(e_a^30'h4):e_a;
 wire e_bad=(e_a[6:2]^e_a[11:7]^e_a[16:12])!=P||e_a<wc_base||{1'b0,e_a}>=wend_q;
 wire[4:0]bhi5={cm_row[1:0],j[2:0]};wire[4:0]col={cm_col,j[3]};
 wire[4:0]pcf=(MUT==2)?(col^bhi5):(P^col^bhi5);
 wire[29:0]vm_addr={cm_row,j[2:0],col,pcf,2'b00};
 wire[16:0]vm_tag={cm_bank,cm_epoch[11:0],j};
 wire vm_req=st==ISSUE;
 assign b_in_v=vm_req?1'b1:wb_st?(e_v&&w_more):(st==NORM&&a_v);
 assign b_in_d=vm_req?{1'b0,vm_addr,4'd4,vm_tag,32'd0,256'd0}:
               wb_st?{1'b1,w_addr,4'd1,{1'b1,8'd0,wsent},32'hffffffff,e_d[255:0]}:a_d;
 assign e_r=w_more&&b_in_r;
 wire w_push=wb_st&&b_in_v&&b_in_r;
 assign a_r=st==NORM&&b_in_r;
 assign c_k_v=b_v;
 assign {c_k_we,c_k_addr,c_k_len,c_k_tag,c_k_wstrb,c_k_wdata}=b_d;
 wire b_pop=b_v&&c_k_rdy;
 wire b_pop_grp=b_pop&&!(st==ISSUE||st==WAIT||st==WB);
 wire c_ring_fault;
 generate if(KRL1!=0)begin:g_c_rl1
  reg c_rdy_q,c_rdy_seen;wire[2:0]c_cnt,c_cnt_next;
  ot_hbm_svc_ring_h9b_ff #(.WIDTH(RW),.DEPTH((MUT==6)?2:3)) u_c(.clk(hbm_clk),.rst_n(hrst_q),.in_v(c_kr_v&&c_rdy_seen),
   .in_data({c_kr_tag,c_kr_beat,c_kr_data}),.out_v(c_v),.pop(c_v&&c_r),.out_data(c_d),
   .cnt(c_cnt),.cnt_next(c_cnt_next),.fault(c_ring_fault));
  always @(posedge hbm_clk)
   if(!hrst_q)begin c_rdy_q<=1'b0;c_rdy_seen<=1'b0;end
   else begin c_rdy_q<=c_cnt_next<=3'd1;c_rdy_seen<=c_rdy_q;end
  assign c_kr_rdy=c_rdy_q;
 end else begin:g_c_rl0
  assign c_ring_fault=1'b0;
  ot_hbm_svc_pin_skid2 #(.WIDTH(RW)) u_c(.clk(hbm_clk),.rst_n(hrst_q),.in_v(c_kr_v),.in_r(c_kr_rdy),
   .in_data({c_kr_tag,c_kr_beat,c_kr_data}),.out_v(c_v),.out_r(c_r),.out_data(c_d));
 end endgenerate
 assign vm_phase=(st==ISSUE||st==WAIT)^(MUT==1&&st==PEND);
 wire f_r,fs_in_r;
 assign c_r=vm_phase?fs_in_r:d_r;
 wire c_pop_grp=c_v&&!vm_phase&&d_r;
 wire c_pop_vm=c_v&&vm_phase&&fs_in_r;
 wire[16:0]rt=c_d[RW-1-:17];wire[3:0]rb=c_d[259:256];
 wire tag_ok=rt=={cm_bank,cm_epoch[11:0],rt[3:0]}&&rb<4;
 wire[FW-1:0]f_d={cm_bank,cm_epoch,rt[3:0],rb[1:0],c_d[255:0]};
 wire f_ov,f_un,rf_valid;wire[FW-1:0]rf_data;wire f_wv;wire[FW-1:0]f_wd;
 generate if(FILL_STAGE!=0)begin:g_fs
  // one register ahead of the FIFO write, never valid into a full FIFO
  reg fs_v;reg[FW-1:0]fs_d;
  assign fs_in_r=!fs_v||f_r;
  always @(posedge hbm_clk or negedge hrst_q)if(!hrst_q)fs_v<=1'b0;else if(fs_in_r)fs_v<=c_pop_vm;
  always @(posedge hbm_clk)if(c_pop_vm||(MUT==9&&c_v&&vm_phase))fs_d<=f_d;
  assign f_wv=fs_v&&f_r;assign f_wd=fs_d;
 end else begin:g_nofs
  assign fs_in_r=f_r;assign f_wv=c_pop_vm;assign f_wd=f_d;
 end endgenerate
 ot_hbm_svc_async_fifo #(.WIDTH(FW),.DEPTH(8)) u_fill(
  .wr_clk(hbm_clk),.wr_rst_n(hrst_q),.wr_valid(f_wv),.wr_ready(f_r),.wr_data(f_wd),.wr_overflow(f_ov),
  .rd_clk(stream_clk),.rd_rst_n(srst_q),.rd_valid(rf_valid),.rd_ready(rf_valid),.rd_data(rf_data),.rd_underflow(f_un));
 wire[8:0]rd_beats=b_pop_grp&&!b_d[KW-1]?{5'd0,b_d[KW-1-30-1-:4]}:9'd0;
 wire drained=!b_v&&g_rd_out==0&&g_wr_out==0;
 wire wdrained=!b_v&&(g_wr_out==0||MUT==3);
 wire g_done=c_k_wr_done&&!wb_st;
 always @(posedge hbm_clk or negedge hrst_q)begin
  if(!hrst_q)begin st<=NORM;j<=0;got<=0;g_rd_out<=0;g_wr_out<=0;hf<=0;wsent<=0;wdone<=0;end
  else begin
   g_rd_out<=g_rd_out+rd_beats[7:0]-{7'd0,c_pop_grp};
   g_wr_out<=g_wr_out+{5'd0,b_pop_grp&&b_d[KW-1]}-{5'd0,g_done};
   if(g_done&&g_wr_out==0)hf<=1;
   if(w_push)begin wsent<=wsent+1'b1;if(e_bad)hf<=1;end
   if(c_k_wr_done&&wb_st)begin wdone<=wdone+1'b1;if(wdone==wsent)hf<=1;end
   if(c_pop_grp&&g_rd_out==0&&!(MUT==1))hf<=1;
   if(c_pop_vm&&!tag_ok)hf<=1;
   case(st)
    NORM:if(take_cmd)begin st<=PEND;j<=0;got<=0;end
         else if(take_wb)begin st<=WPEND;wsent<=0;wdone<=0;end
    PEND:if(drained||MUT==1)st<=ISSUE;
    ISSUE:if(b_in_r)begin j<=j+1'b1;if(j==4'd15)st<=WAIT;end
    WPEND:if(wdrained)st<=WB;
    WB:if(wsent==wn&&wdone==wn)st<=NORM;
    default:;
   endcase
   if(c_pop_vm)begin
    got<=got+1'b1;
    if(got==7'd63)st<=NORM;
   end
  end
 end
 always @(posedge hbm_clk or negedge hrst_q)
  if(!hrst_q)begin g_k_wr_done<=0;w_k_wr_done<=0;end
  else begin g_k_wr_done<=g_done;w_k_wr_done<=c_k_wr_done&&wb_st;end
 assign norm=st==NORM;assign hfault=hf||f_ov||c_ring_fault;
 always @(posedge stream_clk or negedge srst_q)if(!srst_q)fill_v<=0;else fill_v<=rf_valid;
 always @(posedge stream_clk){fill_bank,fill_epoch,fill_slot,fill_data}<=rf_data;
endmodule

// Stream-side command capture, WB lane counts, both command CDC FIFOs, window take, fault collection.
module ot_hbm_svc_vmks_ctl #(parameter integer MUT=0,WCNT_STAGE=1,GUARD=0)(
 input wire hbm_clk,stream_clk,hrst_q,srst_q,input wire[2:0]sm_s,
 input wire vm_v,vm_bank,input wire[15:0]vm_epoch,input wire[14:0]vm_row,input wire[3:0]vm_col,
 input wire wbw_v,input wire[29:0]wbw_base,input wire[11:0]wbw_total,
 input wire lanes_norm,input wire lanes_fault,
 output wire take_cmd,take_wb,output reg[35:0]cmd_q,output wire[31:0]wn,output wire[29:0]wc_base,output reg[30:0]wend_q,
 output reg fault
);
 localparam integer CMW=36,WQW=74;
 reg cv_q;reg[CMW-1:0]cd_q;
 always @(posedge stream_clk)cd_q<={vm_bank,vm_epoch,vm_row,vm_col};
 always @(posedge stream_clk or negedge srst_q)if(!srst_q)cv_q<=0;else cv_q<=vm_v;
 wire cf_wr_ready,cf_ov,cf_rd_valid,cf_un;wire[CMW-1:0]cf_rd_data;
 wire go;
 assign take_cmd=cf_rd_valid&&go;
 ot_hbm_svc_async_fifo #(.WIDTH(CMW),.DEPTH(4)) u_cmd(
  .wr_clk(stream_clk),.wr_rst_n(srst_q),.wr_valid(cv_q),.wr_ready(cf_wr_ready),.wr_data(cd_q),.wr_overflow(cf_ov),
  .rd_clk(hbm_clk),.rd_rst_n(hrst_q),.rd_valid(cf_rd_valid),.rd_ready(take_cmd),.rd_data(cf_rd_data),.rd_underflow(cf_un));
 always @(posedge hbm_clk)if(take_cmd)cmd_q<=cf_rd_data;
 function automatic [2:0] ov(input [4:0] g,input [7:0] lo,input [7:0] hi);   // |[4g,4g+4) intersect [lo,hi)|
  reg[7:0]a,z;begin a=({1'b0,g,2'b00}>lo)?{1'b0,g,2'b00}:lo;z=({1'b0,g,2'b00}+8'd4<hi)?{1'b0,g,2'b00}+8'd4:hi;ov=(z>a)?3'(z-a):3'd0;end
 endfunction
 reg wv1,wv2,wv3;reg[29:0]wb1,wb2;reg[11:0]wt1,wt2;reg[29:0]we2;
 always @(posedge stream_clk)begin wb1<=wbw_base;wt1<=wbw_total;wb2<=wb1;wt2<=wt1;we2<=wb1+30'(wt1)-30'd1;end
 always @(posedge stream_clk or negedge srst_q)if(!srst_q)begin wv1<=0;wv2<=0;wv3<=0;end else begin wv1<=wbw_v;wv2<=wv1;wv3<=wv2;end
 // lane counts: head + tail + 4 per whole chunk, as wcnt of the master, split over two stages (per-lane overlaps | sum)
 wire[6:0]wb_d7=we2[13:7]-wb2[13:7]-7'd1;
 wire[8:0]mid9={wb_d7,2'b00};
 wire d_zero=we2[29:7]==wb2[29:7];
 wire t_zero=wt2==0;
 wire[4:0]bg=wb2[11:7]^wb2[16:12];wire[4:0]eg=we2[11:7]^we2[16:12];
 wire[7:0]ehi={1'b0,we2[6:0]}+8'd1;
 wire wf_wr_ready,wf_ov,wf_rd_valid,wf_un;wire[WQW-1:0]wf_rd_data;
 wire wq_v;wire[WQW-1:0]wq;
 integer ll;
 reg[2:0]ovh[0:3],ovt[0:3];
 always @*begin
  for(ll=0;ll<4;ll=ll+1)begin
   ovh[ll]=d_zero?ov(({sm_s,2'(ll)})^bg,{1'b0,wb2[6:0]},ehi):ov(({sm_s,2'(ll)})^bg,{1'b0,wb2[6:0]},8'd128);
   ovt[ll]=(MUT==11)?ov(({sm_s,2'(ll)})^bg,8'd0,ehi):ov(({sm_s,2'(ll)})^eg,8'd0,ehi);
  end
 end
 function automatic [7:0] csum(input t0,input dz,input [2:0] h,input [2:0] tl,input [8:0] m);
  reg[8:0]n;begin if(t0)n=0;else if(dz)n=9'(h);else n=9'(h)+9'(tl)+m;csum=n[7:0];end
 endfunction
 generate if(WCNT_STAGE!=0)begin:g_w2
  reg wv4;reg[29:0]a_b;reg[11:0]a_t;reg[8:0]a_m;reg a_dz,a_tz;reg[11:0]a_ovh,a_ovt;reg[WQW-1:0]wq4;
  always @(posedge stream_clk)begin
   a_b<=wb2;a_t<=wt2;a_m<=mid9;a_dz<=d_zero;a_tz<=t_zero;
   a_ovh<={ovh[3],ovh[2],ovh[1],ovh[0]};a_ovt<={ovt[3],ovt[2],ovt[1],ovt[0]};
   wq4<={a_b,a_t,csum(a_tz,a_dz,a_ovh[11:9],a_ovt[11:9],a_m),csum(a_tz,a_dz,a_ovh[8:6],a_ovt[8:6],a_m),
         csum(a_tz,a_dz,a_ovh[5:3],a_ovt[5:3],a_m),csum(a_tz,a_dz,a_ovh[2:0],a_ovt[2:0],a_m)};
  end
  always @(posedge stream_clk or negedge srst_q)if(!srst_q)wv4<=0;else wv4<=wv3;
  assign wq_v=wv4;assign wq=wq4;
 end else begin:g_w1
  reg[WQW-1:0]wq3;
  always @(posedge stream_clk)wq3<={wb2,wt2,csum(t_zero,d_zero,ovh[3],ovt[3],mid9),csum(t_zero,d_zero,ovh[2],ovt[2],mid9),
                                    csum(t_zero,d_zero,ovh[1],ovt[1],mid9),csum(t_zero,d_zero,ovh[0],ovt[0],mid9)};
  assign wq_v=wv3;assign wq=wq3;
 end endgenerate
 assign take_wb=wf_rd_valid&&go&&!cf_rd_valid;
 ot_hbm_svc_async_fifo #(.WIDTH(WQW),.DEPTH(4)) u_wcmd(
  .wr_clk(stream_clk),.wr_rst_n(srst_q),.wr_valid(wq_v),.wr_ready(wf_wr_ready),.wr_data(wq),.wr_overflow(wf_ov),
  .rd_clk(hbm_clk),.rd_rst_n(hrst_q),.rd_valid(wf_rd_valid),.rd_ready(take_wb),.rd_data(wf_rd_data),.rd_underflow(wf_un));
 reg[WQW-1:0]wcmd_q;
 always @(posedge hbm_clk)if(take_wb)begin wcmd_q<=wf_rd_data;wend_q<={1'b0,wf_rd_data[WQW-1-:30]}+31'(wf_rd_data[43:32]);end
 assign wc_base=wcmd_q[WQW-1-:30];assign wn=wcmd_q[31:0];
 // seam guard: GUARD=0 is the single-tile form
 generate if(GUARD!=0&&MUT!=12)begin:g_guard
  reg[2:0]gc;
  always @(posedge hbm_clk or negedge hrst_q)if(!hrst_q)gc<=0;else if(take_cmd||take_wb)gc<=3'(GUARD);else if(gc!=0)gc<=gc-3'd1;
  assign go=lanes_norm&&gc==0;
 end else begin:g_noguard
  assign go=lanes_norm;
 end endgenerate
 wire hfault_stream;reg sbad;
 ot_hbm_svc_fault_cdc u_fault_cdc(.wr_clk(hbm_clk),.wr_rst_n(hrst_q),
  .rd_clk(stream_clk),.rd_rst_n(srst_q),.src_fault(lanes_fault||cf_un||wf_un),
  .dst_fault(hfault_stream),.wr_overflow(),.rd_underflow());
 always @(posedge stream_clk or negedge srst_q)begin
  if(!srst_q)begin sbad<=0;fault<=0;end
  else begin
   if(cv_q&&!cf_wr_ready)sbad<=1;
   if(wq_v&&!wf_wr_ready)sbad<=1;
   fault<=sbad||hfault_stream||cf_ov||wf_ov;
  end
 end
endmodule

// ONE TILE: same pin list as ot_hbm_svc_vm_kshare_splitstrap.
module ot_hbm_svc_vm_kshare_splitstrap_f1 #(parameter integer MUT=0,KRL1=1,PTR_SKID=1,FILL_STAGE=1,WCNT_STAGE=1) (
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire[2:0]sm_stream,sm_hbm,
 input wire[3:0]g_k_v,output wire[3:0]g_k_rdy,input wire[119:0]g_k_addr,input wire[15:0]g_k_len,input wire[67:0]g_k_tag,
 input wire[3:0]g_k_we,input wire[1023:0]g_k_wdata,input wire[127:0]g_k_wstrb,output wire[3:0]g_k_wr_done,
 output wire[3:0]g_kr_v,input wire[3:0]g_kr_rdy,output wire[67:0]g_kr_tag,output wire[15:0]g_kr_beat,output wire[1023:0]g_kr_data,
 output wire[3:0]c_k_v,input wire[3:0]c_k_rdy,output wire[119:0]c_k_addr,output wire[15:0]c_k_len,output wire[67:0]c_k_tag,
 output wire[3:0]c_k_we,output wire[1023:0]c_k_wdata,output wire[127:0]c_k_wstrb,input wire[3:0]c_k_wr_done,
 input wire[3:0]c_kr_v,output wire[3:0]c_kr_rdy,input wire[67:0]c_kr_tag,input wire[15:0]c_kr_beat,input wire[1023:0]c_kr_data,
 input wire vm_v,vm_bank,input wire[15:0]vm_epoch,input wire[14:0]vm_row,input wire[3:0]vm_col,
 input wire wbw_v,input wire[29:0]wbw_base,input wire[11:0]wbw_total,
 input wire[3:0]w_k_v,output wire[3:0]w_k_rdy,input wire[119:0]w_k_addr,input wire[1023:0]w_k_wdata,output wire[3:0]w_k_wr_done,
 output wire[3:0]fill_v,output wire[3:0]fill_bank,output wire[23:0]fill_slot,output wire[63:0]fill_epoch,output wire[1023:0]fill_data,
 output wire fault
);
 reg srst_q,hrst_q;
 always @(posedge stream_clk or negedge stream_rst_n)if(!stream_rst_n)srst_q<=1'b0;else srst_q<=1'b1;
 always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)hrst_q<=1'b0;else hrst_q<=1'b1;
 reg[2:0]sm_s,sm_h;
 always @(posedge stream_clk)sm_s<=((MUT==5)||(MUT==8))?3'd0:sm_stream;
 always @(posedge hbm_clk)sm_h<=((MUT==5)||(MUT==7))?3'd0:sm_hbm;
 wire take_cmd,take_wb;wire[35:0]cmd_q;wire[31:0]wn;wire[29:0]wc_base;wire[30:0]wend_q;wire[3:0]norm_l,hfault_l;
 ot_hbm_svc_vmks_ctl #(.MUT(MUT),.WCNT_STAGE(WCNT_STAGE)) u_ctl(.hbm_clk(hbm_clk),.stream_clk(stream_clk),.hrst_q(hrst_q),.srst_q(srst_q),.sm_s(sm_s),
  .vm_v(vm_v),.vm_bank(vm_bank),.vm_epoch(vm_epoch),.vm_row(vm_row),.vm_col(vm_col),.wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),
  .lanes_norm(&norm_l),.lanes_fault(|hfault_l),.take_cmd(take_cmd),.take_wb(take_wb),.cmd_q(cmd_q),.wn(wn),.wc_base(wc_base),.wend_q(wend_q),.fault(fault));
 genvar l;
 generate for(l=0;l<4;l=l+1)begin:lane
  ot_hbm_svc_vmks_lane #(.LANE(l),.MUT(MUT),.KRL1(KRL1),.PTR_SKID(PTR_SKID),.FILL_STAGE(FILL_STAGE)) u_l(.hbm_clk(hbm_clk),.stream_clk(stream_clk),.hrst_q(hrst_q),.srst_q(srst_q),.sm_h(sm_h),
   .take_cmd(take_cmd),.take_wb(take_wb),.cmd_q(cmd_q),.wn(wn[8*l+:8]),.wc_base(wc_base),.wend_q(wend_q),
   .g_k_v(g_k_v[l]),.g_k_rdy(g_k_rdy[l]),.g_k_addr(g_k_addr[30*l+:30]),.g_k_len(g_k_len[4*l+:4]),.g_k_tag(g_k_tag[17*l+:17]),
   .g_k_we(g_k_we[l]),.g_k_wdata(g_k_wdata[256*l+:256]),.g_k_wstrb(g_k_wstrb[32*l+:32]),.g_k_wr_done(g_k_wr_done[l]),
   .g_kr_v(g_kr_v[l]),.g_kr_rdy(g_kr_rdy[l]),.g_kr_tag(g_kr_tag[17*l+:17]),.g_kr_beat(g_kr_beat[4*l+:4]),.g_kr_data(g_kr_data[256*l+:256]),
   .c_k_v(c_k_v[l]),.c_k_rdy(c_k_rdy[l]),.c_k_addr(c_k_addr[30*l+:30]),.c_k_len(c_k_len[4*l+:4]),.c_k_tag(c_k_tag[17*l+:17]),
   .c_k_we(c_k_we[l]),.c_k_wdata(c_k_wdata[256*l+:256]),.c_k_wstrb(c_k_wstrb[32*l+:32]),.c_k_wr_done(c_k_wr_done[l]),
   .c_kr_v(c_kr_v[l]),.c_kr_rdy(c_kr_rdy[l]),.c_kr_tag(c_kr_tag[17*l+:17]),.c_kr_beat(c_kr_beat[4*l+:4]),.c_kr_data(c_kr_data[256*l+:256]),
   .w_k_v(w_k_v[l]),.w_k_rdy(w_k_rdy[l]),.w_k_addr(w_k_addr[30*l+:30]),.w_k_wdata(w_k_wdata[256*l+:256]),.w_k_wr_done(w_k_wr_done[l]),
   .fill_v(fill_v[l]),.fill_bank(fill_bank[l]),.fill_slot(fill_slot[6*l+:6]),.fill_epoch(fill_epoch[16*l+:16]),.fill_data(fill_data[256*l+:256]),
   .norm(norm_l[l]),.hfault(hfault_l[l]));
 end endgenerate
endmodule

// TWO TILES.  ot_hbm_svc_vmks_t0 = control + lanes LA,LB; ot_hbm_svc_vmks_t1 = lanes LC,LD.  The seam is control only (window command,
// lane counts, norm, fault); no K or fill data crosses.  Registered by the kit face shells: +1 out, +1 in.
// Each tile lands the reset and strap pins on its own flops (the parent nets reach both tiles).
module ot_hbm_svc_vmks_t0 #(parameter integer MUT=0,KRL1=1,GUARD=4,LA=0,LB=1) (
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire[2:0]sm_stream,sm_hbm,
 input wire[1:0]g_k_v,output wire[1:0]g_k_rdy,input wire[59:0]g_k_addr,input wire[7:0]g_k_len,input wire[33:0]g_k_tag,
 input wire[1:0]g_k_we,input wire[511:0]g_k_wdata,input wire[63:0]g_k_wstrb,output wire[1:0]g_k_wr_done,
 output wire[1:0]g_kr_v,input wire[1:0]g_kr_rdy,output wire[33:0]g_kr_tag,output wire[7:0]g_kr_beat,output wire[511:0]g_kr_data,
 output wire[1:0]c_k_v,input wire[1:0]c_k_rdy,output wire[59:0]c_k_addr,output wire[7:0]c_k_len,output wire[33:0]c_k_tag,
 output wire[1:0]c_k_we,output wire[511:0]c_k_wdata,output wire[63:0]c_k_wstrb,input wire[1:0]c_k_wr_done,
 input wire[1:0]c_kr_v,output wire[1:0]c_kr_rdy,input wire[33:0]c_kr_tag,input wire[7:0]c_kr_beat,input wire[511:0]c_kr_data,
 input wire vm_v,vm_bank,input wire[15:0]vm_epoch,input wire[14:0]vm_row,input wire[3:0]vm_col,
 input wire wbw_v,input wire[29:0]wbw_base,input wire[11:0]wbw_total,
 input wire[1:0]w_k_v,output wire[1:0]w_k_rdy,input wire[59:0]w_k_addr,input wire[511:0]w_k_wdata,output wire[1:0]w_k_wr_done,
 output wire[1:0]fill_v,output wire[1:0]fill_bank,output wire[11:0]fill_slot,output wire[31:0]fill_epoch,output wire[511:0]fill_data,
 output wire fault,
 output wire s_take_cmd,s_take_wb,output wire[35:0]s_cmd,output wire[15:0]s_wn,output wire[29:0]s_wbase,output wire[30:0]s_wend,
 input wire[1:0]s_norm,input wire s_fault
);
 reg srst_q,hrst_q;
 always @(posedge stream_clk or negedge stream_rst_n)if(!stream_rst_n)srst_q<=1'b0;else srst_q<=1'b1;
 always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)hrst_q<=1'b0;else hrst_q<=1'b1;
 reg[2:0]sm_s,sm_h;
 always @(posedge stream_clk)sm_s<=((MUT==5)||(MUT==8))?3'd0:sm_stream;
 always @(posedge hbm_clk)sm_h<=((MUT==5)||(MUT==7))?3'd0:sm_hbm;
 wire[31:0]wn;wire[1:0]norm_l,hfault_l;wire[29:0]wc_base;wire[30:0]wend_q;
 assign s_wbase=wc_base;assign s_wend=wend_q;
 ot_hbm_svc_vmks_ctl #(.MUT(MUT),.GUARD(GUARD)) u_ctl(.hbm_clk(hbm_clk),.stream_clk(stream_clk),.hrst_q(hrst_q),.srst_q(srst_q),.sm_s(sm_s),
  .vm_v(vm_v),.vm_bank(vm_bank),.vm_epoch(vm_epoch),.vm_row(vm_row),.vm_col(vm_col),.wbw_v(wbw_v),.wbw_base(wbw_base),.wbw_total(wbw_total),
  .lanes_norm((&norm_l)&&(&s_norm)),.lanes_fault((|hfault_l)||s_fault),.take_cmd(s_take_cmd),.take_wb(s_take_wb),.cmd_q(s_cmd),.wn(wn),.wc_base(wc_base),.wend_q(wend_q),.fault(fault));
 // lanes not in this tile: their counts leave on the seam, in LC,LD order (ascending)
 localparam integer LC=(LA!=0&&LB!=0)?0:((LA!=1&&LB!=1)?1:2);
 localparam integer LD=(LC==2)?3:((LA!=2&&LB!=2&&LC!=2)?2:3);
 assign s_wn={wn[8*LD+:8],wn[8*LC+:8]};
 genvar i;
 generate for(i=0;i<2;i=i+1)begin:lane
  localparam integer L=(i==0)?LA:LB;
  ot_hbm_svc_vmks_lane #(.LANE(L),.MUT(MUT),.KRL1(KRL1)) u_l(.hbm_clk(hbm_clk),.stream_clk(stream_clk),.hrst_q(hrst_q),.srst_q(srst_q),.sm_h(sm_h),
   .take_cmd(s_take_cmd),.take_wb(s_take_wb),.cmd_q(s_cmd),.wn(wn[8*L+:8]),.wc_base(wc_base),.wend_q(wend_q),
   .g_k_v(g_k_v[i]),.g_k_rdy(g_k_rdy[i]),.g_k_addr(g_k_addr[30*i+:30]),.g_k_len(g_k_len[4*i+:4]),.g_k_tag(g_k_tag[17*i+:17]),
   .g_k_we(g_k_we[i]),.g_k_wdata(g_k_wdata[256*i+:256]),.g_k_wstrb(g_k_wstrb[32*i+:32]),.g_k_wr_done(g_k_wr_done[i]),
   .g_kr_v(g_kr_v[i]),.g_kr_rdy(g_kr_rdy[i]),.g_kr_tag(g_kr_tag[17*i+:17]),.g_kr_beat(g_kr_beat[4*i+:4]),.g_kr_data(g_kr_data[256*i+:256]),
   .c_k_v(c_k_v[i]),.c_k_rdy(c_k_rdy[i]),.c_k_addr(c_k_addr[30*i+:30]),.c_k_len(c_k_len[4*i+:4]),.c_k_tag(c_k_tag[17*i+:17]),
   .c_k_we(c_k_we[i]),.c_k_wdata(c_k_wdata[256*i+:256]),.c_k_wstrb(c_k_wstrb[32*i+:32]),.c_k_wr_done(c_k_wr_done[i]),
   .c_kr_v(c_kr_v[i]),.c_kr_rdy(c_kr_rdy[i]),.c_kr_tag(c_kr_tag[17*i+:17]),.c_kr_beat(c_kr_beat[4*i+:4]),.c_kr_data(c_kr_data[256*i+:256]),
   .w_k_v(w_k_v[i]),.w_k_rdy(w_k_rdy[i]),.w_k_addr(w_k_addr[30*i+:30]),.w_k_wdata(w_k_wdata[256*i+:256]),.w_k_wr_done(w_k_wr_done[i]),
   .fill_v(fill_v[i]),.fill_bank(fill_bank[i]),.fill_slot(fill_slot[6*i+:6]),.fill_epoch(fill_epoch[16*i+:16]),.fill_data(fill_data[256*i+:256]),
   .norm(norm_l[i]),.hfault(hfault_l[i]));
 end endgenerate
endmodule

module ot_hbm_svc_vmks_t1 #(parameter integer MUT=0,KRL1=1,LA=2,LB=3) (
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire[2:0]sm_hbm,
 input wire[1:0]g_k_v,output wire[1:0]g_k_rdy,input wire[59:0]g_k_addr,input wire[7:0]g_k_len,input wire[33:0]g_k_tag,
 input wire[1:0]g_k_we,input wire[511:0]g_k_wdata,input wire[63:0]g_k_wstrb,output wire[1:0]g_k_wr_done,
 output wire[1:0]g_kr_v,input wire[1:0]g_kr_rdy,output wire[33:0]g_kr_tag,output wire[7:0]g_kr_beat,output wire[511:0]g_kr_data,
 output wire[1:0]c_k_v,input wire[1:0]c_k_rdy,output wire[59:0]c_k_addr,output wire[7:0]c_k_len,output wire[33:0]c_k_tag,
 output wire[1:0]c_k_we,output wire[511:0]c_k_wdata,output wire[63:0]c_k_wstrb,input wire[1:0]c_k_wr_done,
 input wire[1:0]c_kr_v,output wire[1:0]c_kr_rdy,input wire[33:0]c_kr_tag,input wire[7:0]c_kr_beat,input wire[511:0]c_kr_data,
 input wire[1:0]w_k_v,output wire[1:0]w_k_rdy,input wire[59:0]w_k_addr,input wire[511:0]w_k_wdata,output wire[1:0]w_k_wr_done,
 output wire[1:0]fill_v,output wire[1:0]fill_bank,output wire[11:0]fill_slot,output wire[31:0]fill_epoch,output wire[511:0]fill_data,
 input wire s_take_cmd,s_take_wb,input wire[35:0]s_cmd,input wire[15:0]s_wn,input wire[29:0]s_wbase,input wire[30:0]s_wend,
 output wire[1:0]s_norm,output wire s_fault
);
 reg srst_q,hrst_q;
 always @(posedge stream_clk or negedge stream_rst_n)if(!stream_rst_n)srst_q<=1'b0;else srst_q<=1'b1;
 always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)hrst_q<=1'b0;else hrst_q<=1'b1;
 reg[2:0]sm_h;
 always @(posedge hbm_clk)sm_h<=((MUT==5)||(MUT==7))?3'd0:sm_hbm;
 wire[1:0]hfault_l;
 assign s_fault=|hfault_l;
 genvar i;
 generate for(i=0;i<2;i=i+1)begin:lane
  localparam integer L=(i==0)?LA:LB;
  ot_hbm_svc_vmks_lane #(.LANE(L),.MUT(MUT),.KRL1(KRL1)) u_l(.hbm_clk(hbm_clk),.stream_clk(stream_clk),.hrst_q(hrst_q),.srst_q(srst_q),.sm_h(sm_h),
   .take_cmd(s_take_cmd),.take_wb(s_take_wb),.cmd_q(s_cmd),.wn(s_wn[8*i+:8]),.wc_base(s_wbase),.wend_q(s_wend),
   .g_k_v(g_k_v[i]),.g_k_rdy(g_k_rdy[i]),.g_k_addr(g_k_addr[30*i+:30]),.g_k_len(g_k_len[4*i+:4]),.g_k_tag(g_k_tag[17*i+:17]),
   .g_k_we(g_k_we[i]),.g_k_wdata(g_k_wdata[256*i+:256]),.g_k_wstrb(g_k_wstrb[32*i+:32]),.g_k_wr_done(g_k_wr_done[i]),
   .g_kr_v(g_kr_v[i]),.g_kr_rdy(g_kr_rdy[i]),.g_kr_tag(g_kr_tag[17*i+:17]),.g_kr_beat(g_kr_beat[4*i+:4]),.g_kr_data(g_kr_data[256*i+:256]),
   .c_k_v(c_k_v[i]),.c_k_rdy(c_k_rdy[i]),.c_k_addr(c_k_addr[30*i+:30]),.c_k_len(c_k_len[4*i+:4]),.c_k_tag(c_k_tag[17*i+:17]),
   .c_k_we(c_k_we[i]),.c_k_wdata(c_k_wdata[256*i+:256]),.c_k_wstrb(c_k_wstrb[32*i+:32]),.c_k_wr_done(c_k_wr_done[i]),
   .c_kr_v(c_kr_v[i]),.c_kr_rdy(c_kr_rdy[i]),.c_kr_tag(c_kr_tag[17*i+:17]),.c_kr_beat(c_kr_beat[4*i+:4]),.c_kr_data(c_kr_data[256*i+:256]),
   .w_k_v(w_k_v[i]),.w_k_rdy(w_k_rdy[i]),.w_k_addr(w_k_addr[30*i+:30]),.w_k_wdata(w_k_wdata[256*i+:256]),.w_k_wr_done(w_k_wr_done[i]),
   .fill_v(fill_v[i]),.fill_bank(fill_bank[i]),.fill_slot(fill_slot[6*i+:6]),.fill_epoch(fill_epoch[16*i+:16]),.fill_data(fill_data[256*i+:256]),
   .norm(s_norm[i]),.hfault(hfault_l[i]));
 end endgenerate
endmodule
`default_nettype wire
