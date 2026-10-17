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
//     the 4-lane compare and the fault) plus the per-branch request hop38 and the 39-b control part of each response
//     hop295, with their branch reset flops.
// Every seam is register to register with the SAME registers as the flat seg, so this parent is cycle-identical to
// qkd_static_kv_landing_seg (latency 8 edges); bench tools/qwen_static_kv/run_landing_seg_h.sh = the flat bench with
// this parent as the DUT.  Clocks: one top clock port per hard-child clock pin (cluster entry rule): ck -> u_row,
// ck_p0..ck_p3 -> u_lane[0..3]; the die delivers each from its regional tree.
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
    qkd_static_kv_landing_pc #(.MUT(MUT),.VMAP(1),.FAULT_PIPE(1),.WRITE_PIPE(0),.CHECK_PIPE(1))u_pc(
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

module qkd_static_kv_landing_row #(parameter integer HOP_MUT=0)(
    input wire ck,input wire rst_n,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    input wire req_valid,input wire [13:0] req_t,input wire req_v,
    input wire [15:0] req_epoch,input wire [5:0] req_layer,
    input wire vreq_valid,input wire [13:0] vreq_t,
    output wire rsp_valid,output wire [13:0] rsp_t,
    output wire rsp_v,output wire [15:0] rsp_epoch,output wire [5:0] rsp_layer,output wire fault,
    // lane faces: request leaves the hop38 registers; response control lands on the hop (control part of hop295)
    output wire [3:0] get_d,output wire [55:0] gt_d,output wire [3:0] gv_d,output wire [63:0] ge_d,output wire [23:0] gl_d,
    input wire [3:0] ov,input wire [55:0] ot,input wire [3:0] vv,input wire [63:0] oe,
    input wire [23:0] ol,input wire [3:0] pf
);
    wire [3:0] get,gv;
    wire [55:0] gt;
    wire [63:0] ge;
    wire [23:0] gl;
    wire [3:0] ov_d,pf_d,vv_d;
    wire [55:0] ot_d;
    wire [63:0] oe_d;
    wire [23:0] ol_d;
    for(genvar branch=0;branch<4;branch=branch+1)begin:g_hop
      (* keep *) reg hrn;
      always @(posedge ck) hrn <= rst_n;
      qkd_static_kv_hop38 #(.MUT(HOP_MUT==2 && branch==0))u_req(
        .ck(ck),.rst_n(hrn),
        .a({gl[6*branch+:6],ge[16*branch+:16],gv[branch],gt[14*branch+:14],get[branch]}),
        .b({gl_d[6*branch+:6],ge_d[16*branch+:16],gv_d[branch],gt_d[14*branch+:14],get_d[branch]}));
      qkd_static_kv_hop #(.W(39))u_rsp(
        .ck(ck),.rst_n(hrn),
        .a({pf[branch],ol[6*branch+:6],oe[16*branch+:16],vv[branch],ot[14*branch+:14],ov[branch]}),
        .b({pf_d[branch],ol_d[6*branch+:6],oe_d[16*branch+:16],vv_d[branch],ot_d[14*branch+:14],ov_d[branch]}));
    end
    qkd_static_kv_rowctl #(.VREQ(1),.DATA(0)) u_rowctl(
      .ck(ck),.rst_n(rst_n),.req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),
      .vreq_valid(vreq_valid),.vreq_t(vreq_t),.arm(arm),.epoch(epoch),.layer(layer),
      .pc_get(get),.pc_get_t(gt),.pc_get_v(gv),.pc_get_epoch(ge),.pc_get_layer(gl),
      .pc_valid(ov_d),.pc_data(1024'd0),.pc_t(ot_d),.pc_v(vv_d),.pc_epoch(oe_d),.pc_layer(ol_d),.pc_fault(pf_d),
      .rsp_valid(rsp_valid),.rsp_data(),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),.fault(fault));
endmodule

// Wires-only parent: the data ports of qkd_static_kv_landing_seg + one clock entry per lane.
module qkd_static_kv_landing_seg_h #(
    parameter integer MUT=0,HOP_MUT=0
)(
    input wire ck,input wire ck_p0,input wire ck_p1,input wire ck_p2,input wire ck_p3,input wire rst_n,
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
    wire [3:0] get_d,gv_d,ov,pf,vv;
    wire [55:0] gt_d,ot;
    wire [63:0] ge_d,oe;
    wire [23:0] gl_d,ol;
    wire [3:0] ckp = {ck_p3,ck_p2,ck_p1,ck_p0};
    qkd_static_kv_landing_row #(.HOP_MUT(HOP_MUT==2 ? 2 : 0)) u_row(
      .ck(ck),.rst_n(rst_n),.arm(arm),.epoch(epoch),.layer(layer),
      .req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),
      .vreq_valid(vreq_valid),.vreq_t(vreq_t),
      .rsp_valid(rsp_valid),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),.fault(fault),
      .get_d(get_d),.gt_d(gt_d),.gv_d(gv_d),.ge_d(ge_d),.gl_d(gl_d),
      .ov(ov),.ot(ot),.vv(vv),.oe(oe),.ol(ol),.pf(pf));
    genvar q;
    generate for(q=0;q<4;q=q+1)begin:g_lane
      // HOP_MUT 1 (negative control, as the flat seg): branch 0's response hop flips a data bit
      qkd_static_kv_landing_lane #(.MUT(MUT),.HOP_MUT(HOP_MUT==1 && q==0))u_lane(
       .ck(ckp[q]),.rst_n(rst_n),.cfg_stack(cfg_stack),.cfg_group(cfg_group),.arm(arm),.epoch(epoch),.layer(layer),
       .expected_put(expected_put[q]),.expected_sector(expected_sector[10*q+:10]),
       .actual_valid(actual_valid[q]),.actual_sector(actual_sector[10*q+:10]),
       .actual_epoch(actual_epoch[16*q+:16]),.actual_layer(actual_layer[6*q+:6]),.actual_data(actual_data[256*q+:256]),
       .get(get_d[q]),.get_t(gt_d[14*q+:14]),.get_v(gv_d[q]),.get_epoch(ge_d[16*q+:16]),.get_layer(gl_d[6*q+:6]),
       .out_valid(ov[q]),.out_t(ot[14*q+:14]),.out_v(vv[q]),.out_epoch(oe[16*q+:16]),.out_layer(ol[6*q+:6]),.fault(pf[q]),
       .rsp_data(rsp_data[256*q+:256]));
    end endgenerate
endmodule
