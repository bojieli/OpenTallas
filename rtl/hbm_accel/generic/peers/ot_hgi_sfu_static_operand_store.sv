`timescale 1ns/1ps
`default_nettype none
// OT_SFU_SYNC_RST (H-SU k8, 2026-10-16 owner standard: regional SYNC reset trees, no async-clear fanout): when defined,
// every reset in this file is synchronous to its own clock (the regional rst_n comes registered from ot_rst_relay /
// the die's regional relays); undefined = the previous asynchronous form, bit-identical behaviour after release.
`ifndef OT_SFU_ARST
`ifdef OT_SFU_SYNC_RST
`define OT_SFU_ARST(r)
`else
`define OT_SFU_ARST(r) or negedge r
`endif
`endif
// Compiler-prefetched operand store for the actual sixteen-lane SFU.
// Four independent operand groups and one output group, each with sixteen
// interleaved physical banks. No issue/return queues, credits or leases.
// Eight arriving sectors can fill all four operand groups at two sectors per
// group per edge. A conflicting same-bank write is an error, never a retry.
// Index/gather memory and non-VM sources are NOT aliased onto these operands.
// The separate engine index port must receive its own actual mapped service.
module ot_hgi_sfu_static_operand_store #(
 parameter integer LWB=15, MUT_XBAR=0,
 // HBM-SAFE-K9 (10-19, coordinator 0ks): WPIPE=1 registers every bank-write input (VM stage sector meta + data and the
 // lane element writes vm_*) once on clk before the groups' write select, cutting the VM meta -> bank w_mask_in
 // (~702 ps / 19 lv) and lane u_sfu -> u_output wcoll_q (~717 ps / 19 lv) stages. Every bank write lands 1 edge later
 // (priced: SFU calendar write-landing +1; reads stay at their edges). GCLK=1: group g (0-3 operand, 4 output) runs on
 // its own regional root clk_grp[g] (its 16 macros + bank/crossbar logic sit in one floorplan column). Defaults 0 keep
 // every other user bit-identical (clk_grp unused).
 parameter integer WPIPE=0, GCLK=0,
 // LH-SU (10-19, safe-design items 3/4/6): WROT=1 bank-aligns each of the 8 stage sectors ONCE here (shared by the
 // four operand groups): slot b of sector s = the word j = (b - addr_lo) mod 16 when j < 8 (its mask bit), with the
 // row hi or hi+1 (wrap = b < addr_lo). Each group bank then takes the highest-numbered sector hitting it (the same
 // last-writer-wins order and same-bank collision fault as the per-word loop). Same edges; no schedule change.
 parameter integer WROT=0,
 // Same-edge kept scalar select copies; default off preserves released users.
 parameter integer NATIVE32=0
)(
 input wire clk,rst_n,
 input wire [4:0] clk_grp,
 input wire [3:0] scalar_load,scalar_enable,
 // NATIVE32 (s8): eight same-edge upstream copies per group (index 8*g+k) of scalar_load (bridge meta-edge copies)
 // and scalar_enable (split2 io-edge copies). Unused when NATIVE32=0.
 input wire [31:0] scalar_load_leaves,scalar_enable_leaves,
 input wire [95:0] scalar_addr,
 input wire [127:0] scalar_data,
 input wire [63:0] rd_re,
 input wire [1535:0] rd_addr,
 input wire [127:0] rd_src,
 output wire [2047:0] rd_q,
 input wire [15:0] vm_we,
 input wire [383:0] vm_waddr,
 input wire [511:0] vm_wdata,
 input wire [7:0] stage_v,
 input wire [15:0] stage_group,
 input wire [8*LWB-1:0] stage_addr,
 input wire [8*8*4-1:0] stage_lo_replicas,
 input wire [63:0] stage_mask,
 input wire [2047:0] stage_data,
 input wire [1:0] drain_v,
 input wire [2*16-1:0] drain_v_leaves,
 input wire [2*16*LWB-1:0] drain_addr_leaves,
 input wire [2*LWB-1:0] drain_addr,
 output wire [511:0] drain_data,
 output wire [1:0] drain_result_v,
 output reg fault
);
 generate if(LWB<14 || LWB>17)begin:g_bad_size
  ot_sfu_store_requires_actual_supported_SRAM_geometry u_refuse();
 end endgenerate
 wire [4:0] group_fault;
 reg [23:0] scalar_addr_q[0:3];
 reg [31:0] scalar_data_q[0:3];
 reg [3:0] scalar_valid;
 reg scalar_bad;
 // se_l[4*l+g]: the scalar_enable[g] copy that serves lane l (NATIVE32: upstream copy l/2; else the port itself)
 wire [63:0] se_l;
 for(genvar l=0;l<16;l=l+1)begin:g_se_l
  for(genvar g=0;g<4;g=g+1)begin:g_g
   assign se_l[4*l+g]=NATIVE32?scalar_enable_leaves[8*g+l/2]:scalar_enable[g];
  end
 end
 // NATIVE32 scalar registers: sq_all[80*g+:80] = {data, address copy B (lanes 8-15), address copy A (lanes 0-7)}
 wire [319:0] sq_all; wire [7:0] sv_all;
 generate if(NATIVE32)begin:g_scalar_native
  // s8: each upstream load copy enables ten of the eighty unreset bits of its group (same edge as the original
  // load); the two valid copies keep their reset.
  for(genvar g=0;g<4;g=g+1)begin:g_g
   wire [79:0] nv={scalar_data[32*g+:32],scalar_addr[24*g+:24],scalar_addr[24*g+:24]};
   (* keep=1,dont_touch=1 *) reg [79:0] sq;
   (* keep=1,dont_touch=1 *) reg [1:0] sv;
   for(genvar i=0;i<80;i=i+1)begin:g_b
    always @(posedge clk)if(scalar_load_leaves[8*g+i/10])sq[i]<=nv[i];
   end
   always @(posedge clk `OT_SFU_ARST(rst_n))
    if(!rst_n)sv<=0;else if(scalar_load_leaves[8*g+7])sv<=2'b11;
   assign sq_all[80*g+:80]=sq;assign sv_all[2*g+:2]=sv;
  end
  always @*begin
   scalar_bad=0;
   for(integer l=0;l<16;l=l+1)for(integer g=0;g<4;g=g+1)
    if(rd_re[4*l+g] && se_l[4*l+g] &&
     (!sv_all[2*g+l/8] || rd_addr[24*(4*l+g)+:24]!=sq_all[80*g+24*(l/8)+:24]))scalar_bad=1;
  end
 end else begin:g_scalar_original
  assign sq_all=0;assign sv_all=0;
  always @(posedge clk)for(integer g=0;g<4;g=g+1)
   if(scalar_load[g])begin scalar_addr_q[g]<=scalar_addr[24*g+:24];scalar_data_q[g]<=scalar_data[32*g+:32];end
  always @(posedge clk `OT_SFU_ARST(rst_n))
   if(!rst_n)scalar_valid<=0;else scalar_valid<=scalar_valid|scalar_load;
  always @*begin
   scalar_bad=0;
   for(integer l=0;l<16;l=l+1)for(integer g=0;g<4;g=g+1)
    if(rd_re[4*l+g] && scalar_enable[g] &&
     (!scalar_valid[g] || rd_addr[24*(4*l+g)+:24]!=scalar_addr_q[g]))scalar_bad=1;
  end
 end endgenerate
 reg bad_source,bad_range;
 always @*begin
  bad_source=0;bad_range=0;
  for(integer l=0;l<16;l=l+1)begin
   if(vm_we[l] && |vm_waddr[24*l+LWB+:24-LWB])bad_range=1;
   for(integer g=0;g<4;g=g+1)
    if(rd_re[4*l+g] && !se_l[4*l+g] && |rd_addr[24*(4*l+g)+LWB+:24-LWB])bad_range=1;
  end
  for(integer b=0;b<8;b=b+1)
   if(stage_v[b] && stage_addr[LWB*b+:LWB]>{LWB{1'b1}}-7)bad_range=1;
  for(integer b=0;b<2;b=b+1)
   if(drain_v[b] && drain_addr[LWB*b+:LWB]>{LWB{1'b1}}-7)bad_range=1;
  for(integer l=0;l<16;l=l+1)
   for(integer s=0;s<4;s=s+1)
    if(rd_re[4*l+s] && rd_src[8*l+2*s+:2]!=0)bad_source=1;
 end
 always @(posedge clk `OT_SFU_ARST(rst_n))
  if(!rst_n)fault<=0;
  else if(bad_source || bad_range || scalar_bad || |group_fault)fault<=1;
 // ---- bank-write landing stage (WPIPE): fault checks above keep the raw inputs (unchanged fault edges)
 wire [7:0] w_stage_v; wire [15:0] w_stage_group; wire [8*LWB-1:0] w_stage_addr; wire [63:0] w_stage_mask;
 wire [2047:0] w_stage_data; wire [15:0] w_vm_we; wire [383:0] w_vm_waddr; wire [511:0] w_vm_wdata;
 generate if(WPIPE)begin:g_wpipe
  reg [7:0] sv_q; reg [15:0] sg_q; reg [8*LWB-1:0] sa_q; reg [63:0] sm_q; reg [2047:0] sd_q;
  reg [15:0] we_q; reg [383:0] wa_q; reg [511:0] wd_q;
  always @(posedge clk `OT_SFU_ARST(rst_n))
   if(!rst_n)begin sv_q<=0;we_q<=0;end else begin sv_q<=stage_v;we_q<=vm_we;end
  always @(posedge clk)begin sg_q<=stage_group;sa_q<=stage_addr;sm_q<=stage_mask;sd_q<=stage_data;wa_q<=vm_waddr;wd_q<=vm_wdata;end
`ifdef OT_SFU_STORE_MUT_WPIPE_SKEW
  // bench negative control: the write enables bypass the landing stage while address / data take it (must mismatch)
  assign w_stage_v=stage_v; assign w_vm_we=vm_we;
`else
  assign w_stage_v=sv_q; assign w_vm_we=we_q;
`endif
  assign w_stage_group=sg_q; assign w_stage_addr=sa_q; assign w_stage_mask=sm_q; assign w_stage_data=sd_q;
  assign w_vm_waddr=wa_q; assign w_vm_wdata=wd_q;
 end else begin:g_wdirect
  assign w_stage_v=stage_v; assign w_stage_group=stage_group; assign w_stage_addr=stage_addr; assign w_stage_mask=stage_mask;
  assign w_stage_data=stage_data; assign w_vm_we=vm_we; assign w_vm_waddr=vm_waddr; assign w_vm_wdata=vm_wdata;
 end endgenerate
 // ---- shared bank-aligned sector rotate (WROT)
 localparam integer RBS=LWB-4;
 wire [8*16*32-1:0] swr_d; wire [8*16-1:0] swr_m, swr_w; wire [8*RBS-1:0] swr_r0, swr_r1;
 wire [8*16*16*4-1:0] rotate_lo;
 generate if(NATIVE32 && WPIPE && WROT)begin:g_rotate_copies
  // Capture on the existing WPIPE edge. s8: eight select copies per bank, each serving one 4-bit rotate slice
  // (two 2-bit halves); every upstream replica (8/sector, one per bank pair) feeds 16 of these FFs plus the two
  // banks' presel hit decode below. No new stage or data storage is added.
  (* keep=1,dont_touch=1 *) reg [8*16*8*4-1:0] lo_q;
  for(genvar s=0;s<8;s=s+1)begin:g_s
   for(genvar b=0;b<16;b=b+1)begin:g_b
    for(genvar c=0;c<8;c=c+1)begin:g_c
     always @(posedge clk)lo_q[4*((s*16+b)*8+c)+:4]<=stage_lo_replicas[4*(s*8+b/2)+:4];
    end
    for(genvar h=0;h<16;h=h+1)begin:g_h
     assign rotate_lo[4*((s*16+b)*16+h)+:4]=lo_q[4*((s*16+b)*8+h/2)+:4];
    end
   end
  end
 end else begin:g_rotate_original
  for(genvar s=0;s<8;s=s+1)begin:g_s
   for(genvar b=0;b<16;b=b+1)begin:g_b
    for(genvar h=0;h<16;h=h+1)begin:g_h
     assign rotate_lo[4*((s*16+b)*16+h)+:4]=w_stage_addr[LWB*s+:4];
    end
   end
  end
 end endgenerate
 generate if(WROT)begin:g_wrot
  for(genvar s=0;s<8;s=s+1)begin:g_s
   wire [RBS-1:0] hi=w_stage_addr[LWB*s+4+:RBS];
   assign swr_r0[RBS*s+:RBS]=hi;
   assign swr_r1[RBS*s+:RBS]=hi+1'b1;
   for(genvar b=0;b<16;b=b+1)begin:g_b
    localparam [3:0] B4=b;
    wire [3:0] lo=rotate_lo[4*((s*16+b)*16)+:4];
`ifdef OT_SFU_STORE_MUT_WROT
    // bench negative control: the rotate is off by one bank (every staged word lands in the neighbouring bank)
    wire [3:0] d=B4-lo-4'd1;
`else
    wire [3:0] d=B4-lo;
`endif
    assign swr_m[16*s+b]=!d[3] && w_stage_mask[8*s+d[2:0]];
    assign swr_w[16*s+b]=(B4<lo);
    for(genvar h=0;h<16;h=h+1)begin:g_half
`ifdef OT_SFU_STORE_MUT_WROT
     wire [3:0] dh=B4-rotate_lo[4*((s*16+b)*16+h)+:4]-4'd1;
`else
     wire [3:0] dh=B4-rotate_lo[4*((s*16+b)*16+h)+:4];
`endif
     assign swr_d[32*(16*s+b)+2*h+:2]=w_stage_data[256*s+32*dh[2:0]+2*h+:2];
    end
   end
  end
 end else begin:g_nowrot
  assign swr_d=0; assign swr_m=0; assign swr_w=0; assign swr_r0=0; assign swr_r1=0;
 end endgenerate
 wire [4:0] gck;
 for(genvar g=0;g<5;g=g+1)begin:g_gck
  assign gck[g]=GCLK?clk_grp[g]:clk;
 end
 // ---- s8 PRESEL (NATIVE32 && WPIPE [&& WROT]): every bank's write enable, one-hot source selects and collision are
 // decoded from the RAW bank-write inputs and captured on the EXISTING WPIPE edge in kept per-bank registers; each
 // select has its own copy per destination slice (data[15:0], data[31:16], row), so no shared decoded select drives a
 // wide mux. Same write edge, same last-writer order and the same collision-fault edge as the WPIPE loop.
 localparam integer PS=(NATIVE32 && WPIPE && WROT)?1:0, PSO=(NATIVE32 && WPIPE)?1:0;
 wire [127:0] ps_hit,ps_wrap;   // [16*s+b]: sector s writes bank b / with row hi+1 (raw inputs, WPIPE D side)
 if(PS)begin:g_presel_hits
  for(genvar s=0;s<8;s=s+1)begin:g_s
   for(genvar b=0;b<16;b=b+1)begin:g_b
    localparam [3:0] B4=b;
    wire [3:0] lo=stage_lo_replicas[4*(s*8+b/2)+:4];
`ifdef OT_SFU_STORE_MUT_WROT
    wire [3:0] d=B4-lo-4'd1;
`else
    wire [3:0] d=B4-lo;
`endif
    assign ps_hit[16*s+b]=stage_v[s] && !d[3] && stage_mask[8*s+d[2:0]];
    assign ps_wrap[16*s+b]=(B4<lo);
   end
  end
 end else begin:g_presel_none
  assign ps_hit=0;assign ps_wrap=0;
 end
 for(genvar g=0;g<4;g=g+1)begin:g_operand
  wire [15:0] req;
  wire [383:0] addr;
  wire [511:0] data;
  wire [511:0] scalar_read;
  wire [31:0] scalar_selected;
  if(NATIVE32)begin:g_scalar_leaf
   // s8: each lane's two half selects and four byte enables come from that lane's own upstream enable copy.
   (* keep=1, dont_touch=1 *) reg [31:0] selected_q;
   for(genvar sl=0;sl<16;sl=sl+1)begin:g_l
    always @(posedge clk)selected_q[2*sl+:2]<={2{se_l[4*sl+g]}};
    for(genvar by=0;by<4;by=by+1)begin:g_b
     ot_hgi_sfu_scalar_byte u_byte(.clk(clk),.re(rd_re[4*sl+g]),.en(se_l[4*sl+g]),
      .d(sq_all[80*g+48+8*by+:8]),.q(scalar_read[32*sl+8*by+:8]));
    end
   end
   assign scalar_selected=selected_q;
  end else begin:g_scalar_original
   reg [511:0] read_q;
   reg selected_q;
   always @(posedge clk)begin
    selected_q<=scalar_enable[g];
    for(integer sl=0;sl<16;sl=sl+1)if(rd_re[4*sl+g] && scalar_enable[g])read_q[32*sl+:32]<=scalar_data_q[g];
   end
   assign scalar_selected={32{selected_q}};
   assign scalar_read=read_q;
  end
  wire [7:0] sw;
  for(genvar l=0;l<16;l=l+1)begin:g_lane
   assign req[l]=rd_re[4*l+g] && rd_src[8*l+2*g+:2]==0 && !se_l[4*l+g];
   assign addr[24*l+:24]=rd_addr[(4*l+g)*24+:24];
   for(genvar h=0;h<2;h=h+1)begin:g_half
    assign rd_q[(4*l+g)*32+16*h+:16]=scalar_selected[2*l+h]?scalar_read[32*l+16*h+:16]:data[32*l+16*h+:16];
   end
  end
  for(genvar b=0;b<8;b=b+1)begin:g_stage
   assign sw[b]=w_stage_v[b] && w_stage_group[2*b+:2]==g;
  end
  wire [15:0] pw_we; wire pw_coll; wire [127:0] pw_sd0,pw_sd1,pw_sa0,pw_sa1;
  wire [16*8*32-1:0] pw_d; wire [16*8*RBS-1:0] pw_r0,pw_r1;
  if(PS)begin:g_presel
   wire [7:0] gv;
   for(genvar s=0;s<8;s=s+1)begin:g_gv
    assign gv[s]=stage_group[2*s+:2]==g;
   end
   reg [15:0] we_d; reg coll_d; reg [127:0] win_d,wr_d;    // [8*b+s]
   always @*begin
    coll_d=0;we_d=0;win_d=0;wr_d=0;
    for(integer b=0;b<16;b=b+1)
     for(integer s=7;s>=0;s=s-1)
      if(gv[s] && ps_hit[16*s+b])begin
       if(we_d[b])coll_d=1;                           // a higher sector already writes this bank: fail closed
       else begin win_d[8*b+s]=1;wr_d[8*b+s]=ps_wrap[16*s+b];end
       we_d[b]=1;
      end
   end
   (* keep=1,dont_touch=1 *) reg [15:0] we_q;
   (* keep=1,dont_touch=1 *) reg coll_q;
   (* keep=1,dont_touch=1 *) reg [127:0] sd0_q,sd1_q,sa0_q,sa1_q;
   (* keep=1,dont_touch=1 *) reg [8*RBS-1:0] hi_q;       // this group's copy of the sector rows
   always @(posedge clk)begin
    we_q<=we_d;coll_q<=coll_d;sd0_q<=win_d;sd1_q<=win_d;sa0_q<=win_d&~wr_d;sa1_q<=win_d&wr_d;
    for(integer s=0;s<8;s=s+1)hi_q[RBS*s+:RBS]<=stage_addr[LWB*s+4+:RBS];
   end
   assign pw_we=we_q;assign pw_coll=coll_q;
   assign pw_sd0=sd0_q;assign pw_sd1=sd1_q;assign pw_sa0=sa0_q;assign pw_sa1=sa1_q;
   for(genvar b=0;b<16;b=b+1)begin:g_pb
    for(genvar s=0;s<8;s=s+1)begin:g_ps
     assign pw_d[32*(8*b+s)+:32]=swr_d[32*(16*s+b)+:32];
     assign pw_r0[RBS*(8*b+s)+:RBS]=hi_q[RBS*s+:RBS];
     assign pw_r1[RBS*(8*b+s)+:RBS]=hi_q[RBS*s+:RBS]+1'b1;
    end
   end
  end else begin:g_presel_off
   assign pw_we=0;assign pw_coll=0;assign pw_sd0=0;assign pw_sd1=0;assign pw_sa0=0;assign pw_sa1=0;
   assign pw_d=0;assign pw_r0=0;assign pw_r1=0;
  end
  ot_hgi_su_lgroup2 #(.N(16),.M(16),.LWB(LWB),.AW(24),.NLW(0),
   .MACRO(1),.MUT_XBAR(MUT_XBAR),.NS(8),.WROT(WROT),.NATIVE32(NATIVE32),.PRESEL(PS),.PNC(8)) u_group(
   .clk(gck[g]),.rst_n(rst_n),.rq(req),.rr(req),.ra(addr),.rd(data),
   .sr_v(8'd0),.sr_addr({8*LWB{1'b0}}),.sr_d(),.sr_rv(),
   .sw_v(sw),.sw_addr(w_stage_addr),.sw_mask(w_stage_mask),.sw_d(w_stage_data),
   .swr_d(swr_d),.swr_m(swr_m),.swr_w(swr_w),.swr_r0(swr_r0),.swr_r1(swr_r1),
   .lw(1'b0),.lwa(24'd0),.lwd(32'd0),.s1_v(1'b0),.s1_a({LWB{1'b0}}),.s1_d(32'd0),
   .pw_we(pw_we),.pw_coll(pw_coll),.pw_sd0(pw_sd0),.pw_sd1(pw_sd1),.pw_sa0(pw_sa0),.pw_sa1(pw_sa1),
   .pw_d(pw_d),.pw_r0(pw_r0),.pw_r1(pw_r1),
   .flt(group_fault[g]));
 end
 // ---- output group (lane element writes): s8 PRESEL. Bank b's only legal writers are lane 0 (any bank) and lane b
 // (its own bank); the later lane (b) wins, a row mismatch or any other lane/bank pair is the same write-collision
 // fault as the loop (an illegal lane write is fault-only here: fail closed).
 wire [15:0] po_we; wire po_coll; wire [31:0] po_sd0,po_sd1,po_sa0;
 wire [16*2*32-1:0] po_d; wire [16*2*RBS-1:0] po_r;
 if(PSO)begin:g_presel_out
  reg [15:0] we_d; reg coll_d; reg [31:0] sel_d;           // [2*b+c]: c=0 lane 0, c=1 lane b
  always @*begin
   coll_d=0;we_d=0;sel_d=0;
   for(integer l=1;l<16;l=l+1)
    if(vm_we[l] && vm_waddr[24*l+:4]!=l)coll_d=1;
   for(integer b=0;b<16;b=b+1)begin
    if(vm_we[0] && vm_waddr[0+:4]==b)begin we_d[b]=1;sel_d[2*b]=1;end
    if(b!=0 && vm_we[b] && vm_waddr[24*b+:4]==b)begin
     if(we_d[b] && vm_waddr[4+:RBS]!=vm_waddr[24*b+4+:RBS])coll_d=1;
     we_d[b]=1;sel_d[2*b]=0;sel_d[2*b+1]=1;
    end
   end
  end
  (* keep=1,dont_touch=1 *) reg [15:0] we_q;
  (* keep=1,dont_touch=1 *) reg coll_q;
  (* keep=1,dont_touch=1 *) reg [31:0] sd0_q,sd1_q,sa0_q;
  always @(posedge clk)begin we_q<=we_d;coll_q<=coll_d;sd0_q<=sel_d;sd1_q<=sel_d;sa0_q<=sel_d;end
  assign po_we=we_q;assign po_coll=coll_q;assign po_sd0=sd0_q;assign po_sd1=sd1_q;assign po_sa0=sa0_q;
  for(genvar b=0;b<16;b=b+1)begin:g_pb
   assign po_d[32*(2*b)+:32]=w_vm_wdata[0+:32];
   assign po_d[32*(2*b+1)+:32]=w_vm_wdata[32*b+:32];
   assign po_r[RBS*(2*b)+:RBS]=w_vm_waddr[4+:RBS];
   assign po_r[RBS*(2*b+1)+:RBS]=w_vm_waddr[24*b+4+:RBS];
  end
 end else begin:g_presel_out_off
  assign po_we=0;assign po_coll=0;assign po_sd0=0;assign po_sd1=0;assign po_sa0=0;assign po_d=0;assign po_r=0;
 end
 ot_hgi_su_lgroup2 #(.N(16),.M(16),.LWB(LWB),.AW(24),.NLW(16),
  .MACRO(1),.MUT_XBAR(MUT_XBAR),.NS(2),.NATIVE32(NATIVE32),.PRESEL(PSO),.PNC(2)) u_output(
  .clk(gck[4]),.rst_n(rst_n),.rq(16'd0),.rr(16'd0),.ra(384'd0),.rd(),
  .sr_v(drain_v),.sr_addr(drain_addr),.sr_v_leaf(drain_v_leaves),.sr_addr_leaf(drain_addr_leaves),.sr_d(drain_data),.sr_rv(drain_result_v),
  .sw_v(2'd0),.sw_addr({2*LWB{1'b0}}),.sw_mask(16'd0),.sw_d(512'd0),
  .lw(w_vm_we),.lwa(w_vm_waddr),.lwd(w_vm_wdata),.s1_v(1'b0),.s1_a({LWB{1'b0}}),.s1_d(32'd0),
  .pw_we(po_we),.pw_coll(po_coll),.pw_sd0(po_sd0),.pw_sd1(po_sd1),.pw_sa0(po_sa0),.pw_sa1(32'd0),
  .pw_d(po_d),.pw_r0(po_r),.pw_r1(po_r),
  .flt(group_fault[4]));
endmodule
// Isolate each enabled byte so ABC cannot share one 32-bit mux-enable driver (s8: the read/enable AND is inside).
(* keep_hierarchy=1 *) module ot_hgi_sfu_scalar_byte(input wire clk,re,en,input wire[7:0]d,output reg[7:0]q);
 always @(posedge clk)if(re && en)q<=d;
endmodule
`default_nettype wire
