module dsdv_idx_qf_old #(
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [7:0]    uid,        // die tree uid (die configuration input)
    input  wire [512:0]  qs,         // local frame source (s_3S)
    input  wire [512:0]  ql,         // parent tree link
    output reg  [512:0]  qr,         // -> irg_00 qi
    output reg  [512:0]  qc0,        // -> child link 0
    output reg  [512:0]  qc1,        // -> child link 1
    output reg  [3:0]    st          // {no-entry seen, bad frame, collision, fault}
);
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg [512:0] qs_r, ql_r, s1;
    reg [7:0]   me;
    always @(posedge ck or negedge rn)
        if (!rn) begin qs_r[0] <= 1'b0; ql_r[0] <= 1'b0; s1[0] <= 1'b0; qc0[0] <= 1'b0; qc1[0] <= 1'b0; me <= 8'd0; end
        else begin
            qs_r[0] <= qs[0]; ql_r[0] <= ql[0]; s1[0] <= qs_r[0] | ql_r[0];
            qc0[0] <= s1[0]; qc1[0] <= s1[0]; me <= uid;
        end
    always @(posedge ck) begin
        qs_r[512:1] <= qs[512:1]; ql_r[512:1] <= ql[512:1];
        s1[512:1] <= (qs_r[0] ? qs_r[512:1] : 512'd0) | (ql_r[0] ? ql_r[512:1] : 512'd0);
        qc0[512:1] <= s1[512:1]; qc1[512:1] <= s1[512:1];
    end
    wire        v  = s1[0];
    wire [511:0] d = s1[512:1];
    // framing
    reg         infr, tree, hit;
    reg  [11:0] left;
    reg  [3:0]  nsl;                    // spec words left
    reg  [511:0] hdr;
    reg  [106:0] spec;
    wire [7:0]  want = (MUT == 1) ? me + 8'd1 : me;
    reg  [106:0] w_spec; reg w_hit;
    integer e;
    always @* begin
        w_spec = 107'd0; w_hit = 1'b0;
        for (e = 0; e < 4; e = e + 1)
            if (d[128 * e + 127] && d[128 * e + 119 +: 8] == want) begin w_spec = d[128 * e +: 107]; w_hit = 1'b1; end
    end
    reg [3:0] fl;
    always @(posedge ck or negedge rn)
        if (!rn) begin infr <= 1'b0; tree <= 1'b0; hit <= 1'b0; left <= 0; nsl <= 0; qr[0] <= 1'b0; fl <= 4'd0; st <= 4'd0; end
        else begin
            qr[0] <= 1'b0;
            if (qs_r[0] && ql_r[0]) fl[1] <= 1'b1;
            if (v) begin
                if (!infr) begin                                          // header
                    infr <= d[491:480] != 12'd0; left <= d[491:480];
                    tree <= d[511:508] == 4'd10; hit <= 1'b0;
                    if (d[511:508] == 4'd10) begin
                        hdr <= d; nsl <= d[3:0];
                        if (d[3:0] == 4'd0 || d[491:480] != 12'(64) + 12'(d[3:0])) fl[2] <= 1'b1;
                    end else qr[0] <= 1'b1;                               // other frames pass
                end else begin
                    left <= left - 12'd1;
                    if (left == 12'd1) infr <= 1'b0;
                    if (tree && nsl != 4'd0) begin                       // spec word
                        nsl <= nsl - 4'd1;
                        if (w_hit) begin spec <= w_spec; hit <= 1'b1; end
                        if (nsl == 4'd1) begin
                            if (w_hit || hit) qr[0] <= 1'b1;             // this die's header goes out now
                            else fl[3] <= 1'b1;
                        end
                    end else if (!tree || hit) qr[0] <= 1'b1;            // query words (or another frame's payload)
                end
            end
            st <= {fl[3], fl[2], fl[1], fl[1] | fl[2]};
        end
    // data path of qr (header rewrite in the cycle of the last spec word)
    wire [106:0] my_spec = w_hit ? w_spec : spec;
    always @(posedge ck) begin
        if (v && infr && tree && nsl == 4'd1) begin
            qr[512:1] <= 512'd0;
            qr[512:509] <= 4'd4; qr[503:496] <= hdr[502:495]; qr[492:481] <= 12'd64; qr[459:450] <= hdr[458:449];
            qr[107:1] <= my_spec;
        end else qr[512:1] <= d;
    end
endmodule
