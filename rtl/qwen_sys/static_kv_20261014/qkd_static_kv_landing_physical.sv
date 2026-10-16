`timescale 1ns/1fs
// Real balanced physical branch stages. Logical5 +request1 +return1 =7coreedges.
// Compiler metadata/actual-return producers, native clocks/views remain mandatory.
module qkd_static_kv_landing_physical_grp #(
    parameter integer STACK=0,GROUP=0,MUT=0,HOP_MUT=0
)(
    input wire ck,input wire [3:0] ck_pc,input wire [3:0] ck_req_rly,ck_rsp_rly,input wire rst_n,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    input wire [3:0] expected_put,input wire [39:0] expected_sector,
    input wire [3:0] actual_valid,input wire [39:0] actual_sector,
    input wire [63:0] actual_epoch,input wire [23:0] actual_layer,input wire [1023:0] actual_data,
    input wire req_valid,input wire [13:0] req_t,input wire req_v,
    input wire [15:0] req_epoch,input wire [5:0] req_layer,
    output wire rsp_valid,output wire [1023:0] rsp_data,output wire [13:0] rsp_t,
    output wire rsp_v,output wire [15:0] rsp_epoch,output wire [5:0] rsp_layer,output wire fault
);
    wire [3:0] get,gv,ov,pf,vv;
    wire [55:0] gt,ot;
    wire [63:0] ge,oe;
    wire [23:0] gl,ol;
    wire [1023:0] od;

    wire [3:0] get_d,gv_d,ov_d,pf_d,vv_d;
    wire [55:0] gt_d,ot_d;
    wire [63:0] ge_d,oe_d;
    wire [23:0] gl_d,ol_d;
    wire [1023:0] od_d;
    for(genvar branch=0;branch<4;branch=branch+1)begin:g_hop
      qkd_static_kv_hop38 #(.MUT(HOP_MUT==2 && branch==0))u_req(
        .ck(ck_req_rly[branch]),.rst_n(rst_n),
        .a({gl[6*branch+:6],ge[16*branch+:16],gv[branch],gt[14*branch+:14],get[branch]}),
        .b({gl_d[6*branch+:6],ge_d[16*branch+:16],gv_d[branch],gt_d[14*branch+:14],get_d[branch]}));
      qkd_static_kv_hop295 #(.MUT(HOP_MUT==1 && branch==0))u_rsp(
        .ck(ck_rsp_rly[branch]),.rst_n(rst_n),
        .a({pf[branch],ol[6*branch+:6],oe[16*branch+:16],vv[branch],ot[14*branch+:14],od[256*branch+:256],ov[branch]}),
        .b({pf_d[branch],ol_d[6*branch+:6],oe_d[16*branch+:16],vv_d[branch],ot_d[14*branch+:14],od_d[256*branch+:256],ov_d[branch]}));
    end
    qkd_static_kv_rowctl u_rowctl(
      .ck(ck),.rst_n(rst_n),.req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),
      .pc_get(get),.pc_get_t(gt),.pc_get_v(gv),.pc_get_epoch(ge),.pc_get_layer(gl),
      .pc_valid(ov_d),.pc_data(od_d),.pc_t(ot_d),.pc_v(vv_d),.pc_epoch(oe_d),.pc_layer(ol_d),.pc_fault(pf_d),
      .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),.fault(fault));
    genvar q;
    generate for(q=0;q<4;q=q+1)begin:g_pc
      qkd_static_kv_landing_pc #(.MUT(MUT))u_pc(
       .ck(ck_pc[q]),.rst_n(rst_n),.cfg_stack(2'(STACK)),.cfg_group(3'(GROUP)),.arm(arm),.epoch(epoch),.layer(layer),
       .expected_put(expected_put[q]),.expected_sector(expected_sector[10*q+:10]),
       .actual_valid(actual_valid[q]),.actual_sector(actual_sector[10*q+:10]),
       .actual_epoch(actual_epoch[16*q+:16]),.actual_layer(actual_layer[6*q+:6]),.actual_data(actual_data[256*q+:256]),
       .get(get_d[q]),.get_t(gt_d[14*q+:14]),.get_v(gv_d[q]),.get_epoch(ge_d[16*q+:16]),.get_layer(gl_d[6*q+:6]),
       .out_valid(ov[q]),.out_data(od[256*q+:256]),.out_t(ot[14*q+:14]),
       .out_v(vv[q]),.out_epoch(oe[16*q+:16]),.out_layer(ol[6*q+:6]),.fault(pf[q]));
    end endgenerate
endmodule
