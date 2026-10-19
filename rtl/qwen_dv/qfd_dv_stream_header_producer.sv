// PRIVATE GENERATED HEADER COMPONENT. Not a parent/consumer adoption.
// Model edaa82b7a: zero new data edges,201 FFs excluding parent reset forests.
`default_nettype none
module qfd_dv_stream_header_producer (
    input wire ck,
    input wire [4:0] rst_read,
    input wire [6:0] rst_capture,
    input wire [4*1088-1:0] sw_bank,se_bank,
    input wire [11:0] sw_epo,se_epo,
    input wire [4*46-1:0] sw_vld,se_vld,
    output wire [95:0] sw_i_copies,
    output wire [49:0] se_i_copies
);
    wire [3:0] sw_bit1087_pre;
    ot_pl_land_field_copies #(.COPIES(4),.D(4),.K(2)) u_pre0(
        .ck(ck),.rsi(rst_read[0]),.bank({sw_bank[4351],sw_bank[3263],sw_bank[2175],sw_bank[1087]}),.epo(sw_epo),
        .vld(sw_vld[180+:4]),.o(sw_bit1087_pre));
    wire [0:0] sw_bit1084_pre;
    ot_pl_land_field_copies #(.COPIES(1),.D(4),.K(2)) u_pre1(
        .ck(ck),.rsi(rst_read[1]),.bank({sw_bank[4348],sw_bank[3260],sw_bank[2172],sw_bank[1084]}),.epo(sw_epo),
        .vld(sw_vld[180+:4]),.o(sw_bit1084_pre));
    wire [0:0] sw_bit1085_pre;
    ot_pl_land_field_copies #(.COPIES(1),.D(4),.K(2)) u_pre2(
        .ck(ck),.rsi(rst_read[2]),.bank({sw_bank[4349],sw_bank[3261],sw_bank[2173],sw_bank[1085]}),.epo(sw_epo),
        .vld(sw_vld[180+:4]),.o(sw_bit1085_pre));
    wire [0:0] sw_bit1086_pre;
    ot_pl_land_field_copies #(.COPIES(1),.D(4),.K(2)) u_pre3(
        .ck(ck),.rsi(rst_read[3]),.bank({sw_bank[4350],sw_bank[3262],sw_bank[2174],sw_bank[1086]}),.epo(sw_epo),
        .vld(sw_vld[180+:4]),.o(sw_bit1086_pre));
    wire [2:0] se_bit1087_pre;
    ot_pl_land_field_copies #(.COPIES(3),.D(4),.K(2)) u_pre4(
        .ck(ck),.rsi(rst_read[4]),.bank({se_bank[4351],se_bank[3263],se_bank[2175],se_bank[1087]}),.epo(se_epo),
        .vld(se_vld[180+:4]),.o(se_bit1087_pre));
    qfd_dv_header_capture_group #(.W(24),.ID(0)) u_capture0(
        .ck(ck),.rst_n(rst_capture[0]),.d({sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1086_pre[0],sw_bit1086_pre[0],sw_bit1085_pre[0],sw_bit1085_pre[0],sw_bit1084_pre[0],sw_bit1084_pre[0]}),.q(sw_i_copies[0+:24]));
    qfd_dv_header_capture_group #(.W(24),.ID(1)) u_capture1(
        .ck(ck),.rst_n(rst_capture[1]),.d({sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2]}),.q(sw_i_copies[24+:24]));
    qfd_dv_header_capture_group #(.W(24),.ID(2)) u_capture2(
        .ck(ck),.rst_n(rst_capture[2]),.d({sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2]}),.q(sw_i_copies[48+:24]));
    qfd_dv_header_capture_group #(.W(24),.ID(3)) u_capture3(
        .ck(ck),.rst_n(rst_capture[3]),.d({sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2],sw_bit1087_pre[1],sw_bit1087_pre[0],sw_bit1087_pre[3],sw_bit1087_pre[2]}),.q(sw_i_copies[72+:24]));
    qfd_dv_header_capture_group #(.W(24),.ID(4)) u_capture4(
        .ck(ck),.rst_n(rst_capture[4]),.d({se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0]}),.q(se_i_copies[0+:24]));
    qfd_dv_header_capture_group #(.W(24),.ID(5)) u_capture5(
        .ck(ck),.rst_n(rst_capture[5]),.d({se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0],se_bit1087_pre[2],se_bit1087_pre[1],se_bit1087_pre[0]}),.q(se_i_copies[24+:24]));
    qfd_dv_header_capture_group #(.W(2),.ID(6)) u_capture6(
        .ck(ck),.rst_n(rst_capture[6]),.d({se_bit1087_pre[1],se_bit1087_pre[0]}),.q(se_i_copies[48+:2]));
endmodule
(* keep_hierarchy="yes" *)
module qfd_dv_header_capture_group #(parameter integer W=24,ID=0)(
    input wire ck,rst_n,input wire [W-1:0] d,output wire [W-1:0] q
);
    generate for(genvar b=0;b<W;b=b+1) begin:g_bit
        (* keep_hierarchy="yes" *) qfd_dv_header_capture_bit #(.ID(ID*24+b)) u_bit(
            .ck(ck),.rst_n(rst_n),.d(d[b]),.q(q[b]));
    end
    if(W<1||W>24) begin:g_invalid
        QFD_HEADER_CAPTURE_GROUP_REQUIRES1_TO24 u_bad();
    end endgenerate
endmodule
(* keep_hierarchy="yes" *)
module qfd_dv_header_capture_bit #(parameter integer ID=0)(
    input wire ck,rst_n,d,output wire q
);
    (* keep=1 *) reg value;
    always @(posedge ck or negedge rst_n) if(!rst_n)value<=0;else value<=d;
    assign q=value;
endmodule
`default_nettype wire
