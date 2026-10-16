// Candidate only: all command/Y/calendar inputs already in this serial clock domain.
// No inherited physical view or fixed phase bridge; output y_rdy is compatibility status only.
module ot_s81_hc_cpin_calendar #(
    parameter integer COMMAND_POST_AGES = 0,
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, TH = 8
) (
    input  wire                cck, crs, sk, srs,
    input wire [639:0] command_post_ages,
    output wire [639:0] n_command_post_ages,
    input wire [31:0] y_tag,command_y_tag,command_done_age,command_ss_age,command_scalar_age,
    input wire [4:0] y_row,
    output reg [31:0] n_y_tag,n_command_y_tag,n_command_done_age,n_command_ss_age,n_command_scalar_age,
    output reg [4:0] n_y_row,
    // Descriptor is held from command capture until the next command; it
    // shares the command's registered serial boundary without new cycles.
    // Disabled mode adds no state and preserves the previous parameter profile.
    // die pins
    input  wire                c_cmd_v,
    input  wire [83:0]         c_cmd_d,
    output reg                 c_done_v,
    output reg  [7:0]          c_done_tag,
    input  wire                inp,
    output reg  [S_RD-1:0]     rq_v,
    output reg  [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output reg                 flt,
    output reg                 online,
    output reg  [3:0]          fcode,
    input  wire                y_v,
    output reg                 y_rdy,
    input  wire [YS1-1:0]      y_s,
    // the outer roots: accept pulse
    (* keep = "true" *) output reg yacc_w,
    (* keep = "true" *) output reg yacc_e,
    // combine tile seam
    output reg                 n_cmd_v,
    output reg  [83:0]         n_cmd_d,
    input  wire                n_done_v,
    input  wire [7:0]          n_done_tag,
    output reg                 n_inp,
    input  wire [S_RD-1:0]     n_rq_v,
    input  wire [S_RD*14-1:0]  n_rq_row,
    output reg  [S_RD-1:0]     n_rs_v,
    output reg  [S_RD*512-1:0] n_rs_d,
    input  wire                n_flt,
    input  wire                n_online,
    input  wire [3:0]          n_fcode,
    (* keep = "true" *) output reg n_yacc,
    output reg  [YS1-1:0]      n_y,
    input  wire                n_ypop
);
    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;
    generate if(COMMAND_POST_AGES!=0)begin:g_command_post_ages
      reg[639:0]held;
      always @(posedge sk)if(c_cmd_v)held<=command_post_ages;
      assign n_command_post_ages=held;
    end else begin:g_no_command_post_ages
      assign n_command_post_ages=640'd0;
    end endgenerate
    // controller-clock domain: command in, done out (pin flops; the seam flops are the combine tile's)
    always @(posedge sk or negedge srs)
        if (!srs) begin n_cmd_v <= 1'b0; c_done_v <= 1'b0; end
        else begin n_cmd_v <= c_cmd_v; c_done_v <= n_done_v; end
    always @(posedge sk) begin n_cmd_d <= c_cmd_d; c_done_tag <= n_done_tag; end
    // slab clock
    // Each identical acceptance pulse has its own physical pin flop. keep=true prevents synthesis from merging
    // the W/E/S copies; the recipe-2 pin hook places each at its own face, with no added cycle.
    wire      acc = y_v; // compiler-reserved event, never gated by occupancy/pop
    always @(posedge sk or negedge srs)
        if (!srs) begin
            n_inp <= 1'b0; rq_v <= 0; n_rs_v <= 0; flt <= 1'b0; online <= 1'b0; fcode <= 0;
            y_rdy <= 1'b0; n_yacc <= 1'b0; yacc_w <= 1'b0; yacc_e <= 1'b0;
        end else begin
            n_inp <= inp; rq_v <= n_rq_v; n_rs_v <= rs_v; flt <= n_flt; online <= n_online; fcode <= n_fcode;
            y_rdy <= 1'b1; // compatibility/status only; not an execution enable
            n_yacc <= acc; yacc_w <= acc; yacc_e <= acc;
        end
    always @(posedge sk) begin rq_row <= n_rq_row; n_rs_d <= rs_d; n_y <= y_s; end
    always @(posedge sk) begin
        n_y_tag <= y_tag; n_y_row <= y_row;
        n_command_y_tag <= command_y_tag; n_command_done_age <= command_done_age;
        n_command_ss_age <= command_ss_age; n_command_scalar_age <= command_scalar_age;
    end
endmodule
