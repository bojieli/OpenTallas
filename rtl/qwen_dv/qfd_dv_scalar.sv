`timescale 1ns/1ps
// =====================================================================================================================
// qfd_dv_scalar -- the Q-DV slice's scalar-tree face and (when configured as root) the global-sum root.
//
// Scalar word (96 b):  [95] v, [94:92] kind (1 PSUM = a block partial sum, 2 RB = a broadcast scalar), [91:88] src
// slice, [87:64] idx (PSUM: block index 0..31; RB: the receivers' VM element address), [63:32] 0, [31:0] value.
// Port behaviour (static schedule; a pass word and an own word on the same edge is a sticky fault, never a stall):
//   in PSUM : root -> absorbed into its block slot; other slices -> passed on (registered, one edge)
//   in RB   : src == this slice -> absorbed (the ring has delivered it to every slice); else written into the local
//             VM at idx (w1) and passed on
//   own PSUM (the reducer's block sum, red window 11): root -> its block slot; else -> sent
//   own RB   (an SU write to window 11; the local VM write is done by the slice top) -> sent with src = this slice
// ROOT: after `nb` block sums of the armed op are in (any arrival order: they are filed by idx), the root adds them by
// the golden pairwise tree ((s0 + s1) + (s2 + s3)) + ... padded with +0 to a power of two (R-ARITH: each block sum is
// an aligned 16-chunk subtree of the csum8 tree, so this is csum8 over the whole vector), one pipelined
// ot_hdc_qadd (the SU's adder), and writes the total into the local VM at ss_addr (w1).
// MUT 1 (bench negative control): the root folds the block sums sequentially (((s0 + s1) + s2) + ...) (must FAIL).
// =====================================================================================================================
module qfd_dv_scalar #(
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [3:0]    sid,          // slice id (strap, pin-registered by the top)
    input  wire          cfg_v,
    input  wire          cfg_root,
    input  wire [5:0]    cfg_nb,       // 1 .. 32
    input  wire [23:0]   cfg_ss,
    input  wire [95:0]   sc_i,         // pin-registered by the top
    output reg  [95:0]   sc_o,
    input  wire          ps_v,         // own block sum
    input  wire [23:0]   ps_idx,
    input  wire [31:0]   ps_val,
    input  wire          rb_v,         // own broadcast scalar
    input  wire [23:0]   rb_idx,
    input  wire [31:0]   rb_val,
    output reg           w1_we,
    output reg  [23:0]   w1_addr,
    output reg  [31:0]   w1_data,
    output reg           busy,
    output reg           fault
);
    localparam [2:0] K_PSUM = 3'd1, K_RB = 3'd2;
    reg        root; reg [5:0] nb; reg [23:0] ss;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin root <= 1'b0; nb <= 6'd0; ss <= 24'd0; end
        else if (cfg_v) begin root <= cfg_root; nb <= cfg_nb; ss <= cfg_ss; end
    wire        iv = sc_i[95];
    wire [2:0]  ik = sc_i[94:92];
    wire [3:0]  is = sc_i[91:88];
    wire        in_ps = iv && ik == K_PSUM;
    wire        in_rb = iv && ik == K_RB;
    wire        pass = (in_ps && !root) || (in_rb && is != sid);
    wire        own_ps_out = ps_v && !root;
    // -------------------------------------------------------------- the out port
    always @(posedge ck or negedge rst_n)
        if (!rst_n) sc_o <= 96'd0;
        else if (pass) sc_o <= sc_i;
        else if (own_ps_out) sc_o <= {1'b1, K_PSUM, sid, ps_idx, 32'd0, ps_val};
        else if (rb_v) sc_o <= {1'b1, K_RB, sid, rb_idx, 32'd0, rb_val};
        else sc_o <= 96'd0;
    // -------------------------------------------------------------- root slots
    reg [31:0] s [0:31];
    reg [5:0]  cnt;
    wire       in_root = in_ps && root;
    wire       own_root = ps_v && root;
    // combine engine
    localparam [1:0] S_IDLE = 2'd0, S_ISSUE = 2'd1, S_DRAIN = 2'd2, S_OUT = 2'd3;
    reg [1:0]  st;
    reg [5:0]  m;            // items at this level (power of two)
    reg [4:0]  ip;           // pair index being issued
    reg [3:0]  dr;           // drain counter
    function automatic [5:0] p2ceil(input [5:0] n);
        begin
            if (n <= 1) p2ceil = 6'd1; else if (n <= 2) p2ceil = 6'd2; else if (n <= 4) p2ceil = 6'd4;
            else if (n <= 8) p2ceil = 6'd8; else if (n <= 16) p2ceil = 6'd16; else p2ceil = 6'd32;
        end
    endfunction
    // the adder (latency 3) and its tag line (destination slot)
    reg         av;
    reg  [31:0] aa, ab;
    reg  [4:0]  at;
    wire [31:0] ay;
    wire        af;
    ot_hdc_qadd #(.L(3)) u_add (.clk(ck), .rst_n(rst_n), .v(av), .a(aa), .b(ab), .y(ay), .fault(af));
    wire [5:0]  td;
    ot_hdc_delay #(.W(6), .D(3), .RESET(1)) u_tag (.clk(ck), .rst_n(rst_n), .d({av, at}), .q(td));
    wire        rv = td[5];
    wire [4:0]  rt = td[4:0];
    integer k;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            cnt <= 6'd0; st <= S_IDLE; m <= 6'd0; ip <= 5'd0; dr <= 4'd0; av <= 1'b0;
        end else begin
            av <= 1'b0;
            if (cfg_v) begin
                cnt <= 6'd0; st <= S_IDLE;
                for (k = 0; k < 32; k = k + 1) s[k] <= 32'd0;
            end else begin
                if (st == S_IDLE) begin
                    if (in_root) s[sc_i[68:64]] <= sc_i[31:0];
                    if (own_root) s[ps_idx[4:0]] <= ps_val;
                    if (cnt + (in_root ? 6'd1 : 6'd0) + (own_root ? 6'd1 : 6'd0) == nb && nb != 6'd0 &&
                        (in_root || own_root)) begin
                        st <= S_ISSUE; m <= (MUT == 1) ? nb : p2ceil(nb); ip <= 5'd0; cnt <= 6'd0;
                    end else
                        cnt <= cnt + (in_root ? 6'd1 : 6'd0) + (own_root ? 6'd1 : 6'd0);
                end else if (st == S_ISSUE) begin
                    if (MUT == 1) begin
                        // sequential fold: one add at a time, result back into s[0]
                        if (m <= 6'd1) st <= S_OUT;
                        else begin
                            av <= 1'b1; aa <= s[0]; ab <= s[6'd1 + {1'b0, ip}]; at <= 5'd0;
                            ip <= ip + 5'd1; st <= S_DRAIN; dr <= 4'd5;
                            m <= m - 6'd1;
                        end
                    end else if (m <= 6'd1) st <= S_OUT;
                    else begin
                        av <= 1'b1; aa <= s[{ip, 1'b0}]; ab <= s[{ip, 1'b1}]; at <= ip;
                        if ({1'b0, ip} + 6'd1 == (m >> 1)) begin st <= S_DRAIN; dr <= 4'd5; end
                        ip <= ip + 5'd1;
                    end
                end else if (st == S_DRAIN) begin
                    if (dr == 4'd0) begin
                        st <= S_ISSUE;
                        if (MUT != 1) begin m <= m >> 1; ip <= 5'd0; end
                    end else dr <= dr - 4'd1;
                end else if (st == S_OUT) begin
                    st <= S_IDLE;
                end
                if (rv) s[rt] <= ay;
            end
        end
    end
    // -------------------------------------------------------------- VM writes: RB tap, root total
    wire tap_rb = in_rb && is != sid;
    wire tot = (st == S_OUT);
    always @(posedge ck or negedge rst_n)
        if (!rst_n) w1_we <= 1'b0;
        else w1_we <= tap_rb || tot;
    always @(posedge ck) begin
        w1_addr <= tap_rb ? sc_i[87:64] : ss;
        w1_data <= tap_rb ? sc_i[31:0] : s[0];
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) busy <= 1'b0;
        else busy <= (st != S_IDLE);
    // -------------------------------------------------------------- faults
    wire bad = (pass && (own_ps_out || rb_v)) || (own_ps_out && rb_v) || (tap_rb && tot) ||
               (iv && ik != K_PSUM && ik != K_RB) ||
               ((in_root || own_root) && st != S_IDLE) || (rv && af) ||
               (in_root && (sc_i[87:69] != 0 || sc_i[68:64] >= {1'b0, nb[4:0]} && nb != 6'd32)) ||
               (own_root && (ps_idx[23:5] != 0 || ps_idx[4:0] >= {1'b0, nb[4:0]} && nb != 6'd32));
    always @(posedge ck or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else fault <= fault | bad;
endmodule
