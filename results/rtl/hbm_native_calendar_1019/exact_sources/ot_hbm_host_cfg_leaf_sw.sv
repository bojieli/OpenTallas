`timescale 1ns/1ps
`default_nettype none
module ot_hbm_host_cfg_leaf_m38 #(
    parameter integer NCP = 2,            
    parameter integer NT  = 18,           
    parameter integer NF  = 28,           
    parameter integer MUT = 0
)(
    input  wire clk, rst_n,
    input  wire        cfg_v,
    input  wire [7:0]  cfg_target,
    input  wire [11:0] cfg_addr,
    input  wire [255:0] cfg_data,
    input  wire        desc_v,
    input  wire [11:0] desc_base,
    input  wire [12:0] desc_limit,
    input  wire [15:0] desc_loops,
    input  wire        launch_v,
    output wire [NCP-1:0]      o_cfg_v,
    output wire [NCP*8-1:0]    o_cfg_target,
    output wire [NCP*12-1:0]   o_cfg_addr,
    output wire [NCP*256-1:0]  o_cfg_data,
    output wire [NCP-1:0]      o_desc_v,
    output wire [NCP*12-1:0]   o_desc_base,
    output wire [NCP*13-1:0]   o_desc_limit,
    output wire [NCP*16-1:0]   o_desc_loops,
    output wire [NCP-1:0]      o_launch_v,
    input  wire [NT-1:0] t_ready, t_active,
    input  wire [NF-1:0] t_fault,
    output reg  [NT-1:0] s_ready, s_active,
    output reg  [NF-1:0] s_fault
);
    localparam integer PW = 8 + 12 + 256 + 12 + 13 + 16;    
    wire [1:0] rr;
    ot_rst_relay_m38 #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    reg cv_p, dv_p, lv_p;
    reg [PW-1:0] pl_p;
    always @(posedge clk) pl_p <= {desc_loops, desc_limit, desc_base, cfg_data, cfg_addr, cfg_target};
    always @(posedge clk or negedge rr[0])
        if (!rr[0]) begin cv_p <= 1'b0; dv_p <= 1'b0; lv_p <= 1'b0; end
        else begin cv_p <= cfg_v; dv_p <= desc_v; lv_p <= launch_v; end
    genvar g;
    generate for (g = 0; g < NCP; g = g + 1) begin : g_cp
        (* keep = "true" *) reg cv_c, dv_c, lv_c;
        (* keep = "true" *) reg [PW-1:0] pl_c;
        wire [PW-1:0] pl_m = (MUT == 1 && g == 1) ? (pl_p & ~({{(PW-21){1'b0}}, 1'b1, 20'd0})) : pl_p;
        always @(posedge clk) pl_c <= pl_m;
        always @(posedge clk or negedge rr[0])
            if (!rr[0]) begin cv_c <= 1'b0; dv_c <= 1'b0; lv_c <= 1'b0; end
            else begin cv_c <= cv_p; dv_c <= dv_p; lv_c <= lv_p; end
        wire short = (MUT == 2 && g == 1);
        wire [PW-1:0] pl_o = short ? pl_p : pl_c;
        assign o_cfg_v[g]               = short ? cv_p : cv_c;
        assign o_desc_v[g]              = short ? dv_p : dv_c;
        assign o_launch_v[g]            = short ? lv_p : lv_c;
        assign o_cfg_target[g*8 +: 8]   = pl_o[0 +: 8];
        assign o_cfg_addr[g*12 +: 12]   = pl_o[8 +: 12];
        assign o_cfg_data[g*256 +: 256] = pl_o[20 +: 256];
        assign o_desc_base[g*12 +: 12]  = pl_o[276 +: 12];
        assign o_desc_limit[g*13 +: 13] = pl_o[288 +: 13];
        assign o_desc_loops[g*16 +: 16] = pl_o[301 +: 16];
    end endgenerate
    reg [NT-1:0] rdy_p, act_p;
    reg [NF-1:0] flt_p;
    wire [NT-1:0] rdy_m;
    generate if (MUT == 3 && NT >= 2) begin : g_m3
        assign rdy_m = {rdy_p[NT-1:2], rdy_p[0], rdy_p[1]};
    end else begin : g_m3n
        assign rdy_m = rdy_p;
    end endgenerate
    always @(posedge clk or negedge rr[1])
        if (!rr[1]) begin
            rdy_p <= {NT{1'b0}}; act_p <= {NT{1'b0}}; flt_p <= {NF{1'b0}};
            s_ready <= {NT{1'b0}}; s_active <= {NT{1'b0}}; s_fault <= {NF{1'b0}};
        end else begin
            rdy_p <= t_ready; act_p <= t_active; flt_p <= t_fault;
            s_ready <= rdy_m; s_active <= act_p;
            s_fault <= (MUT == 4) ? (flt_p & ~{{(NF-1){1'b0}}, 1'b1}) : flt_p;
        end
endmodule
`default_nettype wire
`default_nettype none
module ot_hbm_host_cfg_leaf2_m38 #(parameter integer NT = 20, parameter integer NF = 32, parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [NT-1:0] t_ready, t_active, input wire [NF-1:0] t_fault,
    output wire [NT-1:0] s_ready, s_active, output wire [NF-1:0] s_fault
);
    ot_hbm_host_cfg_leaf_m38 #(.NCP(2), .NT(NT), .NF(NF), .MUT(MUT)) u (.clk(clk), .rst_n(rst_n),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v),
        .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .o_cfg_v({b_cfg_v, a_cfg_v}), .o_cfg_target({b_cfg_target, a_cfg_target}), .o_cfg_addr({b_cfg_addr, a_cfg_addr}),
        .o_cfg_data({b_cfg_data, a_cfg_data}), .o_desc_v({b_desc_v, a_desc_v}), .o_desc_base({b_desc_base, a_desc_base}),
        .o_desc_limit({b_desc_limit, a_desc_limit}), .o_desc_loops({b_desc_loops, a_desc_loops}),
        .o_launch_v({b_launch_v, a_launch_v}),
        .t_ready(t_ready), .t_active(t_active), .t_fault(t_fault), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
endmodule
`default_nettype wire
`default_nettype none
module ot_hbm_host_cfg_leaf_sw #(parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [17:0] t_ready, t_active, input wire [28:0] t_fault,
    output wire [17:0] s_ready, s_active, output wire [28:0] s_fault
); /*verilator hier_block*/
    ot_hbm_host_cfg_leaf2_m38 #(.NT(18), .NF(29), .MUT(MUT)) u (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .a_cfg_v(a_cfg_v), .a_cfg_target(a_cfg_target), .a_cfg_addr(a_cfg_addr), .a_cfg_data(a_cfg_data),
        .a_desc_v(a_desc_v), .a_desc_base(a_desc_base), .a_desc_limit(a_desc_limit), .a_desc_loops(a_desc_loops),
        .a_launch_v(a_launch_v), .b_cfg_v(b_cfg_v), .b_cfg_target(b_cfg_target), .b_cfg_addr(b_cfg_addr),
        .b_cfg_data(b_cfg_data), .b_desc_v(b_desc_v), .b_desc_base(b_desc_base), .b_desc_limit(b_desc_limit),
        .b_desc_loops(b_desc_loops), .b_launch_v(b_launch_v), .t_ready(t_ready), .t_active(t_active),
        .t_fault(t_fault), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
endmodule
module ot_hbm_host_cfg_leaf_se_m38 #(parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [17:0] t_ready, t_active, input wire [25:0] t_fault,
    output wire [17:0] s_ready, s_active, output wire [25:0] s_fault
);
    ot_hbm_host_cfg_leaf2_m38 #(.NT(18), .NF(26), .MUT(MUT)) u (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .a_cfg_v(a_cfg_v), .a_cfg_target(a_cfg_target), .a_cfg_addr(a_cfg_addr), .a_cfg_data(a_cfg_data),
        .a_desc_v(a_desc_v), .a_desc_base(a_desc_base), .a_desc_limit(a_desc_limit), .a_desc_loops(a_desc_loops),
        .a_launch_v(a_launch_v), .b_cfg_v(b_cfg_v), .b_cfg_target(b_cfg_target), .b_cfg_addr(b_cfg_addr),
        .b_cfg_data(b_cfg_data), .b_desc_v(b_desc_v), .b_desc_base(b_desc_base), .b_desc_limit(b_desc_limit),
        .b_desc_loops(b_desc_loops), .b_launch_v(b_launch_v), .t_ready(t_ready), .t_active(t_active),
        .t_fault(t_fault), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
endmodule
module ot_hbm_host_cfg_leaf_nw_m38 #(parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [18:0] t_ready, t_active, input wire [28:0] t_fault,
    output wire [18:0] s_ready, s_active, output wire [28:0] s_fault
);
    ot_hbm_host_cfg_leaf2_m38 #(.NT(19), .NF(29), .MUT(MUT)) u (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .a_cfg_v(a_cfg_v), .a_cfg_target(a_cfg_target), .a_cfg_addr(a_cfg_addr), .a_cfg_data(a_cfg_data),
        .a_desc_v(a_desc_v), .a_desc_base(a_desc_base), .a_desc_limit(a_desc_limit), .a_desc_loops(a_desc_loops),
        .a_launch_v(a_launch_v), .b_cfg_v(b_cfg_v), .b_cfg_target(b_cfg_target), .b_cfg_addr(b_cfg_addr),
        .b_cfg_data(b_cfg_data), .b_desc_v(b_desc_v), .b_desc_base(b_desc_base), .b_desc_limit(b_desc_limit),
        .b_desc_loops(b_desc_loops), .b_launch_v(b_launch_v), .t_ready(t_ready), .t_active(t_active),
        .t_fault(t_fault), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
endmodule
module ot_hbm_host_cfg_leaf_ne_m38 #(parameter integer MUT = 0) (
    input  wire clk, rst_n,
    input  wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input  wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input  wire launch_v,
    output wire a_cfg_v, output wire [7:0] a_cfg_target, output wire [11:0] a_cfg_addr, output wire [255:0] a_cfg_data,
    output wire a_desc_v, output wire [11:0] a_desc_base, output wire [12:0] a_desc_limit, output wire [15:0] a_desc_loops,
    output wire a_launch_v,
    output wire b_cfg_v, output wire [7:0] b_cfg_target, output wire [11:0] b_cfg_addr, output wire [255:0] b_cfg_data,
    output wire b_desc_v, output wire [11:0] b_desc_base, output wire [12:0] b_desc_limit, output wire [15:0] b_desc_loops,
    output wire b_launch_v,
    input  wire [13:0] t_ready, t_active, input wire [22:0] t_fault,
    output wire [13:0] s_ready, s_active, output wire [22:0] s_fault
);
    ot_hbm_host_cfg_leaf2_m38 #(.NT(14), .NF(23), .MUT(MUT)) u (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .a_cfg_v(a_cfg_v), .a_cfg_target(a_cfg_target), .a_cfg_addr(a_cfg_addr), .a_cfg_data(a_cfg_data),
        .a_desc_v(a_desc_v), .a_desc_base(a_desc_base), .a_desc_limit(a_desc_limit), .a_desc_loops(a_desc_loops),
        .a_launch_v(a_launch_v), .b_cfg_v(b_cfg_v), .b_cfg_target(b_cfg_target), .b_cfg_addr(b_cfg_addr),
        .b_cfg_data(b_cfg_data), .b_desc_v(b_desc_v), .b_desc_base(b_desc_base), .b_desc_limit(b_desc_limit),
        .b_desc_loops(b_desc_loops), .b_launch_v(b_launch_v), .t_ready(t_ready), .t_active(t_active),
        .t_fault(t_fault), .s_ready(s_ready), .s_active(s_active), .s_fault(s_fault));
endmodule
`default_nettype wire
`timescale 1ns/1ps
module ot_rst_relay_m38 #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    localparam integer RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES;
    (* async_reg = "true" *) reg [SYNC_STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n_in) begin
        if (!rst_n_in)
            sync_q <= {SYNC_STAGES{1'b0}};
        else
            sync_q <= {sync_q[SYNC_STAGES-2:0], 1'b1};
    end
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];
    genvar t;
    generate
        for (t = 0; t < TREE_STAGES; t = t + 1) begin : g_stage
            always @(posedge clk or negedge rst_n_in) begin
                if (!rst_n_in)
                    relay_q[t] <= {REGIONS{1'b0}};
                else if (t == 0)
                    relay_q[t] <= {REGIONS{sync_q[SYNC_STAGES-1]}};
                else
                    relay_q[t] <= relay_q[(t == 0) ? 0 : t-1];
            end
        end
    endgenerate
    assign rst_n = relay_q[TREE_STAGES-1];
    initial begin
        if (SYNC_STAGES < 2) $error("ot_rst_relay: SYNC_STAGES must be >= 2 (release crosses from the async port)");
        if (TREE_STAGES < 1) $error("ot_rst_relay: TREE_STAGES must be >= 1");
        if (REGIONS < 1)     $error("ot_rst_relay: REGIONS must be >= 1");
    end
endmodule
