`timescale 1ns/1ps
// Real static TP8 slab masters. Clock entries drive their named physical children.
// Phase/cost qualification requires compiler padding for the actual routed links.

module qfd_port_tiles_0 (
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
    input wire [2049:0] cf1,
    input wire [4095:0] ty,
    input wire [2212:0] rqe,
    input wire [51:0] ame,
    output wire [340:0] tc_e,
    output wire [2047:0] tye,
    output wire [4095:0] tw,
    output wire [4424:0] rq,
    output wire [103:0] tf
);
    wire [2049:0] local_word;
    qfd_slab_word_half u_words (
        .ck(ck),.rst_n(rst_n),
        .ck_bw0(ck_bw0),.ck_bw1(ck_bw1),.ck_bw2(ck_bw2),.ck_bw3(ck_bw3),.ck_bw4(ck_bw4),.ck_bw5(ck_bw5),.ck_bw6(ck_bw6),.ck_bw7(ck_bw7),
        .ck_pair0(ck_pair0),.ck_pair1(ck_pair1),.ck_pair2(ck_pair2),.ck_pair3(ck_pair3),
        .bw({bw7,bw6,bw5,bw4,bw3,bw2,bw1,bw0}),.cw(local_word));
    wire [2212:0] local_result; wire [51:0] local_am;
    qfd_slab_result_half #(.BAND(0),.HALF(0)) u_results (
        .ck(ck),.ck_group({ck_group3,ck_group2,ck_group1,ck_group0}),.rst_n(rst_n),.tc(tc_copy),.ty(ty_local),
        .ck_col({ck_col15,ck_col14,ck_col13,ck_col12,ck_col11,ck_col10,ck_col9,ck_col8,ck_col7,ck_col6,ck_col5,ck_col4,ck_col3,ck_col2,ck_col1,ck_col0}),
        .ck_mul({ck_mul15,ck_mul14,ck_mul13,ck_mul12,ck_mul11,ck_mul10,ck_mul9,ck_mul8,ck_mul7,ck_mul6,ck_mul5,ck_mul4,ck_mul3,ck_mul2,ck_mul1,ck_mul0}),
        .rq(local_result),.am(local_am));
    (* keep *) reg [340:0] tc_copy;
    (* keep *) reg [2047:0] ty_copy,ty_local;
    (* keep *) reg [4095:0] tw_q;
    (* keep *) reg [4424:0] rq_q;
    (* keep *) reg [103:0] tf_q;
    reg align_fault;
    always @(posedge ck) begin
        tc_copy <= tc; ty_copy <= ty[4095:2048]; ty_local <= ty[2047:0];
        tw_q <= {cf1[2047:0],local_word[2047:0]};
        rq_q[2207:0] <= local_result[2207:0];
        rq_q[4415:2208] <= rqe[2207:0];
        rq_q[4423:4416] <= rst_n ? {rqe[2211:2208],local_result[2211:2208]} : 8'd0;
        rq_q[4424] <= rst_n & (rqe[2212] | local_result[2212]);
        if(!rst_n) begin align_fault<=1'b0; tf_q<=104'd0; end
        else begin
            align_fault <= align_fault | (cf1[2048] ^ local_word[2048])
                | (rqe[2212] ^ local_result[2212]) | cf1[2049] | local_word[2049];
            tf_q <= {ame[51] | align_fault,local_am[51] | align_fault,ame[50:0],local_am[50:0]};
        end
    end
    assign tc_e=tc_copy; assign tye=ty_copy; assign tw=tw_q; assign rq=rq_q; assign tf=tf_q;
endmodule

module qfd_port_tiles_0_f1 (
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
    input wire [513:0] bw8,
    input wire [513:0] bw9,
    input wire [513:0] bw10,
    input wire [513:0] bw11,
    input wire [513:0] bw12,
    input wire [513:0] bw13,
    input wire [513:0] bw14,
    input wire [513:0] bw15,
    input wire [340:0] tc,
    input wire [2047:0] ty,
    output wire [2212:0] rq,
    output wire [51:0] am,
    output wire [2049:0] cw0
);
    wire [2049:0] local_word;
    qfd_slab_word_half u_words (
        .ck(ck),.rst_n(rst_n),
        .ck_bw0(ck_bw0),.ck_bw1(ck_bw1),.ck_bw2(ck_bw2),.ck_bw3(ck_bw3),.ck_bw4(ck_bw4),.ck_bw5(ck_bw5),.ck_bw6(ck_bw6),.ck_bw7(ck_bw7),
        .ck_pair0(ck_pair0),.ck_pair1(ck_pair1),.ck_pair2(ck_pair2),.ck_pair3(ck_pair3),
        .bw({bw15,bw14,bw13,bw12,bw11,bw10,bw9,bw8}),.cw(local_word));
    wire [2212:0] local_result; wire [51:0] local_am;
    qfd_slab_result_half #(.BAND(0),.HALF(1)) u_results (
        .ck(ck),.ck_group({ck_group3,ck_group2,ck_group1,ck_group0}),.rst_n(rst_n),.tc(tc),.ty(ty),
        .ck_col({ck_col15,ck_col14,ck_col13,ck_col12,ck_col11,ck_col10,ck_col9,ck_col8,ck_col7,ck_col6,ck_col5,ck_col4,ck_col3,ck_col2,ck_col1,ck_col0}),
        .ck_mul({ck_mul15,ck_mul14,ck_mul13,ck_mul12,ck_mul11,ck_mul10,ck_mul9,ck_mul8,ck_mul7,ck_mul6,ck_mul5,ck_mul4,ck_mul3,ck_mul2,ck_mul1,ck_mul0}),
        .rq(local_result),.am(local_am));
    assign cw0=local_word; assign rq=local_result; assign am=local_am;
endmodule

module qfd_port_tiles_1 (
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
    input wire [2049:0] cf1,
    input wire [4095:0] ty,
    input wire [2212:0] rqe,
    input wire [51:0] ame,
    output wire [340:0] tc_e,
    output wire [2047:0] tye,
    output wire [4095:0] tw,
    output wire [4424:0] rq,
    output wire [103:0] tf
);
    wire [2049:0] local_word;
    qfd_slab_word_half u_words (
        .ck(ck),.rst_n(rst_n),
        .ck_bw0(ck_bw0),.ck_bw1(ck_bw1),.ck_bw2(ck_bw2),.ck_bw3(ck_bw3),.ck_bw4(ck_bw4),.ck_bw5(ck_bw5),.ck_bw6(ck_bw6),.ck_bw7(ck_bw7),
        .ck_pair0(ck_pair0),.ck_pair1(ck_pair1),.ck_pair2(ck_pair2),.ck_pair3(ck_pair3),
        .bw({bw7,bw6,bw5,bw4,bw3,bw2,bw1,bw0}),.cw(local_word));
    wire [2212:0] local_result; wire [51:0] local_am;
    qfd_slab_result_half #(.BAND(1),.HALF(0)) u_results (
        .ck(ck),.ck_group({ck_group3,ck_group2,ck_group1,ck_group0}),.rst_n(rst_n),.tc(tc_copy),.ty(ty_local),
        .ck_col({ck_col15,ck_col14,ck_col13,ck_col12,ck_col11,ck_col10,ck_col9,ck_col8,ck_col7,ck_col6,ck_col5,ck_col4,ck_col3,ck_col2,ck_col1,ck_col0}),
        .ck_mul({ck_mul15,ck_mul14,ck_mul13,ck_mul12,ck_mul11,ck_mul10,ck_mul9,ck_mul8,ck_mul7,ck_mul6,ck_mul5,ck_mul4,ck_mul3,ck_mul2,ck_mul1,ck_mul0}),
        .rq(local_result),.am(local_am));
    (* keep *) reg [340:0] tc_copy;
    (* keep *) reg [2047:0] ty_copy,ty_local;
    (* keep *) reg [4095:0] tw_q;
    (* keep *) reg [4424:0] rq_q;
    (* keep *) reg [103:0] tf_q;
    reg align_fault;
    always @(posedge ck) begin
        tc_copy <= tc; ty_copy <= ty[4095:2048]; ty_local <= ty[2047:0];
        tw_q <= {cf1[2047:0],local_word[2047:0]};
        rq_q[2207:0] <= local_result[2207:0];
        rq_q[4415:2208] <= rqe[2207:0];
        rq_q[4423:4416] <= rst_n ? {rqe[2211:2208],local_result[2211:2208]} : 8'd0;
        rq_q[4424] <= rst_n & (rqe[2212] | local_result[2212]);
        if(!rst_n) begin align_fault<=1'b0; tf_q<=104'd0; end
        else begin
            align_fault <= align_fault | (cf1[2048] ^ local_word[2048])
                | (rqe[2212] ^ local_result[2212]) | cf1[2049] | local_word[2049];
            tf_q <= {ame[51] | align_fault,local_am[51] | align_fault,ame[50:0],local_am[50:0]};
        end
    end
    assign tc_e=tc_copy; assign tye=ty_copy; assign tw=tw_q; assign rq=rq_q; assign tf=tf_q;
endmodule

module qfd_port_tiles_1_f1 (
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
    input wire [513:0] bw8,
    input wire [513:0] bw9,
    input wire [513:0] bw10,
    input wire [513:0] bw11,
    input wire [513:0] bw12,
    input wire [513:0] bw13,
    input wire [513:0] bw14,
    input wire [513:0] bw15,
    input wire [340:0] tc,
    input wire [2047:0] ty,
    output wire [2212:0] rq,
    output wire [51:0] am,
    output wire [2049:0] cw1
);
    wire [2049:0] local_word;
    qfd_slab_word_half u_words (
        .ck(ck),.rst_n(rst_n),
        .ck_bw0(ck_bw0),.ck_bw1(ck_bw1),.ck_bw2(ck_bw2),.ck_bw3(ck_bw3),.ck_bw4(ck_bw4),.ck_bw5(ck_bw5),.ck_bw6(ck_bw6),.ck_bw7(ck_bw7),
        .ck_pair0(ck_pair0),.ck_pair1(ck_pair1),.ck_pair2(ck_pair2),.ck_pair3(ck_pair3),
        .bw({bw15,bw14,bw13,bw12,bw11,bw10,bw9,bw8}),.cw(local_word));
    wire [2212:0] local_result; wire [51:0] local_am;
    qfd_slab_result_half #(.BAND(1),.HALF(1)) u_results (
        .ck(ck),.ck_group({ck_group3,ck_group2,ck_group1,ck_group0}),.rst_n(rst_n),.tc(tc),.ty(ty),
        .ck_col({ck_col15,ck_col14,ck_col13,ck_col12,ck_col11,ck_col10,ck_col9,ck_col8,ck_col7,ck_col6,ck_col5,ck_col4,ck_col3,ck_col2,ck_col1,ck_col0}),
        .ck_mul({ck_mul15,ck_mul14,ck_mul13,ck_mul12,ck_mul11,ck_mul10,ck_mul9,ck_mul8,ck_mul7,ck_mul6,ck_mul5,ck_mul4,ck_mul3,ck_mul2,ck_mul1,ck_mul0}),
        .rq(local_result),.am(local_am));
    assign cw1=local_word; assign rq=local_result; assign am=local_am;
endmodule

module qfd_port_tiles_2 (
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
    input wire [2049:0] cf1,
    input wire [4095:0] ty,
    input wire [2212:0] rqe,
    input wire [51:0] ame,
    output wire [340:0] tc_e,
    output wire [2047:0] tye,
    output wire [4095:0] tw,
    output wire [4424:0] rq,
    output wire [103:0] tf
);
    wire [2049:0] local_word;
    qfd_slab_word_half u_words (
        .ck(ck),.rst_n(rst_n),
        .ck_bw0(ck_bw0),.ck_bw1(ck_bw1),.ck_bw2(ck_bw2),.ck_bw3(ck_bw3),.ck_bw4(ck_bw4),.ck_bw5(ck_bw5),.ck_bw6(ck_bw6),.ck_bw7(ck_bw7),
        .ck_pair0(ck_pair0),.ck_pair1(ck_pair1),.ck_pair2(ck_pair2),.ck_pair3(ck_pair3),
        .bw({bw7,bw6,bw5,bw4,bw3,bw2,bw1,bw0}),.cw(local_word));
    wire [2212:0] local_result; wire [51:0] local_am;
    qfd_slab_result_half #(.BAND(2),.HALF(0)) u_results (
        .ck(ck),.ck_group({ck_group3,ck_group2,ck_group1,ck_group0}),.rst_n(rst_n),.tc(tc_copy),.ty(ty_local),
        .ck_col({ck_col15,ck_col14,ck_col13,ck_col12,ck_col11,ck_col10,ck_col9,ck_col8,ck_col7,ck_col6,ck_col5,ck_col4,ck_col3,ck_col2,ck_col1,ck_col0}),
        .ck_mul({ck_mul15,ck_mul14,ck_mul13,ck_mul12,ck_mul11,ck_mul10,ck_mul9,ck_mul8,ck_mul7,ck_mul6,ck_mul5,ck_mul4,ck_mul3,ck_mul2,ck_mul1,ck_mul0}),
        .rq(local_result),.am(local_am));
    (* keep *) reg [340:0] tc_copy;
    (* keep *) reg [2047:0] ty_copy,ty_local;
    (* keep *) reg [4095:0] tw_q;
    (* keep *) reg [4424:0] rq_q;
    (* keep *) reg [103:0] tf_q;
    reg align_fault;
    always @(posedge ck) begin
        tc_copy <= tc; ty_copy <= ty[4095:2048]; ty_local <= ty[2047:0];
        tw_q <= {cf1[2047:0],local_word[2047:0]};
        rq_q[2207:0] <= local_result[2207:0];
        rq_q[4415:2208] <= rqe[2207:0];
        rq_q[4423:4416] <= rst_n ? {rqe[2211:2208],local_result[2211:2208]} : 8'd0;
        rq_q[4424] <= rst_n & (rqe[2212] | local_result[2212]);
        if(!rst_n) begin align_fault<=1'b0; tf_q<=104'd0; end
        else begin
            align_fault <= align_fault | (cf1[2048] ^ local_word[2048])
                | (rqe[2212] ^ local_result[2212]) | cf1[2049] | local_word[2049];
            tf_q <= {ame[51] | align_fault,local_am[51] | align_fault,ame[50:0],local_am[50:0]};
        end
    end
    assign tc_e=tc_copy; assign tye=ty_copy; assign tw=tw_q; assign rq=rq_q; assign tf=tf_q;
endmodule

module qfd_port_tiles_2_f1 (
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
    input wire [513:0] bw8,
    input wire [513:0] bw9,
    input wire [513:0] bw10,
    input wire [513:0] bw11,
    input wire [513:0] bw12,
    input wire [513:0] bw13,
    input wire [513:0] bw14,
    input wire [513:0] bw15,
    input wire [340:0] tc,
    input wire [2047:0] ty,
    output wire [2212:0] rq,
    output wire [51:0] am,
    output wire [2049:0] cw2
);
    wire [2049:0] local_word;
    qfd_slab_word_half u_words (
        .ck(ck),.rst_n(rst_n),
        .ck_bw0(ck_bw0),.ck_bw1(ck_bw1),.ck_bw2(ck_bw2),.ck_bw3(ck_bw3),.ck_bw4(ck_bw4),.ck_bw5(ck_bw5),.ck_bw6(ck_bw6),.ck_bw7(ck_bw7),
        .ck_pair0(ck_pair0),.ck_pair1(ck_pair1),.ck_pair2(ck_pair2),.ck_pair3(ck_pair3),
        .bw({bw15,bw14,bw13,bw12,bw11,bw10,bw9,bw8}),.cw(local_word));
    wire [2212:0] local_result; wire [51:0] local_am;
    qfd_slab_result_half #(.BAND(2),.HALF(1)) u_results (
        .ck(ck),.ck_group({ck_group3,ck_group2,ck_group1,ck_group0}),.rst_n(rst_n),.tc(tc),.ty(ty),
        .ck_col({ck_col15,ck_col14,ck_col13,ck_col12,ck_col11,ck_col10,ck_col9,ck_col8,ck_col7,ck_col6,ck_col5,ck_col4,ck_col3,ck_col2,ck_col1,ck_col0}),
        .ck_mul({ck_mul15,ck_mul14,ck_mul13,ck_mul12,ck_mul11,ck_mul10,ck_mul9,ck_mul8,ck_mul7,ck_mul6,ck_mul5,ck_mul4,ck_mul3,ck_mul2,ck_mul1,ck_mul0}),
        .rq(local_result),.am(local_am));
    assign cw2=local_word; assign rq=local_result; assign am=local_am;
endmodule
