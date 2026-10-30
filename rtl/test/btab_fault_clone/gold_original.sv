// Exact original C module body, top name only changed for miter. No candidate logic.
module qfd_dv_s8x_btab_original #(parameter integer MIF = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire            bs_re,
    input  wire [23:0]     bs_addr,
    output reg  [255:0]    bs_q,
    input  wire            tw_we,
    input  wire [1:0]      tw_kind,
    input  wire [8:2]      tw_addr,
    input  wire [1023:0]   tw_data,
    output reg             fault
);
    genvar gk, bk;
    reg rl0, rl1;
    generate if (MIF == 0) begin : g_legacy_reset
        always @(posedge ck) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end   // QC-CORES kit patch (OWNER DECISION 13): rst_n = synchronous registered input; 2-stage synchronous relay, same release depth
    end else begin : g_timed_reset
        // Timed reset input of the physical MIF1 profile; release depth stays2.
        always @(posedge ck) if (!rst_n) begin rl0 <= 1'b0; rl1 <= 1'b0; end else begin rl0 <= 1'b1; rl1 <= rl0; end
    end endgenerate
    reg pbs_re; reg [23:0] pbs_addr;
    always @(posedge ck) begin pbs_re <= bs_re; pbs_addr <= bs_addr; end
    reg ptw_we; reg [1:0] ptw_kind; reg [8:2] ptw_addr; reg [1023:0] ptw_data;
    always @(posedge ck) begin ptw_we <= tw_we; ptw_kind <= tw_kind; ptw_addr <= tw_addr; ptw_data <= tw_data; end
    wire ptw_w = ptw_we && ptw_kind == 2'd2;
    wire [1023:0] twp_d; wire [8:2] twp_a; wire twp_w;
    qfd_dv_s8x_kff #(.W(1024), .ID(7100)) u_twpd (.ck(ck), .d(ptw_data), .q(twp_d));
    qfd_dv_s8x_kff #(.W(7), .ID(7101)) u_twpa (.ck(ck), .d(ptw_addr), .q(twp_a));
    qfd_dv_s8x_kff #(.W(1), .ID(7102)) u_twpw (.ck(ck), .d(ptw_w), .q(twp_w));
    wire [8:0] bs_word = pbs_addr[8:0];
    wire [4*256-1:0] bt_rd;
    wire [1:0] cap_bank;   // bank of the read the SRAMs latch this edge
    generate if (MIF == 0) begin : g_cb0
        assign cap_bank = bs_word[1:0];
    end else begin : g_cb1
        qfd_dv_s8x_kff #(.W(2), .ID(7149)) u_rbk (.ck(ck), .d(bs_word[1:0]), .q(cap_bank));
    end endgenerate
    generate for (bk = 0; bk < 4; bk = bk + 1) begin : g_btb
        wire m_rce, m_we; wire [8:2] m_ra, m_wa; wire [255:0] m_wd;
        if (MIF == 0) begin : g_d
            assign m_rce = pbs_re && bs_word[1:0] == bk[1:0]; assign m_ra = bs_word[8:2];
            assign m_we = twp_w; assign m_wa = twp_a; assign m_wd = twp_d[256*bk +: 256];
        end else begin : g_r
            // per-SRAM landing registers (distinct IDs: distinct kept modules, never merged), decode in front
            qfd_dv_s8x_kff #(.W(1), .ID(7150 + bk)) u_rce (.ck(ck), .d(pbs_re && bs_word[1:0] == bk[1:0]), .q(m_rce));
            qfd_dv_s8x_kff #(.W(7), .ID(7160 + bk)) u_ra (.ck(ck), .d(bs_word[8:2]), .q(m_ra));
            qfd_dv_s8x_kff #(.W(1), .ID(7170 + bk)) u_we (.ck(ck), .d(twp_w), .q(m_we));
            qfd_dv_s8x_kff #(.W(7), .ID(7180 + bk)) u_wa (.ck(ck), .d(twp_a), .q(m_wa));
            qfd_dv_s8x_kff #(.W(256), .ID(7190 + bk)) u_wd (.ck(ck), .d(twp_d[256*bk +: 256]), .q(m_wd));
        end
        ot_sram_1r1w_128x256_m1_r2c2 u_m (.clk(ck), .r_ce_in(m_rce), .r_addr_in(m_ra),
            .rd_out(bt_rd[bk*256 +: 256]), .w_ce_in(m_we), .w_addr_in(m_wa),
            .wd_in(m_wd), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    reg [1:0] s1b_bank; reg [1023:0] btcap;
    always @(posedge ck) begin s1b_bank <= cap_bank; btcap <= bt_rd; end
    wire [3:0] bdec = 4'd1 << s1b_bank;
    wire [255:0] bs_n;
    generate for (gk = 0; gk < 16; gk = gk + 1) begin : g_bsel
        wire [3:0] boh;
        qfd_dv_s8x_kff #(.W(4), .ID(4000 + gk)) u (.ck(ck), .d(bdec), .q(boh));
        assign bs_n[16*gk +: 16] = ({16{boh[0]}} & btcap[256*0 + 16*gk +: 16]) | ({16{boh[1]}} & btcap[256*1 + 16*gk +: 16]) |
                                   ({16{boh[2]}} & btcap[256*2 + 16*gk +: 16]) | ({16{boh[3]}} & btcap[256*3 + 16*gk +: 16]);
    end endgenerate
    always @(posedge ck) bs_q <= bs_n;
    reg bs_bad_q;
    always @(posedge ck) bs_bad_q <= pbs_re && pbs_addr[23:9] != 0;
    always @(posedge ck or negedge rl1)
        if (!rl1) fault <= 1'b0;
        else fault <= fault | bs_bad_q;
endmodule
