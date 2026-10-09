// Additive fixed128-bit face hierarchy; preserves actual f3 per-bit latency.
// Model: tools/hbm_vm8_face_hierarchy_model.py; no physical adoption claim.
module hfd_vm_se_n_hier (
    input wire [0:0] ck,
    input wire [0:0] rst,
    input wire [255:0] f_n_ctl,
    input wire [2255:0] f_n_row,
    input wire [2263:0] f_n_wr,
    input wire [2255:0] f_w_row,
    input wire [2263:0] f_w_wr,
    output wire [255:0] t_n_ctl,
    output wire [2255:0] t_n_row,
    output wire [2263:0] t_n_wr,
    output wire [255:0] t_w_ctl,
    output wire [2255:0] t_w_row,
    output wire [2263:0] t_w_wr,
    input wire [1077:0] s2n,
    output wire [3854:0] n2s
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    wire [2263:0] x_f_w_wr;
    ot_hbm_vm8_face_bus #(.W(2264),.D(1)) u_x_f_w_wr(.clk(clk),.d(f_w_wr),.q(x_f_w_wr));
    wire [2255:0] x_f_w_row;
    ot_hbm_vm8_face_bus #(.W(2256),.D(1)) u_x_f_w_row(.clk(clk),.d(f_w_row),.q(x_f_w_row));
    wire [2263:0] x_f_n_wr;
    ot_hbm_vm8_face_bus #(.W(2264),.D(1)) u_x_f_n_wr(.clk(clk),.d(f_n_wr),.q(x_f_n_wr));
    wire [2255:0] x_f_n_row;
    ot_hbm_vm8_face_bus #(.W(2256),.D(1)) u_x_f_n_row(.clk(clk),.d(f_n_row),.q(x_f_n_row));
    wire [1077:0] x_s2n;
    ot_hbm_vm8_face_bus #(.W(1078),.D(1)) u_x_s2n(.clk(clk),.d(s2n),.q(x_s2n));
    // s2n: f_su_SE[1077:0] (read request [200:0] + placeholders) after its face chain + the seam (+2)
    wire sv; wire [767:0] sd;
    ot_hfd_vm_slice #(.NM(3)) u_slice (.clk(clk), .rst_n(rst_n), .cmd_v(x_f_w_wr[0]), .we(x_f_w_wr[1]), .bank(x_f_w_wr[2]), .addr(x_f_w_wr[9:3]), .wd(x_f_w_wr[777:10]), .rv(sv), .rd(sd));
    wire [2263:0] od_t_n_wr = {1742'd0, x_f_w_wr[1289:778], x_f_w_wr[9:0]};
    wire [2263:0] o_t_n_wr;
    ot_hbm_vm8_face_bus #(.W(2264),.D(3)) g_o_t_n_wr(.clk(clk),.d(od_t_n_wr),.q(o_t_n_wr));
    assign t_n_wr = o_t_n_wr;
    wire [2255:0] od_t_n_row = {193'd0, x_f_w_row[2062:0]};
    wire [2255:0] o_t_n_row;
    ot_hbm_vm8_face_bus #(.W(2256),.D(3)) g_o_t_n_row(.clk(clk),.d(od_t_n_row),.q(o_t_n_row));
    assign t_n_row = o_t_n_row;
    wire [2263:0] od_t_w_wr = {472'd0, x_f_n_wr[512], x_f_n_wr[511:0], x_s2n[1077:0], x_s2n[200:0]};
    wire [2263:0] o_t_w_wr;
    ot_hbm_vm8_face_bus #(.W(2264),.D(3)) g_o_t_w_wr(.clk(clk),.d(od_t_w_wr),.q(o_t_w_wr));
    assign t_w_wr = o_t_w_wr;
    wire [2255:0] od_t_w_row = {974'd0, x_f_n_row[512:1], x_f_n_row[0], sd, sv};
    wire [2255:0] o_t_w_row;
    ot_hbm_vm8_face_bus #(.W(2256),.D(3)) g_o_t_w_row(.clk(clk),.d(od_t_w_row),.q(o_t_w_row));
    assign t_w_row = o_t_w_row;
    assign t_n_ctl = 256'd0;
    assign t_w_ctl = 256'd0;
    wire [3854:0] od_n2s = {x_f_n_wr[1330:513], x_f_w_wr[2263:1290], x_f_w_row[2062:0]};
    wire [3854:0] o_n2s;
    ot_hbm_vm8_face_bus #(.W(3855),.D(3)) g_o_n2s(.clk(clk),.d(od_n2s),.q(o_n2s));
    assign n2s = o_n2s;
endmodule
