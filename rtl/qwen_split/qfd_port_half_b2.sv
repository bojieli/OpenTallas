`timescale 1ns/1ps
// One physical source interface for six b2 halves; hb is a captured position strap.
// ROM_BAND/ROM_HALF name mask files for simulation only; synthesis uses physical macros.
// No inter-half packet or data/control forwarding. Native child stations retained.
module qfd_port_half_b2 #(parameter integer ROM_BAND=0, ROM_HALF=0) (
    input wire [2:0] hb,
    input wire ck,
    input wire ck_bw0,
    input wire ck_bw1,
    input wire ck_bw2,
    input wire ck_bw3,
    input wire ck_bw4,
    input wire ck_bw5,
    input wire ck_bw6,
    input wire ck_bw7,
    input wire ck_pair0,
    input wire ck_pair1,
    input wire ck_pair2,
    input wire ck_pair3,
    input wire ck_col0,
    input wire ck_col1,
    input wire ck_col2,
    input wire ck_col3,
    input wire ck_col4,
    input wire ck_col5,
    input wire ck_col6,
    input wire ck_col7,
    input wire ck_col8,
    input wire ck_col9,
    input wire ck_col10,
    input wire ck_col11,
    input wire ck_col12,
    input wire ck_col13,
    input wire ck_col14,
    input wire ck_col15,
    input wire ck_mul0,
    input wire ck_mul1,
    input wire ck_mul2,
    input wire ck_mul3,
    input wire ck_mul4,
    input wire ck_mul5,
    input wire ck_mul6,
    input wire ck_mul7,
    input wire ck_mul8,
    input wire ck_mul9,
    input wire ck_mul10,
    input wire ck_mul11,
    input wire ck_mul12,
    input wire ck_mul13,
    input wire ck_mul14,
    input wire ck_mul15,
    input wire ck_group0,ck_group1,ck_group2,ck_group3,
    input wire rst_n,
    input wire [513:0] bw0,
    input wire [513:0] bw1,
    input wire [513:0] bw2,
    input wire [513:0] bw3,
    input wire [513:0] bw4,
    input wire [513:0] bw5,
    input wire [513:0] bw6,
    input wire [513:0] bw7,
    input wire [340:0] tc,
    input wire [2047:0] ty,
    output wire [2212:0] rq,
    output wire [51:0] am,
    output wire [2049:0] cw0
);
    (* keep *) reg [2:0] hb_q;
    always @(posedge ck) hb_q<=hb;
    wire [2049:0] local_word;
    qfd_slab_word_half u_words (
        .ck(ck),.rst_n(rst_n),
        .ck_bw0(ck_bw0),.ck_bw1(ck_bw1),.ck_bw2(ck_bw2),.ck_bw3(ck_bw3),.ck_bw4(ck_bw4),.ck_bw5(ck_bw5),.ck_bw6(ck_bw6),.ck_bw7(ck_bw7),
        .ck_pair0(ck_pair0),.ck_pair1(ck_pair1),.ck_pair2(ck_pair2),.ck_pair3(ck_pair3),
        .bw({bw7,bw6,bw5,bw4,bw3,bw2,bw1,bw0}),.cw(local_word));
    wire [2212:0] local_result; wire [51:0] local_am;
    qfd_slab_result_half_b2 #(.ROM_BAND(ROM_BAND),.ROM_HALF(ROM_HALF)) u_results (
        .hb(hb_q),.ck(ck),.ck_group({ck_group3,ck_group2,ck_group1,ck_group0}),.rst_n(rst_n),.tc(tc),.ty(ty),
        .ck_col({ck_col15,ck_col14,ck_col13,ck_col12,ck_col11,ck_col10,ck_col9,ck_col8,ck_col7,ck_col6,ck_col5,ck_col4,ck_col3,ck_col2,ck_col1,ck_col0}),
        .ck_mul({ck_mul15,ck_mul14,ck_mul13,ck_mul12,ck_mul11,ck_mul10,ck_mul9,ck_mul8,ck_mul7,ck_mul6,ck_mul5,ck_mul4,ck_mul3,ck_mul2,ck_mul1,ck_mul0}),
        .rq(local_result),.am(local_am));
    // Preserve the native word faults formerly carried by the slab master.
    // cw0 valid/fault also leave intact for the central cross-half alignment checker.
    reg word_fault;
    reg [51:0] am_q;
    always @(posedge ck) begin
        if (!rst_n) begin word_fault<=0;am_q<=0;end
        else begin
            word_fault<=word_fault | local_word[2049] | (hb_q>=6);
            am_q<={local_am[51] | word_fault,local_am[50:0]};
        end
    end
    assign cw0=local_word; assign rq=local_result; assign am=am_q;
endmodule

