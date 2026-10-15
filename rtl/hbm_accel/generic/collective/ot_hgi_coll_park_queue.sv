// One epoch queue per hardened clock root. All payload inputs capture unconditionally; valid/tag steer locally.
module ot_hgi_coll_park_queue #(
    parameter integer EQ    = 4,
    parameter integer QID   = 0,
    parameter integer PPK   = 512,
    parameter integer DEL   = 4,
    parameter integer PWT   = 545,
    parameter integer MACRO = 2,        // ot_fifo_sram_fwft MACRO: 2 = ot_sram_1r1w_128x256 (PPK / DEL <= 128)
    parameter integer MUT_PARK = 0,     // bench mutant: 1 = bank index ignored (every lane writes bank 0)
    // PSTAGE 1 (A4 2026-10-14, Q1 wg1-3767878c8 TT -62.14 / al1-42a8b643a TT -81.99: pin flop r_v -> bank decode ->
    // ~400 um push / bypass broadcast over the bank row -> ESL slice enables): each bank registers its decoded push and
    // write word next to the bank (one more park edge; drain order and capacity unchanged).  0 = the closed Q0/Q2/Q3 form.
    parameter integer PSTAGE = 0
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire [DEL-1:0]               pv,
    input  wire [DEL*$clog2(EQ)-1:0]    pq,
    input  wire [DEL*$clog2(DEL)-1:0]   ps,
    input  wire [DEL*PWT-1:0]           pd,
    output wire                         hv,
    output wire [PWT-1:0]               hd,
    input  wire                         pop,
    output wire [DEL-1:0]                bank_ovf
);
    localparam integer QB = (EQ > 1) ? $clog2(EQ) : 1;
    localparam integer SB = (DEL > 1) ? $clog2(DEL) : 1;
    localparam integer BD = PPK / DEL;
    initial if (BD * DEL != PPK) $fatal(1, "ot_hgi_coll_park: PPK must be a multiple of DEL");

    // ---- reset: the rst_n port drives only ot_rst_relay; region c = queue c (banks + head), region EQ = pin flops ----
    wire [1:0] rn;
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rn));
    // ---- pin flops (park side): valid reset, payload not ---------------------------------------------------------
    reg [DEL-1:0]     r_v;
    reg [QB-1:0]      r_q [0:DEL-1];
    reg [SB-1:0]      r_s [0:DEL-1];
    reg [PWT-1:0]     r_d [0:DEL-1];
    integer l;
    reg               pop_r;
    always @(posedge clk or negedge rn[1])
        if (!rn[1]) begin r_v <= '0; pop_r <= '0; end else begin r_v <= pv; pop_r <= pop; end
    always @(posedge clk)
        for (l = 0; l < DEL; l = l + 1) begin
            r_q[l] <= pq[l*QB +: QB];
            r_s[l] <= (MUT_PARK == 1) ? '0 : ps[l*SB +: SB];
            r_d[l] <= pd[l*PWT +: PWT];
        end

    // ---- banks ---------------------------------------------------------------------------------------------------
    wire [DEL-1:0]        b_hv, b_ovf;
    assign bank_ovf = b_ovf;
    wire [PWT-1:0]        b_hd [0:DEL-1];
    genvar c, b;
    generate begin : g_q
        reg  [SB-1:0]  hb;                     // bank of the next flit to load into the output register
        reg            ohv; reg [PWT-1:0] ohd;  // registered queue head
        wire           ld;                     // load the output register from the head bank this edge
        assign hv = ohv; assign hd = ohd;
        for (b = 0; b < DEL; b = b + 1) begin : g_b
            reg            push; reg [PWT-1:0] wd;
            integer        k;
            always @* begin
                push = 1'b0; wd = '0;
                for (k = 0; k < DEL; k = k + 1)
                    if (r_v[k] && r_q[k] == QB'(QID) && r_s[k] == b[SB-1:0]) begin push = 1'b1; wd = wd | r_d[k]; end
            end
            wire bpop = ld && hb == b[SB-1:0];
            wire bpush; wire [PWT-1:0] bwd;
            if (PSTAGE != 0) begin : g_ps
                reg ps_v; reg [PWT-1:0] ps_d;
                always @(posedge clk or negedge rn[0]) if (!rn[0]) ps_v <= 1'b0; else ps_v <= push;
                always @(posedge clk) ps_d <= wd;
                assign bpush = ps_v; assign bwd = ps_d;
            end else begin : g_nps
                assign bpush = push; assign bwd = wd;
            end
            ot_coll_park_fifo #(.W(PWT), .DEPTH(BD), .MACRO(MACRO), .ESL(32)) u_f (.clk(clk), .rst_n(rn[0]), .push(bpush), .wdata(bwd),
                .pop(bpop), .hv(b_hv[b]), .head(b_hd[b]), .ovf(b_ovf[b]));
        end
        // registered queue head: (re)load when empty or popped last edge, from the head bank's FWFT head
        assign ld = (!ohv || pop_r) && b_hv[hb];
        always @(posedge clk or negedge rn[0])
            if (!rn[0]) begin ohv <= 1'b0; hb <= '0; end
            else begin
                if (ld) begin ohv <= 1'b1; hb <= (DEL > 1) ? SB'((hb + 1) % DEL) : '0; end
                else if (pop_r) ohv <= 1'b0;
            end
        always @(posedge clk) if (ld) ohd <= b_hd[hb];
    end endgenerate

endmodule
