// hfd_barrier: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  Two K32 root nodes of the closed ot_gpu_barrier_node (barrier_k32: SS +330.53 / FF +39.39 ps): node n (n = 0, 1) takes the 32 SM arrive senses f_cmdproc[32n +: 32] from the cmdproc and returns the release fan-out t_cmdproc[32n +: 32]; each root ties rel_in to its own up.
module hfd_barrier (
    input wire [0:0] ck,
    input wire [63:0] f_cmdproc,
    input wire [0:0] rst,
    output wire [63:0] t_cmdproc
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [63:0] i0_f_cmdproc; always @(posedge clk) i0_f_cmdproc <= f_cmdproc;
    reg [63:0] i1_f_cmdproc; always @(posedge clk) i1_f_cmdproc <= i0_f_cmdproc;
    reg [63:0] i_f_cmdproc; always @(posedge clk) i_f_cmdproc <= i1_f_cmdproc;
    wire [0:0] w_n0_clk;
    wire [0:0] w_n0_rst_n;
    wire [31:0] w_n0_arr;
    wire [0:0] w_n0_up;
    wire [0:0] w_n0_rel_in;
    wire [31:0] w_n0_rel;
    wire [0:0] w_n1_clk;
    wire [0:0] w_n1_rst_n;
    wire [31:0] w_n1_arr;
    wire [0:0] w_n1_up;
    wire [0:0] w_n1_rel_in;
    wire [31:0] w_n1_rel;
    assign w_n0_clk = {1{clk}};
    assign w_n0_rst_n = {1{rst_n}};
    assign w_n0_arr = {i_f_cmdproc[31:0]};
    assign w_n0_rel_in = w_n0_up;
    ot_gpu_barrier_node #(.K(32)) u_n0 (.clk(w_n0_clk), .rst_n(w_n0_rst_n), .arr(w_n0_arr), .up(w_n0_up), .rel_in(w_n0_rel_in), .rel(w_n0_rel));
    assign w_n1_clk = {1{clk}};
    assign w_n1_rst_n = {1{rst_n}};
    assign w_n1_arr = {i_f_cmdproc[63:32]};
    assign w_n1_rel_in = w_n1_up;
    ot_gpu_barrier_node #(.K(32)) u_n1 (.clk(w_n1_clk), .rst_n(w_n1_rst_n), .arr(w_n1_arr), .up(w_n1_up), .rel_in(w_n1_rel_in), .rel(w_n1_rel));
    wire [63:0] od_t_cmdproc = {w_n1_rel[31:0], w_n0_rel[31:0]};
    wire [63:0] o_t_cmdproc;
    for (genvar k = 0; k < 64; k = k + 1) begin : g_o_t_cmdproc
        ot_hfd_oreg3 u (.clk(clk), .d(od_t_cmdproc[k]), .q(o_t_cmdproc[k]));
    end
    assign t_cmdproc[63:0] = o_t_cmdproc[63:0];
endmodule
