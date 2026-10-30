module ot_s81sl_vn_b_rin #(
    parameter integer LM = 5,
    parameter integer LA = 6,
    // F6 SRAM-side write stage; 0 external cycles via exact read forwarding.
    parameter integer HW_STAGE = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          hw_v,
    input  wire [2:0]    hw_j,
    input  wire          hw_hf,
    input  wire [255:0]  hw_d,
    input  wire          hr_v,
    input  wire [2:0]    hr_j,
    input  wire          hr_hf,
    output reg           hq_v,
    output reg  [255:0]  hq_d,           // half row 1 when hr_hf = 1, else 0 (the leaf ORs vn_a's)
    input  wire          wl_v,
    input  wire [2:0]    wl_i,
    input  wire [127:0]  wl_d,           // lanes 4..7 of the gain row
    input  wire          n_go,
    input  wire [127:0]  n_pre,
    input  wire          rb_v,
    input  wire [31:0]   rb_d,
    input  wire          c_v_q,            // chain partial acc3 from vn_a
    input  wire [30:0]   c_s_q,            // acc3 magnitude: its sign is constant 0 (OWNER DECISION 8)
    output wire          chain_rs_c, // exact reset feed for the lifted valid FF
    output reg           p_v,
    output reg  [31:0]   p_d,
    output reg           y_v,
    output reg  [2:0]    y_i,
    output reg  [63:0]   y,              // packed BF16 lanes 4..7
    (* keep *) output reg fault
);
    localparam integer DC = LM + 3 * LA + 2;     // acc3 at vn_b's chain (2 partition flops)
    localparam integer DS = LM + 7 * LA + 2;     // chain sum (group DS + 2)
`ifdef OT_S81_VN_CONST_ZERO
    // DIE-S81-31/VEZ 10-29 (opt-in define, off by default): constant-zero lanes declared to the RTL (ng4 XO_ZERO_LOW);
    // the chunk sums are sums of squares (sign constant 0), so the unreset tree operand store lv is read sign-masked
    localparam integer VN_XO_ZERO_LOW = 16;
    localparam [31:0]  LV_MASK = 32'h7fffffff;
`else
    localparam integer VN_XO_ZERO_LOW = 0;
    localparam [31:0]  LV_MASK = 32'hffffffff;
`endif
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_c = rsv[0], rs_g = rsv[1], rs_t = rsv[2], rs_o = rsv[3];

    reg hw_v_c, hr_v_c, go_c, wl_v_c, rb_v_c;
    reg [2:0] hw_j_c, hr_j_c, wl_i_c; reg hw_hf_c, hr_hf_c;
    reg [255:0] hw_d_c; reg [127:0] wl_d_c; reg [127:0] pre_in, pre_c; reg [31:0] rb_d_c;
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin hw_v_c <= 1'b0; hr_v_c <= 1'b0; go_c <= 1'b0; wl_v_c <= 1'b0; rb_v_c <= 1'b0; end
        else begin hw_v_c <= hw_v; hr_v_c <= hr_v; go_c <= n_go; wl_v_c <= wl_v; rb_v_c <= rb_v; end
    always @(posedge clk) begin
        hw_j_c <= hw_j; hw_hf_c <= hw_hf; hw_d_c <= hw_d; hr_j_c <= hr_j; hr_hf_c <= hr_hf;
        pre_in <= n_pre;
        wl_i_c <= wl_i; wl_d_c <= wl_d; rb_d_c <= rb_d;
    end
    always @(posedge clk)
`ifdef OT_S81SL_MUT_PRESTALE
        if (n_go) pre_c <= pre_in;
