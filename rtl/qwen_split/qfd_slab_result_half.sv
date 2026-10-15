`timescale 1ns/1ps
// Four real result groups of one TP8 band half. The tree controller's native
// request addresses are consumed directly; no invented scale-base descriptor.
module qfd_slab_result_half #(
    parameter integer BAND = 0,
    parameter integer HALF = 0
) (
    input wire ck, rst_n,
    input wire [15:0] ck_col, ck_mul,
    input wire [3:0] ck_group,
    input wire [340:0] tc,
    input wire [2047:0] ty,
    output wire [2212:0] rq,
    output wire [51:0] am
);
    wire [4095:0] colq_all;
    genvar g,c;
    generate for(g=0;g<4;g=g+1) begin:g_group
        localparam integer REQ = 4*HALF+g;
        wire [1023:0] colq;
        for(c=0;c<4;c=c+1) begin:g_col
            `ifdef SYNTHESIS
            ot_qwen_slab_pg_col u_col (.clk(ck_col[4*g+c]),
`else
            ot_qwen_slab_pg_col #(.ROM_INSTANCE($sformatf("qslab_b%0d_h%0d_g%0d_c%0d",BAND,HALF,g,c))) u_col (.clk(ck_col[4*g+c]),
`endif
                .gre1(tc[140] & tc[141+REQ]),
                .addr1(tc[149+24*REQ +: 24]), .cid(4'(c)),
                .m5(colq[256*c +: 256]));
        end
        assign colq_all[1024*g +: 1024] = colq;
    end endgenerate
    wire [3:0] we;
    wire [95:0] addr;
    wire [63:0] mask;
    wire [2047:0] data;
    wire ov,fault;
    wire [203:0] heads;
    wire [3:0] gov,gfault;
    // q15: port q (scale merge of group q + spport) is the hardened leaf qfd_slab_port_leaf on clock entry ck_group[q].
    generate for(genvar q=0;q<4;q=q+1) begin:g_port
        qfd_slab_port_leaf u_leaf (
            .ck(ck_group[q]),.ck_mul0(ck_mul[4*q]),.ck_mul1(ck_mul[4*q+1]),.ck_mul2(ck_mul[4*q+2]),.ck_mul3(ck_mul[4*q+3]),.rst_n(rst_n),.pt_id(16'(8*BAND+4*HALF+q)),
            .colq(colq_all[1024*q +: 1024]),.lv_in(ty[512*q +:512]),.a_v_e2(tc[26]),.a_f_e2(tc[139:27]),
            .o_we(we[q]),.o_addr(addr[24*q +:24]),.o_mask(mask[16*q +:16]),
            .o_data(data[512*q +:512]),.o_ov(gov[q]),.am(heads[51*q +:51]),.fault(gfault[q]));
    end endgenerate
    function automatic [50:0] winner(input [50:0] a,input [50:0] b);
        winner=(a[50] && (!b[50] || ({a[49:18],~a[17:0]}>{b[49:18],~b[17:0]}))) ? a:b;
    endfunction
    reg [50:0] h01,h23,head;
    reg fault_q;
    always @(posedge ck) begin
        h01<=winner(heads[50:0],heads[101:51]);
        h23<=winner(heads[152:102],heads[203:153]);
        head<=winner(h01,h23);
        fault_q<=rst_n & ((|gfault) | (|(gov ^ {4{gov[0]}})));
    end
    assign ov=gov[0];assign fault=fault_q;
    // Each slot is {addr24,mask16,data512}; the four strobes and burst marker
    // are separate, matching ot_qfd_res_ser's actual interface.
    generate for(g=0;g<4;g=g+1) begin:g_result
        assign rq[552*g +: 552] = {addr[24*g +: 24],mask[16*g +: 16],data[512*g +: 512]};
    end endgenerate
    assign rq[2211:2208] = we;
    assign rq[2212] = ov;
    assign am = {fault,head};
endmodule
