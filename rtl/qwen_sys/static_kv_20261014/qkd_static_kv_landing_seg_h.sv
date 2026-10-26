`timescale 1ns/1ps
// KVCTRL 1815 (2026-10-16, lead Q-KV): HIERARCHICAL form of the static landing segment qkd_static_kv_landing_seg.
// Why: the flat seg tile (ls5, 151.2 x 1,512 um) is 9 % utilised and its ONE ck root spans 1,512 um: measured gate TT
// insertion 722..753 ps (9,492 sinks), so even a CLOSED flat view fails the native launch rule (<= 220 ps).
// The content splits along its own seams into hardened children with short local roots:
//   * u_lane[q] = qkd_static_kv_landing_lane (ONE master, 4 x at the PC pitch): the landing PC (VMAP 1, FAULT_PIPE 1,
//     WRITE_PIPE 0, CHECK_PIPE 1) with its 128x256 SRAM, plus THAT PC's 256-b response data pipe (the data part of the
//     branch hop295, then idata, then rsp_data: the same three registers as the flat seg), so the 1,024-b data never
//     travels to the centre: PC q's data enters on the E face and leaves on the W face within PC q's pitch.
//   * u_row = qkd_static_kv_landing_row at the centre: the VREQ row control (rowctl DATA 0: all its control registers,
//     the 4-lane compare and the fault) plus, for the two NEAR branches 1 / 2, the request hop38 and the 39-b control
//     part of the response hop295 with their branch reset flops.
//   * u_rly0 / u_rly3 = qkd_static_kv_landing_relay (one master, the second mirrored): the same hop38 + 39-b hop + reset
//     flop for the two FAR branches 0 / 3, placed half way between lane 0 / 3 and the row (each lane-to-row run is
//     ~510 um centre to centre: one register stage per ~255 um, as the flat seg's hop did).
//   * strap / arm registers (qkd_static_kv_landing_preg, h2, lead Q-KV 2026-10-17: shared pins must stay within the
//     measured reach 446 um): arm / epoch / layer / cfg_stack / cfg_group are registered in the row (copy for lanes 1/2)
//     and in each relay (lanes 0/3), and the lane PCs take them as their input registers (PRE_REG 1): the same edge
//     from the segment pin. The lane reset input is a registered copy of rst_n (lane reset deassertion +1 edge: a reset
//     guard only, no traffic edge moves; the lane PC's async reset stays its own local rn flop).
// Every seam is register to register with the SAME registers as the flat seg, so this parent is cycle-identical to
// qkd_static_kv_landing_seg (latency 8 edges); bench tools/qwen_static_kv/run_landing_seg_h.sh = the flat bench with
// this parent as the DUT.  Clocks: one top clock port per hard-child clock pin (cluster entry rule): ck -> u_row,
// ck_p0..ck_p3 -> u_lane[0..3], ck_r0 / ck_r3 -> u_rly0 / u_rly3; the die delivers each from its regional tree.
// The PC input registers for the shared segment pins, placed upstream within reach (row / relay); see PRE_REG.
module qkd_static_kv_landing_preg(
    input wire ck,input wire rst_n,input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    input wire [1:0] cfg_stack,input wire [2:0] cfg_group,
    output reg arm_o,output reg [15:0] epoch_o,output reg [5:0] layer_o,output reg [1:0] stack_o,output reg [2:0] group_o,
    output reg rst_o
);
    (* keep *) reg rnu;
    always @(posedge ck) rnu <= rst_n;
    always @(posedge ck or negedge rnu) if(!rnu) arm_o<=1'b0; else arm_o<=arm;
    always @(posedge ck)begin epoch_o<=epoch;layer_o<=layer;stack_o<=cfg_stack;group_o<=cfg_group;rst_o<=rst_n;end
endmodule

module qkd_static_kv_landing_lane #(parameter integer MUT=0,HOP_MUT=0)(
    input wire ck,input wire rst_n,
    input wire [1:0] cfg_stack,input wire [2:0] cfg_group,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    input wire expected_put,input wire [9:0] expected_sector,
    input wire actual_valid,input wire [9:0] actual_sector,
    input wire [15:0] actual_epoch,input wire [5:0] actual_layer,input wire [255:0] actual_data,
    // request from the row (its hop38 registers)
    input wire get,input wire [13:0] get_t,input wire get_v,input wire [15:0] get_epoch,input wire [5:0] get_layer,
    // response control to the row (the PC's out_* / fault registers; the row's hop captures them)
    output wire out_valid,output wire [13:0] out_t,output wire out_v,output wire [15:0] out_epoch,
    output wire [5:0] out_layer,output wire fault,
    // response data lane (rsp_data[256q+:256] of the segment)
    output reg [255:0] rsp_data
);
    wire [255:0] od,hd;
    qkd_static_kv_landing_pc #(.MUT(MUT),.VMAP(1),.FAULT_PIPE(1),.WRITE_PIPE(0),.CHECK_PIPE(1),.PRE_REG(1))u_pc(
     .ck(ck),.rst_n(rst_n),.cfg_stack(cfg_stack),.cfg_group(cfg_group),.arm(arm),.epoch(epoch),.layer(layer),
     .expected_put(expected_put),.expected_sector(expected_sector),
     .actual_valid(actual_valid),.actual_sector(actual_sector),
     .actual_epoch(actual_epoch),.actual_layer(actual_layer),.actual_data(actual_data),
     .get(get),.get_t(get_t),.get_v(get_v),.get_epoch(get_epoch),.get_layer(get_layer),
     .out_valid(out_valid),.out_data(od),.out_t(out_t),
     .out_v(out_v),.out_epoch(out_epoch),.out_layer(out_layer),.fault(fault));
    // the data part of the branch response hop295 (same reset form: hrn <= rst_n, hop rn from it)
    (* keep *) reg hrn;
    always @(posedge ck) hrn <= rst_n;
    qkd_static_kv_hop #(.W(256),.MUT(HOP_MUT))u_rsp(.ck(ck),.rst_n(hrn),.a(od),.b(hd));
    (* keep *) reg [255:0] idata;
    always @(posedge ck)begin idata<=hd;rsp_data<=idata;end
endmodule

module qkd_static_kv_landing_relay #(parameter integer MUT=0)(
    input wire ck,input wire rst_n,
    input wire [37:0] req_a,output wire [37:0] req_b,     // {layer6, epoch16, v, t14, get}: row -> lane
    input wire [38:0] rsp_a,output wire [38:0] rsp_b,     // {fault, layer6, epoch16, v, t14, valid}: lane -> row
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,input wire [1:0] cfg_stack,input wire [2:0] cfg_group,
    output wire arm_o,output wire [15:0] epoch_o,output wire [5:0] layer_o,output wire [1:0] stack_o,output wire [2:0] group_o,
    output wire rst_o
);
    qkd_static_kv_landing_preg u_preg(.ck(ck),.rst_n(rst_n),.arm(arm),.epoch(epoch),.layer(layer),.cfg_stack(cfg_stack),
      .cfg_group(cfg_group),.arm_o(arm_o),.epoch_o(epoch_o),.layer_o(layer_o),.stack_o(stack_o),.group_o(group_o),.rst_o(rst_o));
    (* keep *) reg hrn;
    always @(posedge ck) hrn <= rst_n;
    qkd_static_kv_hop38 #(.MUT(MUT==2))u_req(.ck(ck),.rst_n(hrn),.a(req_a),.b(req_b));
    qkd_static_kv_hop #(.W(39))u_rsp(.ck(ck),.rst_n(hrn),.a(rsp_a),.b(rsp_b));
endmodule

// Row: lo face = branches 0 (via u_rly0) and 1, hi face = branches 2 and 3 (via u_rly3); bit order [b] = branch lo/hi+b.
module qkd_static_kv_landing_row (
    input wire ck,input wire rst_n,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    input wire req_valid,input wire [13:0] req_t,input wire req_v,
    input wire [15:0] req_epoch,input wire [5:0] req_layer,
    input wire vreq_valid,input wire [13:0] vreq_t,
    output wire rsp_valid,output wire [13:0] rsp_t,
    output wire rsp_v,output wire [15:0] rsp_epoch,output wire [5:0] rsp_layer,output wire fault,
    output wire [75:0] req_lo,output wire [75:0] req_hi,  // per branch {layer6, epoch16, v, t14, get}
    input wire [77:0] rsp_lo,input wire [77:0] rsp_hi,    // per branch {fault, layer6, epoch16, v, t14, valid}
    input wire [1:0] cfg_stack,input wire [2:0] cfg_group,  // lanes 1/2 PC input registers (PRE_REG) live here
    output wire arm_o,output wire [15:0] epoch_o,output wire [5:0] layer_o,output wire [1:0] stack_o,output wire [2:0] group_o,
    output wire rst_o
);
    qkd_static_kv_landing_preg u_preg(.ck(ck),.rst_n(rst_n),.arm(arm),.epoch(epoch),.layer(layer),.cfg_stack(cfg_stack),
      .cfg_group(cfg_group),.arm_o(arm_o),.epoch_o(epoch_o),.layer_o(layer_o),.stack_o(stack_o),.group_o(group_o),.rst_o(rst_o));
    wire [3:0] get,gv;
    wire [55:0] gt;
    wire [63:0] ge;
    wire [23:0] gl;
    wire [151:0] rq_all;          // 4 x 38: the rowctl request word per branch
    wire [155:0] rs_all;          // 4 x 39: the response control word per branch as captured for the rowctl
    wire [155:0] rs_in = {rsp_hi,rsp_lo};
    wire [151:0] rq_out;
    for(genvar branch=0;branch<4;branch=branch+1)begin:g_br
      assign rq_all[38*branch+:38]={gl[6*branch+:6],ge[16*branch+:16],gv[branch],gt[14*branch+:14],get[branch]};
      if(branch==1 || branch==2)begin:g_hop          // near branches: their hops live here
        (* keep *) reg hrn;
        always @(posedge ck) hrn <= rst_n;
        qkd_static_kv_hop38 u_req(.ck(ck),.rst_n(hrn),.a(rq_all[38*branch+:38]),.b(rq_out[38*branch+:38]));
        qkd_static_kv_hop #(.W(39))u_rsp(.ck(ck),.rst_n(hrn),.a(rs_in[39*branch+:39]),.b(rs_all[39*branch+:39]));
      end else begin:g_far                            // far branches: hops in u_rly0 / u_rly3
        assign rq_out[38*branch+:38]=rq_all[38*branch+:38];
        assign rs_all[39*branch+:39]=rs_in[39*branch+:39];
      end
    end
    assign req_lo=rq_out[75:0];assign req_hi=rq_out[151:76];
    wire [3:0] ov_d,pf_d,vv_d;
    wire [55:0] ot_d;
    wire [63:0] oe_d;
    wire [23:0] ol_d;
    for(genvar branch=0;branch<4;branch=branch+1)begin:g_unpack
      assign {pf_d[branch],ol_d[6*branch+:6],oe_d[16*branch+:16],vv_d[branch],ot_d[14*branch+:14],ov_d[branch]}=rs_all[39*branch+:39];
    end
    qkd_static_kv_rowctl #(.VREQ(1),.DATA(0)) u_rowctl(
      .ck(ck),.rst_n(rst_n),.req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),
      .vreq_valid(vreq_valid),.vreq_t(vreq_t),.arm(arm),.epoch(epoch),.layer(layer),
      .pc_get(get),.pc_get_t(gt),.pc_get_v(gv),.pc_get_epoch(ge),.pc_get_layer(gl),
      .pc_valid(ov_d),.pc_data(1024'd0),.pc_t(ot_d),.pc_v(vv_d),.pc_epoch(oe_d),.pc_layer(ol_d),.pc_fault(pf_d),
      .rsp_valid(rsp_valid),.rsp_data(),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),.fault(fault));
endmodule

// Wires-only parent: the data ports of qkd_static_kv_landing_seg + one clock entry per hard child.
module qkd_static_kv_landing_seg_h #(
    parameter integer MUT=0,HOP_MUT=0
)(
    input wire ck,input wire ck_p0,input wire ck_p1,input wire ck_p2,input wire ck_p3,input wire ck_r0,input wire ck_r3,
    input wire rst_n,
    input wire [1:0] cfg_stack,input wire [2:0] cfg_group,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    input wire [3:0] expected_put,input wire [39:0] expected_sector,
    input wire [3:0] actual_valid,input wire [39:0] actual_sector,
    input wire [63:0] actual_epoch,input wire [23:0] actual_layer,input wire [1023:0] actual_data,
    input wire req_valid,input wire [13:0] req_t,input wire req_v,
    input wire [15:0] req_epoch,input wire [5:0] req_layer,
    input wire vreq_valid,input wire [13:0] vreq_t,
    output wire rsp_valid,output wire [1023:0] rsp_data,output wire [13:0] rsp_t,
    output wire rsp_v,output wire [15:0] rsp_epoch,output wire [5:0] rsp_layer,output wire fault
);
    wire [3:0] ckp = {ck_p3,ck_p2,ck_p1,ck_p0};
    wire [75:0] req_lo,req_hi;
    wire [77:0] rsp_lo,rsp_hi;
    wire [151:0] rq_lane;          // per lane request word as it reaches the lane
    wire [155:0] rs_lane;          // per lane response control word as the lane drives it
    wire [37:0] r0_b,r3_b;
    wire [38:0] s0_b,s3_b;
    wire [3:0] l_arm,l_rst;          // per lane: the registered strap / arm copies (lane 0 relay 0, 1/2 row, 3 relay 3)
    wire [63:0] l_epoch;wire [23:0] l_layer;wire [7:0] l_stack;wire [11:0] l_group;
    wire c_arm,c_rst;wire [15:0] c_epoch;wire [5:0] c_layer;wire [1:0] c_stack;wire [2:0] c_group;
    assign l_arm[2:1]={2{c_arm}};assign l_rst[2:1]={2{c_rst}};assign l_epoch[47:16]={2{c_epoch}};
    assign l_layer[17:6]={2{c_layer}};assign l_stack[5:2]={2{c_stack}};assign l_group[8:3]={2{c_group}};
    qkd_static_kv_landing_row u_row(
      .ck(ck),.rst_n(rst_n),.arm(arm),.epoch(epoch),.layer(layer),
      .req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),
      .vreq_valid(vreq_valid),.vreq_t(vreq_t),
      .rsp_valid(rsp_valid),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),.fault(fault),
      .req_lo(req_lo),.req_hi(req_hi),.rsp_lo(rsp_lo),.rsp_hi(rsp_hi),.cfg_stack(cfg_stack),.cfg_group(cfg_group),
      .arm_o(c_arm),.epoch_o(c_epoch),.layer_o(c_layer),.stack_o(c_stack),.group_o(c_group),.rst_o(c_rst));
    qkd_static_kv_landing_relay #(.MUT(HOP_MUT==2 ? 2 : 0)) u_rly0(.ck(ck_r0),.rst_n(rst_n),
      .req_a(req_lo[37:0]),.req_b(r0_b),.rsp_a(rs_lane[38:0]),.rsp_b(s0_b),
      .arm(arm),.epoch(epoch),.layer(layer),.cfg_stack(cfg_stack),.cfg_group(cfg_group),
      .arm_o(l_arm[0]),.epoch_o(l_epoch[15:0]),.layer_o(l_layer[5:0]),.stack_o(l_stack[1:0]),.group_o(l_group[2:0]),.rst_o(l_rst[0]));
    qkd_static_kv_landing_relay u_rly3(.ck(ck_r3),.rst_n(rst_n),
      .req_a(req_hi[75:38]),.req_b(r3_b),.rsp_a(rs_lane[155:117]),.rsp_b(s3_b),
      .arm(arm),.epoch(epoch),.layer(layer),.cfg_stack(cfg_stack),.cfg_group(cfg_group),
      .arm_o(l_arm[3]),.epoch_o(l_epoch[63:48]),.layer_o(l_layer[23:18]),.stack_o(l_stack[7:6]),.group_o(l_group[11:9]),.rst_o(l_rst[3]));
    assign rq_lane={r3_b,req_hi[37:0],req_lo[75:38],r0_b};
    assign rsp_lo={rs_lane[77:39],s0_b};
    assign rsp_hi={s3_b,rs_lane[116:78]};
    genvar q;
    generate for(q=0;q<4;q=q+1)begin:g_lane
      // HOP_MUT 1 (negative control, as the flat seg): branch 0's response hop flips a data bit
      qkd_static_kv_landing_lane #(.MUT(MUT),.HOP_MUT(HOP_MUT==1 && q==0))u_lane(
       .ck(ckp[q]),.rst_n(l_rst[q]),.cfg_stack(l_stack[2*q+:2]),.cfg_group(l_group[3*q+:3]),.arm(l_arm[q]),
       .epoch(l_epoch[16*q+:16]),.layer(l_layer[6*q+:6]),
       .expected_put(expected_put[q]),.expected_sector(expected_sector[10*q+:10]),
       .actual_valid(actual_valid[q]),.actual_sector(actual_sector[10*q+:10]),
       .actual_epoch(actual_epoch[16*q+:16]),.actual_layer(actual_layer[6*q+:6]),.actual_data(actual_data[256*q+:256]),
       .get(rq_lane[38*q]),.get_t(rq_lane[38*q+1+:14]),.get_v(rq_lane[38*q+15]),.get_epoch(rq_lane[38*q+16+:16]),
       .get_layer(rq_lane[38*q+32+:6]),
       .out_valid(rs_lane[39*q]),.out_t(rs_lane[39*q+1+:14]),.out_v(rs_lane[39*q+15]),.out_epoch(rs_lane[39*q+16+:16]),
       .out_layer(rs_lane[39*q+32+:6]),.fault(rs_lane[39*q+38]),
       .rsp_data(rsp_data[256*q+:256]));
    end endgenerate
endmodule
