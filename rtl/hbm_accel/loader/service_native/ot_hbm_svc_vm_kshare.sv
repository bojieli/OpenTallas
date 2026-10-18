`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/vmsm 2026-10-15: the HBM -> VM write path of the SM-specific 4-PC service engine (static successor of the
// retired v15 svc-band fill source of ot_hbm_svc_static_vm_delivery).  ONE master, eight per quadrant: instance k sits on
// the K ports between SM service group svg_<q><k> (lanes 0..3) and its four controllers ctl_<q>_p{4k+l}.
//
// DESIGN (compiler-windowed K-port share): every PC of the quadrant is owned by its SM group; the compiler opens a VM fill
// WINDOW by a calendar command (vm_v, from the quadrant fill calendar on stream_clk).  Per lane the window is
//   PEND : the group's next requests stay in this leaf's group-side pin skid (the group sees k_rdy low -- the K port is
//          the HBM controller boundary, the one place flow control is allowed, HANDOFF 0az / phy_mux precedent); the
//          lane waits until every group read beat and write done already accepted by the controller has come back;
//   ISSUE: 16 four-beat VM reads (k_len 4, PC-local address below, PC hash = P by construction), tag {bank,epoch[11:0],j};
//   WAIT : all 64 VM beats return; then the group owns the port again (NORM).
// The phases never overlap on one controller, so every response is steered by phase alone (the group's 17-bit tickets
// need no reserved tag bit).  VM beats cross to stream_clk in a Gray-pointer SPSC FIFO per lane (the only on-die CDC,
// at the HBM boundary) and leave as delivery fills {fill_v, fill_bank, fill_slot, fill_epoch, fill_data} for
// ot_hbm_svc_vmdel_lane (landing: begin / fill / block_ready / compiler start; the VM write is the static dq slot).
// VM block per PC: 64 slots = 16 bursts j x 4 beats b, slot = 4j+b; DRAM address of burst j:
//   bhi=j[2:0], col={vm_col,j[3]}, k_addr={row,bhi,col,P^col^{row[1:0],bhi},2'b00}  (incoming_pc of ot_hbm_svc_pc_ctrl_leaf
//   = addr[6:2]^addr[11:7]^addr[16:12] = P; addr[1:0]=0, len 4: legal).  Delivery sector = base + slot*32 + P.
// PIN REGISTERS (owner 19:50): every K input enters a 2-entry pin skid (ot_hbm_svc_pin_skid2: valid/data/ready flops,
// the ready input only pops), every K output leaves from a skid register, k_wr_done is re-timed by one flop, the VM
// command is captured at the stream pins, fills leave from stream flops, fault from a flop.  Added fixed latency:
// group->controller request +1 hbm edge (group-side skid) on top of the controller's own KREG skid, controller->group
// response +1 hbm edge; full rate (II=1) in both directions in NORM.  VM command -> first VM request: 1 stream + CDC
// (2 sync + 1) + window drain; last VM beat -> fill_v: CDC (2 sync + 1) + 1 stream edge.
// WB WRITE WINDOWS (H-NETLIST/dmawb 2026-10-16, decision 23:21: DMA write-back shares the controller K ports, no dedicated
// PCs).  A second compiler-placed window kind carries the quadrant's DMA write-back (ot_hbm_svc_wb_kport, which issues
// the window command {wbw_v, wbw_base[29:0] stack-local first sector, wbw_total[11:0] sectors} on the fixed stream edge
// it derives from the DMA's compiled fill start).  Stream side: pin capture, base+total-1, then each lane's EXACT sector
// count n_l = |{s in [base, base+total) : s[6:2]^s[11:7]^s[16:12] == 4*sm+l}| (head chunk + tail chunk + 4 per whole
// 128-sector chunk; <= 68 for total <= 2048) -> 74-bit Gray SPSC FIFO -> hbm side.  Per lane:
//   WPEND: the group's next requests stay in the group skid; the lane waits until every group WRITE already accepted by
//          the controller has signalled k_wr_done (write completions carry no tag; outstanding group READS may keep
//          returning during the window -- their responses carry tags and stay steered to the group);
//   WB   : exactly n_l single-beat full-strobe writes {addr = sector, wdata} from the WB K port (w_k_*: pin skid, the
//          write data source is the WB block's SRAM->CDC FIFO, so the waits stay inside the HBM boundary), each checked
//          for PC hash == P and base <= sector < base+total; their n_l k_wr_done go to w_k_wr_done (true PHY completion,
//          the WB block's posted count); then NORM.
// VM fill commands take priority when both kinds are pending at an all-NORM edge; windows never overlap on a lane.  Added
// latency on the WB write path: +1 hbm edge (WB pin skid) on top of the request skid; k_wr_done -> w_k_wr_done +1 hbm
// edge.  Window command -> first WB write: stream pins + 2 stream (count) + CDC (2 sync + 1) + group write drain.
// MUT: 1 = window does not wait for group responses (mis-steers a group beat), 2 = wrong PC hash in the VM address,
//      3 = WB window does not wait for the group's outstanding writes (window overlap: completions mis-steered),
//      4 = WB write sent to the wrong sector (addr bit 2 flipped), 5 = sm strap ignored (every leaf acts as SM 0).
// KRL1 (H-PC Claude 2026-10-16, with PC master ot_hbm_svc_pc_ctrl_leaf_cfg_h9b; default 0 = unchanged): the controller
//   pin-registers kr_rdy (READY-LATENCY-1: a beat transfers at edge e when c_kr_v(e) && c_kr_rdy sampled at e-1).
//   The controller-side response buffer C becomes a 3-entry ring (ot_hbm_svc_ring_h9b, no data movement on pop):
//   c_kr_rdy is a register = (C occupancy after this edge <= 1); a beat is taken when c_kr_v && the c_kr_rdy value the
//   controller sampled (kept here as c_rdy_seen); <= 2 beats can arrive after c_kr_rdy falls, so 3 entries never overflow
//   and steady streaming stays at II=1. MUT 6 (bench, KRL1): C depth 2 -> overflow fault under back-pressure.
module ot_hbm_svc_vm_kshare #(parameter integer MUT=0,KRL1=0) (
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 // die strap (H-SM DEDUPE 2026-10-16, was parameter SM): the SM group k of this leaf, PCs 4k..4k+3.  One hardened master
 // for all 32 instances; the strap lands in one pin flop per clock domain (static value, no CDC timing on it).
 input wire[2:0]sm,
 // group side (svg_<q><k>, lanes 0..3, same packing as ot_hbm_svc_sm_group)
 input wire[3:0]g_k_v,output wire[3:0]g_k_rdy,input wire[119:0]g_k_addr,input wire[15:0]g_k_len,input wire[67:0]g_k_tag,
 input wire[3:0]g_k_we,input wire[1023:0]g_k_wdata,input wire[127:0]g_k_wstrb,output reg[3:0]g_k_wr_done,
 output wire[3:0]g_kr_v,input wire[3:0]g_kr_rdy,output wire[67:0]g_kr_tag,output wire[15:0]g_kr_beat,output wire[1023:0]g_kr_data,
 // controller side (ctl_<q>_p{4k+l})
 output wire[3:0]c_k_v,input wire[3:0]c_k_rdy,output wire[119:0]c_k_addr,output wire[15:0]c_k_len,output wire[67:0]c_k_tag,
 output wire[3:0]c_k_we,output wire[1023:0]c_k_wdata,output wire[127:0]c_k_wstrb,input wire[3:0]c_k_wr_done,
 input wire[3:0]c_kr_v,output wire[3:0]c_kr_rdy,input wire[67:0]c_kr_tag,input wire[15:0]c_kr_beat,input wire[1023:0]c_kr_data,
 // VM fill window command (quadrant fill calendar, stream_clk)
 input wire vm_v,vm_bank,input wire[15:0]vm_epoch,input wire[14:0]vm_row,input wire[3:0]vm_col,
 // WB write window command (ot_hbm_svc_wb_kport of the quadrant, stream_clk)
 input wire wbw_v,input wire[29:0]wbw_base,input wire[11:0]wbw_total,
 // WB write requests (ot_hbm_svc_wb_kport K ports of PCs 4*SM..4*SM+3, hbm_clk): single beat, full strobe
 input wire[3:0]w_k_v,output wire[3:0]w_k_rdy,input wire[119:0]w_k_addr,input wire[1023:0]w_k_wdata,output reg[3:0]w_k_wr_done,
 // delivery fills (stream_clk) -> ot_hbm_svc_vmdel_lane of PC 4k+l
 output reg[3:0]fill_v,output reg[3:0]fill_bank,output reg[23:0]fill_slot,output reg[63:0]fill_epoch,output reg[1023:0]fill_data,
 output reg fault
);
 localparam integer KW=1+30+4+17+32+256;   // {we,addr,len,tag,wstrb,wdata}
 localparam integer RW=17+4+256;            // {tag,beat,data}
 localparam integer FW=1+16+6+256;          // {bank,epoch,slot,data}
 localparam integer CMW=1+16+15+4;          // {bank,epoch,row,col}
 localparam integer WQW=30+12+32;          // {base,total,n3,n2,n1,n0}
 localparam[2:0]NORM=0,PEND=1,ISSUE=2,WAIT=3,WPEND=4,WB=5;
 // local reset release per domain at the pins (H-SM 2026-10-16, native capture rule): each reset pin lands on ONE
 // async-clear flop (assert async, release synchronous one edge later); every other flop / FIFO / skid clears from it.
 reg srst_q,hrst_q;
 always @(posedge stream_clk or negedge stream_rst_n)if(!stream_rst_n)srst_q<=1'b0;else srst_q<=1'b1;
 always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)hrst_q<=1'b0;else hrst_q<=1'b1;
 reg[2:0]sm_s,sm_h;
 always @(posedge stream_clk)sm_s<=(MUT==5)?3'd0:sm;   // MUT 5: strap ignored
 always @(posedge hbm_clk)sm_h<=(MUT==5)?3'd0:sm;
 // ---------------------------------------------------------------- stream side: command pins -> CDC
 reg cv_q;reg[CMW-1:0]cd_q;
 always @(posedge stream_clk)cd_q<={vm_bank,vm_epoch,vm_row,vm_col};
 always @(posedge stream_clk or negedge srst_q)if(!srst_q)cv_q<=0;else cv_q<=vm_v;
 wire cf_wr_ready,cf_ov,cf_rd_valid,cf_un;wire[CMW-1:0]cf_rd_data;wire all_norm;
 wire take_cmd=cf_rd_valid&&all_norm;
 ot_hbm_svc_async_fifo #(.WIDTH(CMW),.DEPTH(4)) u_cmd(
  .wr_clk(stream_clk),.wr_rst_n(srst_q),.wr_valid(cv_q),.wr_ready(cf_wr_ready),.wr_data(cd_q),.wr_overflow(cf_ov),
  .rd_clk(hbm_clk),.rd_rst_n(hrst_q),.rd_valid(cf_rd_valid),.rd_ready(take_cmd),.rd_data(cf_rd_data),.rd_underflow(cf_un));
 reg[CMW-1:0]cmd_q;
 always @(posedge hbm_clk)if(take_cmd)cmd_q<=cf_rd_data;
 // ---------------------------------------------------------------- stream side: WB window command -> lane counts -> CDC
 function automatic [2:0] ov(input [4:0] g,input [7:0] lo,input [7:0] hi);   // |[4g,4g+4) intersect [lo,hi)|
  reg[7:0]a,z;begin a=({1'b0,g,2'b00}>lo)?{1'b0,g,2'b00}:lo;z=({1'b0,g,2'b00}+8'd4<hi)?{1'b0,g,2'b00}+8'd4:hi;ov=(z>a)?3'(z-a):3'd0;end
 endfunction
 function automatic [7:0] wcnt(input [4:0] p,input [29:0] b,input [29:0] e,input [11:0] t);   // e = b+t-1
  reg[22:0]d;reg[8:0]n;reg[4:0]gh,gt;
  begin
   gh=p^b[11:7]^b[16:12];gt=p^e[11:7]^e[16:12];d=e[29:7]-b[29:7];
   if(t==0)n=0;
   else if(d==0)n=9'(ov(gh,{1'b0,b[6:0]},{1'b0,e[6:0]}+8'd1));
   else n=9'(ov(gh,{1'b0,b[6:0]},8'd128))+9'(ov(gt,8'd0,{1'b0,e[6:0]}+8'd1))+{d[6:0]-7'd1,2'b00};
   wcnt=n[7:0];
  end
 endfunction
 reg wv1,wv2,wv3;reg[29:0]wb1,wb2;reg[11:0]wt1,wt2;reg[29:0]we2;reg[WQW-1:0]wq3;
 always @(posedge stream_clk)begin
  wb1<=wbw_base;wt1<=wbw_total;wb2<=wb1;wt2<=wt1;we2<=wb1+30'(wt1)-30'd1;
  wq3<={wb2,wt2,wcnt({sm_s,2'd3},wb2,we2,wt2),wcnt({sm_s,2'd2},wb2,we2,wt2),wcnt({sm_s,2'd1},wb2,we2,wt2),wcnt({sm_s,2'd0},wb2,we2,wt2)};
 end
 always @(posedge stream_clk or negedge srst_q)if(!srst_q)begin wv1<=0;wv2<=0;wv3<=0;end else begin wv1<=wbw_v;wv2<=wv1;wv3<=wv2;end
 wire wf_wr_ready,wf_ov,wf_rd_valid,wf_un;wire[WQW-1:0]wf_rd_data;
 wire take_wb=wf_rd_valid&&all_norm&&!cf_rd_valid;
 ot_hbm_svc_async_fifo #(.WIDTH(WQW),.DEPTH(4)) u_wcmd(
  .wr_clk(stream_clk),.wr_rst_n(srst_q),.wr_valid(wv3),.wr_ready(wf_wr_ready),.wr_data(wq3),.wr_overflow(wf_ov),
  .rd_clk(hbm_clk),.rd_rst_n(hrst_q),.rd_valid(wf_rd_valid),.rd_ready(take_wb),.rd_data(wf_rd_data),.rd_underflow(wf_un));
 reg[WQW-1:0]wcmd_q;reg[30:0]wend_q;
 always @(posedge hbm_clk)if(take_wb)begin wcmd_q<=wf_rd_data;wend_q<={1'b0,wf_rd_data[WQW-1-:30]}+31'(wf_rd_data[43:32]);end
 wire[29:0]wc_base=wcmd_q[WQW-1-:30];
 wire cm_bank=cmd_q[CMW-1];wire[15:0]cm_epoch=cmd_q[34:19];wire[14:0]cm_row=cmd_q[18:4];wire[3:0]cm_col=cmd_q[3:0];
 // ---------------------------------------------------------------- per lane
 wire[3:0]norm_l,hfault_l;
 wire[3:0]rf_valid;wire[FW*4-1:0]rf_data;
 genvar l;
 generate for(l=0;l<4;l=l+1)begin:lane
  wire[4:0]P={sm_h,2'(l)};
  // group-side request pin skid (A) and controller-side request skid (B)
  wire a_v,a_r;wire[KW-1:0]a_d;
  ot_hbm_svc_pin_skid2 #(.WIDTH(KW)) u_a(.clk(hbm_clk),.rst_n(hrst_q),.in_v(g_k_v[l]),.in_r(g_k_rdy[l]),
   .in_data({g_k_we[l],g_k_addr[30*l+:30],g_k_len[4*l+:4],g_k_tag[17*l+:17],g_k_wstrb[32*l+:32],g_k_wdata[256*l+:256]}),
   .out_v(a_v),.out_r(a_r),.out_data(a_d));
  reg[2:0]st;reg[3:0]j;reg[6:0]got;reg[7:0]g_rd_out;reg[5:0]g_wr_out;reg hf;reg[7:0]wsent,wdone;
  wire[7:0]wn=wcmd_q[8*l+:8];
  // WB-side request pin skid (E)
  wire e_v,e_r;wire[285:0]e_d;
  ot_hbm_svc_pin_skid2 #(.WIDTH(286)) u_e(.clk(hbm_clk),.rst_n(hrst_q),.in_v(w_k_v[l]),.in_r(w_k_rdy[l]),
   .in_data({w_k_addr[30*l+:30],w_k_wdata[256*l+:256]}),.out_v(e_v),.out_r(e_r),.out_data(e_d));
  wire wb_st=st==WB;
  wire w_more=wb_st&&wsent!=wn;
  wire[29:0]e_a=e_d[285:256];
  wire[29:0]w_addr=(MUT==4)?(e_a^30'h4):e_a;
  wire e_bad=(e_a[6:2]^e_a[11:7]^e_a[16:12])!=P||e_a<wc_base||{1'b0,e_a}>=wend_q;
  wire b_in_v,b_in_r,b_v;wire[KW-1:0]b_in_d,b_d;
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
  ot_hbm_svc_pin_skid2 #(.WIDTH(KW)) u_b(.clk(hbm_clk),.rst_n(hrst_q),.in_v(b_in_v),.in_r(b_in_r),.in_data(b_in_d),
   .out_v(b_v),.out_r(c_k_rdy[l]),.out_data(b_d));
  assign c_k_v[l]=b_v;
  assign {c_k_we[l],c_k_addr[30*l+:30],c_k_len[4*l+:4],c_k_tag[17*l+:17],c_k_wstrb[32*l+:32],c_k_wdata[256*l+:256]}=b_d;
  // owner of the request leaving B: the request skid holds only one phase at a time (B empty before ISSUE, ISSUE
  // pushes only VM, NORM resumes after the last VM beat), so a group request is any B pop outside ISSUE/WAIT.
  wire b_pop=b_v&&c_k_rdy[l];
  wire b_pop_grp=b_pop&&!(st==ISSUE||st==WAIT||st==WB);
  // controller-side response pin skid (C) -> group response skid (D) or the VM CDC FIFO
  wire c_v,c_r;wire[RW-1:0]c_d;
  wire c_ring_fault;
  if(KRL1!=0)begin:g_c_rl1
   reg c_rdy_q,c_rdy_seen; wire[2:0]c_cnt,c_cnt_next;
   ot_hbm_svc_ring_h9b #(.WIDTH(RW),.DEPTH((MUT==6)?2:3)) u_c(.clk(hbm_clk),.rst_n(hrst_q),.in_v(c_kr_v[l]&&c_rdy_seen),
    .in_data({c_kr_tag[17*l+:17],c_kr_beat[4*l+:4],c_kr_data[256*l+:256]}),.out_v(c_v),.pop(c_v&&c_r),.out_data(c_d),
    .cnt(c_cnt),.cnt_next(c_cnt_next),.fault(c_ring_fault));
   always @(posedge hbm_clk)
    if(!hrst_q)begin c_rdy_q<=1'b0;c_rdy_seen<=1'b0;end
    else begin c_rdy_q<=c_cnt_next<=3'd1; c_rdy_seen<=c_rdy_q; end
   assign c_kr_rdy[l]=c_rdy_q;
  end else begin:g_c_rl0
   assign c_ring_fault=1'b0;
   ot_hbm_svc_pin_skid2 #(.WIDTH(RW)) u_c(.clk(hbm_clk),.rst_n(hrst_q),.in_v(c_kr_v[l]),.in_r(c_kr_rdy[l]),
    .in_data({c_kr_tag[17*l+:17],c_kr_beat[4*l+:4],c_kr_data[256*l+:256]}),.out_v(c_v),.out_r(c_r),.out_data(c_d));
  end
  wire vm_phase=(st==ISSUE||st==WAIT)^(MUT==1&&st==PEND);
  wire d_r,f_r;
  ot_hbm_svc_pin_skid2 #(.WIDTH(RW)) u_d(.clk(hbm_clk),.rst_n(hrst_q),.in_v(c_v&&!vm_phase),.in_r(d_r),.in_data(c_d),
   .out_v(g_kr_v[l]),.out_r(g_kr_rdy[l]),.out_data({g_kr_tag[17*l+:17],g_kr_beat[4*l+:4],g_kr_data[256*l+:256]}));
  assign c_r=vm_phase?f_r:d_r;
  wire c_pop_grp=c_v&&!vm_phase&&d_r;
  wire c_pop_vm=c_v&&vm_phase&&f_r;
  wire[16:0]rt=c_d[RW-1-:17];wire[3:0]rb=c_d[259:256];
  wire tag_ok=rt=={cm_bank,cm_epoch[11:0],rt[3:0]}&&rb<4;
  wire[FW-1:0]f_d={cm_bank,cm_epoch,rt[3:0],rb[1:0],c_d[255:0]};
  wire f_ov,f_un;
  ot_hbm_svc_async_fifo #(.WIDTH(FW),.DEPTH(8)) u_fill(
   .wr_clk(hbm_clk),.wr_rst_n(hrst_q),.wr_valid(c_pop_vm),.wr_ready(f_r),.wr_data(f_d),.wr_overflow(f_ov),
   .rd_clk(stream_clk),.rd_rst_n(srst_q),.rd_valid(rf_valid[l]),.rd_ready(rf_valid[l]),.rd_data(rf_data[FW*l+:FW]),.rd_underflow(f_un));
  wire[8:0]rd_beats=b_pop_grp&&!b_d[KW-1]?{5'd0,b_d[KW-1-30-1-:4]}:9'd0;
  wire drained=!b_v&&g_rd_out==0&&g_wr_out==0;
  // Controller queue holds 32 writes and KREG holds two more: count needs six bits.
  wire wdrained=!b_v&&(g_wr_out==0||MUT==3);
  wire g_done=c_k_wr_done[l]&&!wb_st;
  always @(posedge hbm_clk or negedge hrst_q)begin
   if(!hrst_q)begin st<=NORM;j<=0;got<=0;g_rd_out<=0;g_wr_out<=0;hf<=0;wsent<=0;wdone<=0;end
   else begin
    g_rd_out<=g_rd_out+rd_beats[7:0]-{7'd0,c_pop_grp};
    g_wr_out<=g_wr_out+{5'd0,b_pop_grp&&b_d[KW-1]}-{5'd0,g_done};
    if(g_done&&g_wr_out==0)hf<=1;
    if(w_push)begin wsent<=wsent+1'b1;if(e_bad)hf<=1;end
    if(c_k_wr_done[l]&&wb_st)begin wdone<=wdone+1'b1;if(wdone==wsent)hf<=1;end
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
   if(!hrst_q)begin g_k_wr_done[l]<=0;w_k_wr_done[l]<=0;end
   else begin g_k_wr_done[l]<=g_done;w_k_wr_done[l]<=c_k_wr_done[l]&&wb_st;end
  assign norm_l[l]=st==NORM;assign hfault_l[l]=hf||f_ov||c_ring_fault;
 end endgenerate
 assign all_norm=&norm_l;
 // ---------------------------------------------------------------- stream side: fills + fault
 wire hfault_stream;reg sbad;
 ot_hbm_svc_fault_cdc u_fault_cdc(.wr_clk(hbm_clk),.wr_rst_n(hrst_q),
  .rd_clk(stream_clk),.rd_rst_n(srst_q),.src_fault(|hfault_l||cf_un||wf_un),
  .dst_fault(hfault_stream),.wr_overflow(),.rd_underflow());
 always @(posedge stream_clk or negedge srst_q)begin
  if(!srst_q)begin fill_v<=0;sbad<=0;fault<=0;end
  else begin
   fill_v<=rf_valid;
   if(cv_q&&!cf_wr_ready)sbad<=1;
   if(wv3&&!wf_wr_ready)sbad<=1;
   fault<=sbad||hfault_stream||cf_ov||wf_ov;
  end
 end
 integer i;
 always @(posedge stream_clk)for(i=0;i<4;i=i+1)begin
  {fill_bank[i],fill_epoch[16*i+:16],fill_slot[6*i+:6],fill_data[256*i+:256]}<=rf_data[FW*i+:FW];
 end
endmodule
`default_nettype wire
