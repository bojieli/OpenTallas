// UNSELECTED five-root physical candidate. H1 forwarding remains one edge;
// bank EP2/ED3 and return skew remain unchanged. Two output-only roots each
// own 14 real request ports, distinct raw-epoch final reset conditioners.
// Functional benches tie all roots. Physical phase/slot/export remain OPEN.
`ifdef OT_SPVM_RESET_ACK
`include "dsfd_vm_reset_ack.svh"
`endif
module dsfd_vm_bgl28_mc5 (
    input wire ck, input wire ck_req, input wire ck_ret, input wire ck_fwd0, input wire ck_fwd1, input wire [0:0] rs, input wire [1:0] grp, input wire [2:0] bi,
    input  wire [27:0] i_v, input wire [27:0] i_we, input wire [28*14-1:0] i_row, input wire [28*4-1:0] i_mask,
    input  wire [28*128-1:0] i_d,
    output wire [27:0] f_v, output wire [27:0] f_we, output wire [28*14-1:0] f_row, output wire [28*4-1:0] f_mask,
    output wire [28*128-1:0] f_d,
    input  wire [9:0] r_v, input wire [10*128-1:0] r_d, input wire [3:0] r_f, input wire [2:0] r_o,
    output wire [9:0] o_v, output wire [10*128-1:0] o_d, output wire [3:0] o_f, output wire [2:0] o_o
`ifdef OT_SPVM_RESET_ACK
    ,output wire [4:0] reset_ack
`endif
);
`ifdef OT_VMBGL_FLOPMEM
    localparam integer MACRO = 0;
`else
    localparam integer MACRO = 1;
`endif
`ifdef OT_VMBGL_MUT_RELAY
    localparam integer PIN_HOP1=0;
`else
    localparam integer PIN_HOP1=1;
`endif
    wire [27:0] cf_v,cf_we;
    wire [28*14-1:0] cf_row;
    wire [28*4-1:0] cf_m;
    wire [28*128-1:0] cf_d;
    wire [1:0] out_clk={ck_fwd1,ck_fwd0};
    wire [1:0] out_release;
    genvar g;
    generate for(g=0;g<2;g=g+1) begin:g_output_reset
        (* keep=1,dont_touch=1 *) reg [1:0] rst_out_b;
        always @(posedge out_clk[g] or negedge rs[0])
            if(!rs[0]) rst_out_b<=2'b11;
            else rst_out_b<={rst_out_b[0],1'b0};
        assign out_release[g]=~rst_out_b[1];
`ifdef OT_SPVM_RESET_ACK
        dsfd_vm_reset_ack u_ack (.clk(out_clk[g]),.request_n(rs[0]),
            .local_release(out_release[g]),.consumer_live(out_release[g]),.ack(reset_ack[3+g]));
`endif
    end endgenerate
    generate begin:g_pin_copy
        (* keep=1,dont_touch=1 *) reg [27:0] qb_v,qb_we;
        (* keep=1,dont_touch=1 *) reg [28*14-1:0] qb_row;
        (* keep=1,dont_touch=1 *) reg [28*4-1:0] qb_m;
        (* keep=1,dont_touch=1 *) reg [28*128-1:0] qb_d;
        for(g=0;g<28;g=g+1) begin:g_port
            localparam integer DOMAIN=(g<14)?0:1;
            // Parallel to bank rb0: no added forwarding or return cycle.
            always @(posedge out_clk[DOMAIN] or negedge out_release[DOMAIN])
                if(!out_release[DOMAIN]) qb_v[g]<=1'b1;
                else qb_v[g]<=~(PIN_HOP1 ? i_v[g] : cf_v[g]);
            always @(posedge out_clk[DOMAIN]) begin
                qb_we[g]<=~(PIN_HOP1 ? i_we[g] : cf_we[g]);
                qb_row[g*14+:14]<=~(PIN_HOP1 ? i_row[g*14+:14] : cf_row[g*14+:14]);
                qb_m[g*4+:4]<=~(PIN_HOP1 ? i_mask[g*4+:4] : cf_m[g*4+:4]);
                qb_d[g*128+:128]<=~(PIN_HOP1 ? i_d[g*128+:128] : cf_d[g*128+:128]);
            end
        end
        assign f_v=~qb_v;assign f_we=~qb_we;assign f_row=~qb_row;
        assign f_mask=~qb_m;assign f_d=~qb_d;
    end endgenerate
    dsfd_vm_bgl #(.NP(28),.NPR(10),.NB(32),.NBL(8),.QD(4),.RQ(8),.MACRO(MACRO),.DW(128),
        .CLOCK_SPLIT(1),.PREHIT(1),.FAST4(1),.FORWARD_HOP(1),.PIN_OUTPUT_COPY(1),
        .FORWARD_PIN_OUTPUT_COPY(0),.RESET_FANOUT_SPLIT(1)) u (
        .ck(ck),.ck_req(ck_req),.ck_ret(ck_ret),.rs(rs),.grp(grp),.bi(bi),
        .i_v(i_v),.i_we(i_we),.i_row(i_row),.i_mask(i_mask),.i_d(i_d),
        .f_v(cf_v),.f_we(cf_we),.f_row(cf_row),.f_mask(cf_m),.f_d(cf_d),
        .r_v(r_v),.r_d(r_d),.r_f(r_f),.r_o(r_o),.o_v(o_v),.o_d(o_d),.o_f(o_f),.o_o(o_o)
`ifdef OT_SPVM_RESET_ACK
        ,.reset_ack(reset_ack[2:0])
`endif
    );
endmodule

// Fixed unconditional no-ACK physical intake interface.
module dsfd_vm_bgl28_mc5_h1pc (
    input wire ck, input wire ck_req, input wire ck_ret, input wire ck_fwd0, input wire ck_fwd1, input wire [0:0] rs, input wire [1:0] grp, input wire [2:0] bi,
    input  wire [27:0] i_v, input wire [27:0] i_we, input wire [28*14-1:0] i_row, input wire [28*4-1:0] i_mask,
    input  wire [28*128-1:0] i_d,
    output wire [27:0] f_v, output wire [27:0] f_we, output wire [28*14-1:0] f_row, output wire [28*4-1:0] f_mask,
    output wire [28*128-1:0] f_d,
    input  wire [9:0] r_v, input wire [10*128-1:0] r_d, input wire [3:0] r_f, input wire [2:0] r_o,
    output wire [9:0] o_v, output wire [10*128-1:0] o_d, output wire [3:0] o_f, output wire [2:0] o_o
);
    dsfd_vm_bgl28_mc5 u_leaf (
        .ck(ck),
        .ck_req(ck_req),
        .ck_ret(ck_ret),
        .ck_fwd0(ck_fwd0),
        .ck_fwd1(ck_fwd1),
        .rs(rs),
        .grp(grp),
        .bi(bi),
        .i_v(i_v),
        .i_we(i_we),
        .i_row(i_row),
        .i_mask(i_mask),
        .i_d(i_d),
        .f_v(f_v),
        .f_we(f_we),
        .f_row(f_row),
        .f_mask(f_mask),
        .f_d(f_d),
        .r_v(r_v),
        .r_d(r_d),
        .r_f(r_f),
        .r_o(r_o),
        .o_v(o_v),
        .o_d(o_d),
        .o_f(o_f),
        .o_o(o_o)
    );
endmodule
