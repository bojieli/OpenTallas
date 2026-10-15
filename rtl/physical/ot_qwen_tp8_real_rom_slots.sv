// TP8 slot-name identity wrappers for CLOSED ROM leaves. No logic, pin/clock rename, or latency.
// Physical aliases are emitted by tools/qwen_tp8/bind_real.py with exact source provenance.
module qfd_su_cbuf_g (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        crom_re,
    input  wire [8*24-1:0]   crom_addr,
    input  wire [5:0]        crom_stage,
    output wire [8*64-1:0]   crom_q,
    input  wire [5:0]        stage,
    input  wire              tok_start,
    input  wire [17:0]       tpos,
    input  wire [2:0]        grp,
    output wire              st_rdy,
    output wire [5:0]        st_rdy_stage,
    output wire [7:0]        f_re,
    output wire [8*24-1:0]   f_addr,
    output wire [5:0]        f_stage,
    input  wire [8*64-1:0]   f_q,
    input  wire              f_fault,
    input  wire [4:0]        f_lat,
    output wire              fault,
    output wire [1:0]        fault_code
);
    ot_qfd_su_cbuf_g u (
        .clk(clk),
        .rst_n(rst_n),
        .crom_re(crom_re),
        .crom_addr(crom_addr),
        .crom_stage(crom_stage),
        .crom_q(crom_q),
        .stage(stage),
        .tok_start(tok_start),
        .tpos(tpos),
        .grp(grp),
        .st_rdy(st_rdy),
        .st_rdy_stage(st_rdy_stage),
        .f_re(f_re),
        .f_addr(f_addr),
        .f_stage(f_stage),
        .f_q(f_q),
        .f_fault(f_fault),
        .f_lat(f_lat),
        .fault(fault),
        .fault_code(fault_code)
    );
endmodule

module qfd_crom_g (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        crom_re,
    input  wire [8*24-1:0]   crom_addr,
    input  wire [5:0]        crom_stage,
    input  wire [5:0]        crom_lb,
    output wire [8*64-1:0]   crom_q,
    output wire              fault,
    output wire [1:0]        fault_code
);
    ot_qfd_crom_gr u (
        .clk(clk),
        .rst_n(rst_n),
        .crom_re(crom_re),
        .crom_addr(crom_addr),
        .crom_stage(crom_stage),
        .crom_lb(crom_lb),
        .crom_q(crom_q),
        .fault(fault),
        .fault_code(fault_code)
    );
endmodule
