`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// LEAD2-S81/TOK2 (2026-10-19): ot_s81sl_cap_ld = static delay of ONE 70-bit CAP return lane before the capture tree.
// Why: the CAP-ED23 fullsix rerun (tok2-capd/fullsix_capd23) still faulted (0002 at 1801): the W tree carries FOUR frames
// (lanes 0..3 = L01 L02 L03 R01; R01 is W lane 3), so an E-only delay cannot separate them (exact packing: NONE for any D).
// Exact packing (cap_ed_calendar/root_pack_nosym.py, s_16_24.json): W lane 3 +16 and the E column +24 give a legal
// six-frame calendar (44 words, 1773..1820).  This leaf delays W lane 3 by D = 16 (ot_s81sl_cap #(.WL3DLY(16))).
// Structure: ot_hdc_delay_rf 70 x (D-2) register-file ring (pin in reg -> RF -> pin out reg; 980 b at D = 16 < 2 kb), the
// lane's valid bit (bit 0) masked until the line is primed (no stale word is ever valid).  Static: the compiler owns D.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cap_ld #(
    parameter integer D = 16
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [69:0] i_w,
    output wire [69:0] o_w
);
    wire [1:0] rsv;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire [69:0] q;
`ifndef OT_S81_CAP_LD_FACE_VALID
    ot_hdc_delay_rf #(.W(70), .D(D)) u_dl (.clk(clk), .rst_n(rsv[0]), .d(i_w), .q(q));
`else
    // Same D-edge register-file delay; capture the post-edge valid mask in
    // the existing output register. No payload or calendar edge moves.
    localparam integer FACE_N = D - 2;
    localparam integer FACE_K = (FACE_N <= 2) ? 1 : $clog2(FACE_N);
    localparam [FACE_K-1:0] FACE_LAST = FACE_N - 1;
    reg [69:0] face_din;
    reg [69:0] face_mem [0:FACE_N-1];
    reg [FACE_K-1:0] face_wptr;
    reg [68:0] face_dout;
    reg face_valid;
`ifndef SYNTHESIS
    initial face_wptr = 0;
`endif
    always @(posedge clk) begin
        face_din <= i_w;
        face_mem[face_wptr] <= face_din;
        face_dout <= face_mem[face_wptr][69:1];
        face_wptr <= (face_wptr >= FACE_LAST) ? 0 : face_wptr + 1'b1;
    end
    always @(posedge clk or negedge rsv[1])
        if (!rsv[1]) face_valid <= 1'b0;
        else face_valid <= face_mem[face_wptr][0] && (primed || cnt == D[CW-1:0]);
    assign q = {face_dout, face_valid};
`endif
    localparam integer CW = $clog2(D + 2);
    reg [CW-1:0] cnt; reg primed;
    always @(posedge clk or negedge rsv[1])
        if (!rsv[1]) begin cnt <= {CW{1'b0}}; primed <= 1'b0; end
        else if (!primed) begin cnt <= cnt + 1'b1; primed <= (cnt == D[CW-1:0]); end
`ifdef OT_S81_CAP_LD_FACE_VALID
    assign o_w = q;
`else
    assign o_w = {q[69:1], q[0] && primed};
`endif
endmodule
`default_nettype wire
