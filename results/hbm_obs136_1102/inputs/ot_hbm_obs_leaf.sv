module ot_hbm_obs_leaf #(
    parameter integer N = 32,
    parameter integer LID = 0,
    parameter [511:0] SYNC_MASK = 512'd0,
    parameter integer MUT = 0
)(
    input  wire clk, rst_n,
    input  wire [N-1:0] obs,
    input  wire q_v,
    input  wire [7:0] q_idx,
    input  wire [31:0] q_d,
    output reg  r_v,
    output reg  [7:0] r_idx,
    output reg  [31:0] r_d
);
    localparam integer NW = (N + 31) / 32;
    localparam integer NP = NW * 32;
    wire [0:0] lrst_n;
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(lrst_n));

`line 46 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/die_glue/ot_hbm_obs_leaf.sv" 0
     
    reg [N-1:0] p1, p2;
    always @(posedge clk) begin p1 <= obs; p2 <= p1; end
    wire [N-1:0] sm = SYNC_MASK[N-1:0];
    wire [N-1:0] live_n = (p1 & ~sm) | (p2 & sm);
    wire [NP-1:0] live;
    assign live[N-1:0] = live_n & ((MUT == 2) ? ({N{1'b1}} >> 1) : {N{1'b1}});
    generate if (NP > N) begin : g_pad
        assign live[NP-1:N] = {(NP - N){1'b0}};
    end endgenerate

`line 57 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/die_glue/ot_hbm_obs_leaf.sv" 0
     
    reg a_v; reg [7:0] a_idx; reg [31:0] a_d;
    always @(posedge clk or negedge lrst_n)
        if (!lrst_n) a_v <= 1'b0; else a_v <= q_v;
    always @(posedge clk) begin a_idx <= q_idx; a_d <= q_d; end

`line 63 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/die_glue/ot_hbm_obs_leaf.sv" 0
     
    (* keep = "true" *) reg [NW-1:0] oh0, oh1, clr;
    reg b_v; reg [7:0] b_idx; reg [31:0] b_d;
    wire hit = a_v && ({29'd0, a_idx[7:5]} == LID);
    integer w;
    always @(posedge clk or negedge lrst_n)
        if (!lrst_n) begin oh0 <= {NW{1'b0}}; oh1 <= {NW{1'b0}}; clr <= {NW{1'b0}}; b_v <= 1'b0; end
        else begin
            b_v <= a_v;
            for (w = 0; w < NW; w = w + 1) begin
                oh0[w] <= hit && (a_idx[4] == (MUT == 3)) && {28'd0, a_idx[3:0]} == w;
                oh1[w] <= hit && (a_idx[4] != (MUT == 3)) && {28'd0, a_idx[3:0]} == w;
                clr[w] <= hit &&  a_idx[4] && {28'd0, a_idx[3:0]} == w && MUT != 1;
            end
        end
    always @(posedge clk) begin b_idx <= a_idx; b_d <= a_d; end

`line 80 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/die_glue/ot_hbm_obs_leaf.sv" 0
     
    reg [NP-1:0] sticky;
    integer k;
    always @(posedge clk or negedge lrst_n)
        if (!lrst_n) sticky <= {NP{1'b0}};
        else for (k = 0; k < NP; k = k + 1) sticky[k] <= (sticky[k] & ~clr[k / 32]) | live[k];

`line 87 "/srv/opentallas-scratch2/claude/codex-hbm-whole-1101/stage5/readset/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/hbm_accel/die_glue/ot_hbm_obs_leaf.sv" 0
    reg [31:0] word;
    integer j;
    always @* begin
        word = 32'd0;
        for (j = 0; j < NW; j = j + 1)
            word = word | ({32{oh0[j]}} & live[j * 32 +: 32]) | ({32{oh1[j]}} & sticky[j * 32 +: 32]);
    end
    always @(posedge clk or negedge lrst_n)
        if (!lrst_n) r_v <= 1'b0; else r_v <= b_v;
    always @(posedge clk) begin
        r_idx <= b_idx;
        r_d <= b_d | word;
    end
endmodule
