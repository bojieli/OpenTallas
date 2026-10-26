module mut_s6_rk (input wire ck, input wire rst_n, input wire d, output reg q);
    always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
module mut_s6_rst2x4 (input wire ck, input wire rst_n, output wire [3:0] rst);
    reg rs1;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs1 <= 1'b0; else rs1 <= 1'b1;
    mut_s6_rk u_k0 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[0]));
    mut_s6_rk u_k1 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[1]));
    mut_s6_rk u_k2 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[2]));
    mut_s6_rk u_k3 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[3]));
endmodule
module mut_s6_rst2_local (input wire ck, input wire rst_n, output wire rst);
    (* keep = 1 *) reg rs1;
    (* keep = 1 *) reg rs2;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs1 <= 1'b0; else rs1 <= 1'b1;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs2 <= 1'b0; else rs2 <= 1'b1;
    assign rst = rs2;
endmodule
module mut_s6_fup_reset_local #(parameter bit LOCAL_RESET_COPIES = 1'b1) (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [1087:0]  st_dn_i,
    input  wire [47:0]    sc_dn_i,
    input  wire [1094:0]  ch_up_i,
    input  wire [9:0]     ag_up_i,
    output reg  [1087:0]  se_q,
    output reg  [47:0]    scd_q,
    output reg  [1094:0]  chu_q,
    output reg  [9:0]     agu_q,
    input  wire [115:0]   cmd_q,
    output reg  [115:0]   cmd_o,
    input  wire [1087:0]  st_up_c,
    output wire [1087:0]  st_up_o,
    input  wire [47:0]    sc_up_c,
    output wire [47:0]    sc_up_o,
    input  wire [452:0]   hr_c,
    output wire [452:0]   hr_o,
    input  wire [1037:0]  chr_c,
    output wire [1037:0]  ch_up_o,
    input  wire [8:0]     treq_c,
    output wire [8:0]     treq_o,
    input  wire [513:0]   l9_c,
    output wire [513:0]   l9_o
);
    assign st_up_o = st_up_c; assign sc_up_o = sc_up_c; assign hr_o = hr_c; assign ch_up_o = chr_c; assign treq_o = treq_c;
    assign l9_o = l9_c;
    wire [3:0] rst;
    wire [3:0] rst_legacy;
    mut_s6_rst2x4 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst_legacy));
    assign rst[0] = rst_legacy[0];
    generate if (LOCAL_RESET_COPIES) begin : g_local_reset
        mut_s6_rst2_local u_agu (.ck(ck), .rst_n(rst_n), .rst(rst[1]));
        mut_s6_rst2_local u_chu (.ck(ck), .rst_n(rst_n), .rst(rst[2]));
        mut_s6_rst2_local u_cmd (.ck(ck), .rst_n(rst_n), .rst(rst[3]));
    end else begin : g_legacy_reset
        assign rst[3:1] = {3{rst_legacy[0]}};
    end endgenerate
    wire setid = cmd_q[0] && cmd_q[3:1] == 3'd7;
    wire [115:0] cmd_n = setid ? {cmd_q[115:8], cmd_q[7:4] + 4'd1, cmd_q[3:0]} : cmd_q;
    always @(posedge ck or negedge rst[0])
        if (!rst[0]) begin se_q[1087] <= 1'b0; scd_q[47] <= 1'b0; end
        else begin se_q[1087] <= st_dn_i[1087]; scd_q[47] <= sc_dn_i[47]; end
    always @(posedge ck or negedge rst[1])
        if (!rst[1]) agu_q <= 10'd0; else agu_q <= ag_up_i;
    always @(posedge ck or negedge rst[2])
        if (!rst[2]) begin chu_q[1094] <= 1'b0; chu_q[547] <= 1'b0; end
        else begin chu_q[1094] <= ch_up_i[1094]; chu_q[547] <= ch_up_i[547]; end
    always @(posedge ck or negedge rst[3])
        if (!rst[3]) cmd_o[0] <= 1'b0; else cmd_o[0] <= cmd_n[0];
    always @(posedge ck) begin
        se_q[1086:0] <= st_dn_i[1086:0]; scd_q[46:0] <= sc_dn_i[46:0];
        chu_q[1093:548] <= ch_up_i[1093:548]; chu_q[546:0] <= ch_up_i[546:0]; cmd_o[115:1] <= cmd_n[115:1];
    end
endmodule
