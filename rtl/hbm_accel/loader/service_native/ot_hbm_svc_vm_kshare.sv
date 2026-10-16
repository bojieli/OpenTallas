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
// MUT: 1 = window does not wait for group responses (mis-steers a group beat), 2 = wrong PC hash in the VM address.
module ot_hbm_svc_vm_kshare #(parameter integer SM=0, parameter integer MUT=0) (
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
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
 // delivery fills (stream_clk) -> ot_hbm_svc_vmdel_lane of PC 4k+l
 output reg[3:0]fill_v,output reg[3:0]fill_bank,output reg[23:0]fill_slot,output reg[63:0]fill_epoch,output reg[1023:0]fill_data,
 output reg fault
);
 localparam integer KW=1+30+4+17+32+256;   // {we,addr,len,tag,wstrb,wdata}
 localparam integer RW=17+4+256;            // {tag,beat,data}
 localparam integer FW=1+16+6+256;          // {bank,epoch,slot,data}
 localparam integer CMW=1+16+15+4;          // {bank,epoch,row,col}
 localparam[1:0]NORM=0,PEND=1,ISSUE=2,WAIT=3;
 // ---------------------------------------------------------------- stream side: command pins -> CDC
 reg cv_q;reg[CMW-1:0]cd_q;
 always @(posedge stream_clk)cd_q<={vm_bank,vm_epoch,vm_row,vm_col};
 always @(posedge stream_clk or negedge stream_rst_n)if(!stream_rst_n)cv_q<=0;else cv_q<=vm_v;
 wire cf_wr_ready,cf_ov,cf_rd_valid,cf_un;wire[CMW-1:0]cf_rd_data;wire all_norm;
 wire take_cmd=cf_rd_valid&&all_norm;
 ot_hbm_svc_async_fifo #(.WIDTH(CMW),.DEPTH(4)) u_cmd(
  .wr_clk(stream_clk),.wr_rst_n(stream_rst_n),.wr_valid(cv_q),.wr_ready(cf_wr_ready),.wr_data(cd_q),.wr_overflow(cf_ov),
  .rd_clk(hbm_clk),.rd_rst_n(hbm_rst_n),.rd_valid(cf_rd_valid),.rd_ready(take_cmd),.rd_data(cf_rd_data),.rd_underflow(cf_un));
 reg[CMW-1:0]cmd_q;
 always @(posedge hbm_clk)if(take_cmd)cmd_q<=cf_rd_data;
 wire cm_bank=cmd_q[CMW-1];wire[15:0]cm_epoch=cmd_q[34:19];wire[14:0]cm_row=cmd_q[18:4];wire[3:0]cm_col=cmd_q[3:0];
 // ---------------------------------------------------------------- per lane
 wire[3:0]norm_l,hfault_l;
 wire[3:0]rf_valid;wire[FW*4-1:0]rf_data;
 genvar l;
 generate for(l=0;l<4;l=l+1)begin:lane
  localparam[4:0]P=5'(4*SM+l);
  // group-side request pin skid (A) and controller-side request skid (B)
  wire a_v,a_r;wire[KW-1:0]a_d;
  ot_hbm_svc_pin_skid2 #(.WIDTH(KW)) u_a(.clk(hbm_clk),.rst_n(hbm_rst_n),.in_v(g_k_v[l]),.in_r(g_k_rdy[l]),
   .in_data({g_k_we[l],g_k_addr[30*l+:30],g_k_len[4*l+:4],g_k_tag[17*l+:17],g_k_wstrb[32*l+:32],g_k_wdata[256*l+:256]}),
   .out_v(a_v),.out_r(a_r),.out_data(a_d));
  reg[1:0]st;reg[3:0]j;reg[6:0]got;reg[7:0]g_rd_out;reg[3:0]g_wr_out;reg hf;
  wire b_in_v,b_in_r,b_v;wire[KW-1:0]b_in_d,b_d;
  wire[4:0]bhi5={cm_row[1:0],j[2:0]};wire[4:0]col={cm_col,j[3]};
  wire[4:0]pcf=(MUT==2)?(col^bhi5):(P^col^bhi5);
  wire[29:0]vm_addr={cm_row,j[2:0],col,pcf,2'b00};
  wire[16:0]vm_tag={cm_bank,cm_epoch[11:0],j};
  wire vm_req=st==ISSUE;
  assign b_in_v=vm_req?1'b1:(st==NORM&&a_v);
  assign b_in_d=vm_req?{1'b0,vm_addr,4'd4,vm_tag,32'd0,256'd0}:a_d;
  assign a_r=st==NORM&&b_in_r;
  ot_hbm_svc_pin_skid2 #(.WIDTH(KW)) u_b(.clk(hbm_clk),.rst_n(hbm_rst_n),.in_v(b_in_v),.in_r(b_in_r),.in_data(b_in_d),
   .out_v(b_v),.out_r(c_k_rdy[l]),.out_data(b_d));
  assign c_k_v[l]=b_v;
  assign {c_k_we[l],c_k_addr[30*l+:30],c_k_len[4*l+:4],c_k_tag[17*l+:17],c_k_wstrb[32*l+:32],c_k_wdata[256*l+:256]}=b_d;
  // owner of the request leaving B: the request skid holds only one phase at a time (B empty before ISSUE, ISSUE
  // pushes only VM, NORM resumes after the last VM beat), so a group request is any B pop outside ISSUE/WAIT.
  wire b_pop=b_v&&c_k_rdy[l];
  wire b_pop_grp=b_pop&&!(st==ISSUE||st==WAIT);
  // controller-side response pin skid (C) -> group response skid (D) or the VM CDC FIFO
  wire c_v,c_r;wire[RW-1:0]c_d;
  ot_hbm_svc_pin_skid2 #(.WIDTH(RW)) u_c(.clk(hbm_clk),.rst_n(hbm_rst_n),.in_v(c_kr_v[l]),.in_r(c_kr_rdy[l]),
   .in_data({c_kr_tag[17*l+:17],c_kr_beat[4*l+:4],c_kr_data[256*l+:256]}),.out_v(c_v),.out_r(c_r),.out_data(c_d));
  wire vm_phase=(st==ISSUE||st==WAIT)^(MUT==1&&st==PEND);
  wire d_r,f_r;
  ot_hbm_svc_pin_skid2 #(.WIDTH(RW)) u_d(.clk(hbm_clk),.rst_n(hbm_rst_n),.in_v(c_v&&!vm_phase),.in_r(d_r),.in_data(c_d),
   .out_v(g_kr_v[l]),.out_r(g_kr_rdy[l]),.out_data({g_kr_tag[17*l+:17],g_kr_beat[4*l+:4],g_kr_data[256*l+:256]}));
  assign c_r=vm_phase?f_r:d_r;
  wire c_pop_grp=c_v&&!vm_phase&&d_r;
  wire c_pop_vm=c_v&&vm_phase&&f_r;
  wire[16:0]rt=c_d[RW-1-:17];wire[3:0]rb=c_d[259:256];
  wire tag_ok=rt=={cm_bank,cm_epoch[11:0],rt[3:0]}&&rb<4;
  wire[FW-1:0]f_d={cm_bank,cm_epoch,rt[3:0],rb[1:0],c_d[255:0]};
  wire f_ov,f_un;
  ot_hbm_svc_async_fifo #(.WIDTH(FW),.DEPTH(8)) u_fill(
   .wr_clk(hbm_clk),.wr_rst_n(hbm_rst_n),.wr_valid(c_pop_vm),.wr_ready(f_r),.wr_data(f_d),.wr_overflow(f_ov),
   .rd_clk(stream_clk),.rd_rst_n(stream_rst_n),.rd_valid(rf_valid[l]),.rd_ready(rf_valid[l]),.rd_data(rf_data[FW*l+:FW]),.rd_underflow(f_un));
  wire[8:0]rd_beats=b_pop_grp&&!b_d[KW-1]?{5'd0,b_d[KW-1-30-1-:4]}:9'd0;
  wire drained=!b_v&&g_rd_out==0&&g_wr_out==0;
  always @(posedge hbm_clk or negedge hbm_rst_n)begin
   if(!hbm_rst_n)begin st<=NORM;j<=0;got<=0;g_rd_out<=0;g_wr_out<=0;hf<=0;end
   else begin
    g_rd_out<=g_rd_out+rd_beats[7:0]-{7'd0,c_pop_grp};
    g_wr_out<=g_wr_out+{3'd0,b_pop_grp&&b_d[KW-1]}-{3'd0,c_k_wr_done[l]};
    if(c_k_wr_done[l]&&g_wr_out==0)hf<=1;
    if(c_pop_grp&&g_rd_out==0&&!(MUT==1))hf<=1;
    if(c_pop_vm&&!tag_ok)hf<=1;
    case(st)
     NORM:if(take_cmd)begin st<=PEND;j<=0;got<=0;end
     PEND:if(drained||MUT==1)st<=ISSUE;
     ISSUE:if(b_in_r)begin j<=j+1'b1;if(j==4'd15)st<=WAIT;end
     default:;
    endcase
    if(c_pop_vm)begin
     got<=got+1'b1;
     if(got==7'd63)st<=NORM;
    end
   end
  end
  always @(posedge hbm_clk or negedge hbm_rst_n)if(!hbm_rst_n)g_k_wr_done[l]<=0;else g_k_wr_done[l]<=c_k_wr_done[l];
  assign norm_l[l]=st==NORM;assign hfault_l[l]=hf||f_ov;
 end endgenerate
 assign all_norm=&norm_l;
 // ---------------------------------------------------------------- stream side: fills + fault
 reg[1:0]hfs;reg sbad;
 always @(posedge stream_clk or negedge stream_rst_n)begin
  if(!stream_rst_n)begin fill_v<=0;hfs<=0;sbad<=0;fault<=0;end
  else begin
   fill_v<=rf_valid;hfs<={hfs[0],|hfault_l||cf_un};
   if(cv_q&&!cf_wr_ready)sbad<=1;
   fault<=sbad||hfs[1]||cf_ov;
  end
 end
 integer i;
 always @(posedge stream_clk)for(i=0;i<4;i=i+1)begin
  {fill_bank[i],fill_epoch[16*i+:16],fill_slot[6*i+:6],fill_data[256*i+:256]}<=rf_data[FW*i+:FW];
 end
endmodule
`default_nettype wire
