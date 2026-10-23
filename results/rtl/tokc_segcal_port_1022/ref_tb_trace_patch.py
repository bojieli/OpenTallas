#!/usr/bin/env python3
"""TOKc-SEGCAL 10-22: dv-form reference tb = the assembly tb_qfd_tt_ctlm_prog.sv (c0f8097f3) + the per-cycle output trace
(+define+TB_TRACE, the same 2481-bit vector and label as tb_qfd_tt_ctlm_prog_hp13.sv).  Only adds output connections
(tl / emb_position / emb_user) and a $fdisplay; the stimulus and DUT are untouched.   ref_tb_trace_patch.py IN OUT"""
import sys
s = open(sys.argv[1]).read()
s = s.replace("wire [17:0] emb_token; wire [55:0] dc; wire cf;",
              "wire [17:0] emb_token; wire [55:0] dc; wire cf; wire [17:0] emb_position; wire [1:0] emb_user; wire [1087:0] tl;", 1)
s = s.replace(".emb_start(emb_start), .emb_token(emb_token), .cf(cf));",
              ".emb_start(emb_start), .emb_token(emb_token), .emb_position(emb_position), .emb_user(emb_user), .tl(tl), .cf(cf));", 1)
tr = """`ifdef TB_TRACE
    integer tr; reg [1023:0] trf;
    initial begin if (!$value$plusargs("TRACE=%s", trf)) trf = "trace.txt"; tr = $fopen(trf, "w"); end
    wire [2480:0] v_tr = {pobs, csr, lcv, ntk, nps, cst, cobs, dobs, cir, dc, ncmd, hr, cmd, tl, emb_start, emb_token,
                          emb_position, emb_user, cf};
`endif
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
`ifdef TB_TRACE
            $fdisplay(tr, "%0d %h", cyc, v_tr);
`endif
"""
old = """    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
"""
assert s.count(old) == 1 and 'emb_position(emb_position)' in s
s = s.replace(old, tr, 1)
open(sys.argv[2], 'w').write(s)
