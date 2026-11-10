"""DIE-QC-97 WLIVE-1: no kept write-enable flop for a write chunk that holds only cas padding bits.  argv: file..."""
import sys
for p in sys.argv[1:]:
    s = open(p).read()
    def rep(old, new):
        global s
        assert s.count(old) == 1, (p, old[:60], s.count(old)); s = s.replace(old, new)
    rep("""    parameter int READ_CHUNK = 0, // optional bounded arbitrary-width read chunks; 0 preserves legacy64/divisibility
    // RSTREP-1: copies""" if "RSTN = 0" in s else """    parameter int READ_CHUNK = 0 // optional bounded arbitrary-width read chunks; 0 preserves legacy64/divisibility
) (
    input  logic         tclk,""",
        ("""    parameter int READ_CHUNK = 0, // optional bounded arbitrary-width read chunks; 0 preserves legacy64/divisibility
    // WLIVE-1 (DIE-QC-97): live bits of t_d (the cas bundle W before 64-bit padding); a write chunk wholly above it
    // writes only constant padding, so its write-enable flop takes D = 0 (the start has no unproven sink).  Default W: every chunk.
    parameter int WLIVE = W,
    // RSTREP-1: copies""" if "RSTN = 0" in s else """    parameter int READ_CHUNK = 0, // optional bounded arbitrary-width read chunks; 0 preserves legacy64/divisibility
    // WLIVE-1 (DIE-QC-97): live bits of t_d (the cas bundle W before 64-bit padding); a write chunk wholly above it
    // writes only constant padding, so its write-enable flop takes D = 0 (the start has no unproven sink).  Default W: every chunk.
    parameter int WLIVE = W
) (
    input  logic         tclk,"""))
    rep("""            for (genvar c = 0; c < WNC; c++) begin : ch
                (* keep = "true" *) ot_meso_wen_ff #(.NEG(WEN_NEG)) u_wen (.clk(wen_clk), .d(t_rst_n && (slot_nx == AW'(i))),
                                                         .q(wen[i * WNC + c]));
            end""", """            for (genvar c = 0; c < WNC; c++) begin : ch
                // WLIVE-1: a padding-only chunk's enable flop keeps its name/site but takes D = 0 (no start load)
                (* keep = "true" *) ot_meso_wen_ff #(.NEG(WEN_NEG)) u_wen (.clk(wen_clk),
                    .d((c * WWC < WLIVE) ? (t_rst_n && (slot_nx == AW'(i))) : 1'b0), .q(wen[i * WNC + c]));
            end""")
    rep(".WRITE_TAIL(WRITE_TAIL), .READ_CHUNK(READ_CHUNK)", ".WRITE_TAIL(WRITE_TAIL), .READ_CHUNK(READ_CHUNK), .WLIVE(W)")
    open(p, "w").write(s)
    print("patched", p)
