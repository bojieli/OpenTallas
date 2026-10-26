module gold_s6_rk (input wire ck, input wire rst_n, input wire d, output reg q);
    always @(posedge ck or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
module gold_s6_rst2x4 (input wire ck, input wire rst_n, output wire [3:0] rst);
    reg rs1;
    always @(posedge ck or negedge rst_n) if (!rst_n) rs1 <= 1'b0; else rs1 <= 1'b1;
    gold_s6_rk u_k0 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[0]));
    gold_s6_rk u_k1 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[1]));
    gold_s6_rk u_k2 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[2]));
    gold_s6_rk u_k3 (.ck(ck), .rst_n(rst_n), .d(rs1), .q(rst[3]));
endmodule
module gold_s6_fup (
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
    gold_s6_rst2x4 u_rl (.ck(ck), .rst_n(rst_n), .rst(rst));
    wire setid = cmd_q[0] && cmd_q[3:1] == 3'd7;
    wire [115:0] cmd_n = setid ? {cmd_q[115:8], cmd_q[7:4] + 4'd1, cmd_q[3:0]} : cmd_q;
    always @(posedge ck or negedge rst[0])
        if (!rst[0]) begin se_q[1087] <= 1'b0; scd_q[47] <= 1'b0; chu_q[1094] <= 1'b0; chu_q[547] <= 1'b0; agu_q <= 10'd0;
                           cmd_o[0] <= 1'b0; end
        else begin se_q[1087] <= st_dn_i[1087]; scd_q[47] <= sc_dn_i[47]; chu_q[1094] <= ch_up_i[1094];
                   chu_q[547] <= ch_up_i[547]; agu_q <= ag_up_i; cmd_o[0] <= cmd_n[0]; end
    always @(posedge ck) begin
        se_q[1086:0] <= st_dn_i[1086:0]; scd_q[46:0] <= sc_dn_i[46:0];
        chu_q[1093:548] <= ch_up_i[1093:548]; chu_q[546:0] <= ch_up_i[546:0]; cmd_o[115:1] <= cmd_n[115:1];
    end
endmodule