`else
        if (go_c) pre_c <= pre_in;
`endif
    // partition pin flops from vn_a (+1 edge)
    assign chain_rs_c = rs_c;

    reg run; reg [2:0] nj; reg g_go, g_inv, g_inv0; reg [511:0] g_x;
    integer i, k;
    wire [255:0] hm1, hm1_mem;
    wire mem_we; wire [6:0] mem_wa; wire [255:0] mem_wd;
    wire         hre = hr_v_c || run;
    wire [6:0]   hra = run ? {4'd0, nj} : {4'd0, hr_j_c};
    generate if (HW_STAGE != 0) begin : g_hwif
        ot_s81sl_hw_write_stage u_stage (.clk(clk), .re(hre && (run || hr_hf_c)), .ra(hra),
            .we(hw_v_c && hw_hf_c), .wa({4'd0, hw_j_c}), .wd(hw_d_c), .mem_q(hm1_mem),
            .mw(mem_we), .ma(mem_wa), .md(mem_wd), .q(hm1));
    end else begin : g_hw_direct
        assign mem_we = hw_v_c && hw_hf_c;
        assign mem_wa = {4'd0, hw_j_c}; assign mem_wd = hw_d_c; assign hm1 = hm1_mem;
    end endgenerate
    ot_sram_1r1w_128x256_m1_r2c2 u_h1 (.clk(clk), .r_ce_in(hre && (run || hr_hf_c)), .r_addr_in(hra), .rd_out(hm1_mem),
        .w_ce_in(mem_we), .w_addr_in(mem_wa), .wd_in(mem_wd), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    reg hrv1, hrhf1;
    always @(posedge clk or negedge rs_o) if (!rs_o) begin hrv1 <= 1'b0; hq_v <= 1'b0; end
        else begin hrv1 <= hr_v_c && !run; hq_v <= hrv1; end
    always @(posedge clk) begin hrhf1 <= hr_hf_c; hq_d <= hm1 & {256{hrhf1}}; end
    always @(posedge clk or negedge rs_c)
        if (!rs_c) begin run <= 1'b0; nj <= 3'd0; g_go <= 1'b0; g_inv0 <= 1'b0; g_inv <= 1'b0; end
        else begin
            g_go <= go_c;
            g_inv0 <= run;
            g_inv <= g_inv0;
            if (go_c) begin run <= 1'b1; nj <= 3'd0; end
            else if (run) begin nj <= nj + 3'd1; if (nj == 3'd7) run <= 1'b0; end
        end
    // S81-CORES-R1 10-27: process-local loop variables (module-scope i shared with the sel priority encoder elaborated a
    // 32-bit DFF with conflicting constant drivers: rtl_lint check -assert); no logic change.
    always @(posedge clk) begin : g_gx
        integer kx, ix;
        for (kx = 0; kx < 4; kx = kx + 1)
            for (ix = 0; ix < 4; ix = ix + 1)
                g_x[(4 * kx + ix) * 32 +: 32] <= {hm1[(4 * kx + ix) * 16 +: 16], 16'd0};
    end

    wire gq, x_v, gy_v; wire [7:0] xi, gy_i; wire [127:0] sq, gy; wire [3:0] lf;
    ot_s81sl_vn_ng4 #(.D(64), .N(8), .LM(LM), .LA(LA), .XO_ZERO_LOW(VN_XO_ZERO_LOW)) u_g (.clk(clk), .rst_n(rs_g), .go(g_go), .in_v(g_inv), .in_x(g_x),
        .pre(pre_c), .wl_v(wl_v_c), .wl_i(wl_i_c), .wl_d(wl_d_c), .rb_v(rb_v_c), .rb_d(rb_d_c), .go_q(gq), .x_v(x_v),
        .xi(xi), .sq(sq), .y(gy), .y_v(gy_v), .y_i(gy_i), .lf(lf));

    // ---- chunk chain, lanes 4..7: adder k (4..7) at vs[LM + LA (k - 1) + 2], operand acc3 = c_s through its pin flop,
    // lane k's square delayed LA (k - 1) + 2
    (* keep = "true", dont_touch = "true" *) reg [4:0] rc;     // [0] chain control / output, [1 + j] stage 4 + j
    always @(posedge clk or negedge rs_g) if (!rs_g) rc <= 5'd0; else rc <= 5'h1f;
    wire [DS:0] vs;
    ot_hdc_vline #(.D(DS)) u_vs (.clk(clk), .rst_n(rc[0]), .v(x_v), .vd(vs));
    wire [7:0] si;
    ot_hdc_delay #(.W(8), .D(DS)) u_si (.clk(clk), .rst_n(rc[0]), .d(xi), .q(si));
    wire [31:0] acc [0:4];
    wire [4:0]  cf;
`ifdef OT_S81SL_SPMUT_C1
    assign acc[0] = {1'b0, c_s};           // NEGATIVE CONTROL: acc3 from the pin, one edge early
`else
    assign acc[0] = {1'b0, c_s_q};          // acc3 >= 0: a sum of squares
`endif
    // lockstep: vn_a's acc3 valid must land on vn_b's own chain slot
    assign cf[0] = c_v_q != vs[DC];
    genvar gj;
    generate for (gj = 0; gj < 4; gj = gj + 1) begin : g_j
        wire [31:0] sd;
        ot_hdc_delay #(.W(32), .D(LA * (gj + 3) + 2)) u_sd (.clk(clk), .rst_n(rc[1 + gj]), .d(sq[gj * 32 +: 32]), .q(sd));
        ot_dsrom_qadd #(.LAT(LA)) u_a (clk, rc[1 + gj], vs[LM + LA * (gj + 3) + 2], acc[gj], sd, acc[gj + 1], cf[gj + 1]);
    end endgenerate
    reg s_v; reg [7:0] s_i; reg [31:0] s;
    always @(posedge clk or negedge rc[0]) if (!rc[0]) s_v <= 1'b0; else s_v <= vs[DS];
    always @(posedge clk) begin s_i <= si; s <= acc[4]; end

    reg [3:0] lf_r; reg gf;
    always @(posedge clk or negedge rc[0])
        if (!rc[0]) begin lf_r <= 4'd0; gf <= 1'b0; end
        else begin
            lf_r <= gq ? 4'd0 : lf;
            gf <= gq ? 1'b0 : ((|lf_r) || (|cf));
        end

    // ---------------------------------------------------------------- beat tree (r-old's, 2 edges late: go clear too)
    reg [1:0] go_d;
    always @(posedge clk or negedge rs_t) if (!rs_t) go_d <= 2'd0; else go_d <= {go_d[0], go_c};
    wire go_t = go_d[1];
    reg [31:0] lv [0:7];  reg [7:0] lp;
    reg [31:0] nv [0:6];  reg [6:0] np, ni;
    wire [31:0] lvm [0:7];                  // lv as the tree reads it (LV_MASK all ones unless OT_S81_VN_CONST_ZERO)
    genvar gv;
    generate for (gv = 0; gv < 8; gv = gv + 1) begin : g_lvm
        assign lvm[gv] = lv[gv] & LV_MASK;
    end endgenerate
    wire [6:0] rdy;
`ifdef OT_S81SL_MUT_TREE
    assign rdy[0] = &lp[3:0] & !ni[0];
    assign rdy[1] = &lp[3:0] & !ni[1];
`else
    assign rdy[0] = lp[0] & lp[1] & !ni[0];
    assign rdy[1] = lp[2] & lp[3] & !ni[1];
`endif
    assign rdy[2] = lp[4] & lp[5] & !ni[2];
    assign rdy[3] = lp[6] & lp[7] & !ni[3];
    assign rdy[4] = np[0] & np[1] & !ni[4];
    assign rdy[5] = np[2] & np[3] & !ni[5];
    assign rdy[6] = np[4] & np[5] & !ni[6];
    reg [2:0] sel; reg any;
    always @(*) begin : g_sel
        integer is;
        any = |rdy; sel = 3'd0;
        for (is = 6; is >= 0; is = is - 1) if (rdy[is]) sel = is[2:0];
    end
    reg [31:0] ta, tb;
    always @(*) begin
        case (sel)
`ifdef OT_S81SL_MUT_TREE
            3'd0: begin ta = lvm[0]; tb = lvm[2]; end
            3'd1: begin ta = lvm[1]; tb = lvm[3]; end
`else
            3'd0: begin ta = lvm[0]; tb = lvm[1]; end
            3'd1: begin ta = lvm[2]; tb = lvm[3]; end
`endif
            3'd2: begin ta = lvm[4]; tb = lvm[5]; end
            3'd3: begin ta = lvm[6]; tb = lvm[7]; end
            3'd4: begin ta = nv[0]; tb = nv[1]; end
            3'd5: begin ta = nv[2]; tb = nv[3]; end
            default: begin ta = nv[4]; tb = nv[5]; end
        endcase
    end
    reg a_v; reg [2:0] a_n; reg [31:0] a_a, a_b;
    wire [31:0] a_y; wire a_f; wire [LA:0] avl; wire [2:0] a_no;
    always @(posedge clk or negedge rs_t)
        if (!rs_t) begin a_v <= 1'b0; lp <= 8'd0; np <= 7'd0; ni <= 7'd0; end
        else begin
            a_v <= any;
            if (go_t) begin lp <= 8'd0; np <= 7'd0; ni <= 7'd0; end
            else begin
                if (s_v) lp[s_i[2:0]] <= 1'b1;
                if (any) ni[sel] <= 1'b1;
                if (avl[LA]) np[a_no] <= 1'b1;
            end
        end
    always @(posedge clk) begin
        if (s_v) lv[s_i[2:0]] <= s;
        a_n <= sel; a_a <= ta; a_b <= tb;
        if (avl[LA]) nv[a_no] <= a_y;
    end
    ot_dsrom_qadd #(.LAT(LA)) u_add (clk, rs_t, a_v, a_a, a_b, a_y, a_f);
    ot_hdc_vline #(.D(LA)) u_avl (.clk(clk), .rst_n(rs_t), .v(a_v), .vd(avl));
    ot_hdc_delay #(.W(3), .D(LA)) u_ano (.clk(clk), .rst_n(rs_t), .d(a_n), .q(a_no));

    (* keep *) reg fault_s;
    wire fault_n = go_c ? run
                 : (hr_v_c && run) ? 1'b1
                 : (gf || (avl[LA] && a_f) || (s_v && s_i > 8'd7)) ? 1'b1 : fault_s;
    always @(posedge clk or negedge rs_o)
        if (!rs_o) begin p_v <= 1'b0; y_v <= 1'b0; fault <= 1'b0; fault_s <= 1'b0; end
        else begin
            p_v <= avl[LA] && a_no == 3'd6;
            y_v <= gy_v;
            fault_s <= fault_n;
            fault <= fault_n;
        end
    always @(posedge clk) begin p_d <= a_y; y_i <= gy_i[2:0];
        y <= {gy[127:112], gy[95:80], gy[63:48], gy[31:16]}; end
endmodule
