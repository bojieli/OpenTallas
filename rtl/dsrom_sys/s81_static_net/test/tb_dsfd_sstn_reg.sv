`timescale 1ns/1ps
// tb_dsfd_sstn_reg: production bench of a generated slot station dsfd_sstn_* / return stage dsfd_rstg with --sstn-reg
// against its specification, every edge, random data, the column reset rs asserted asynchronously and released right
// after a rising edge at random times, valid bits driven high while rs is low (they must read 0):
//   sstn: xa(t+1) = {rs ? xai[282] : 0, xai[281:0]}, xb(t+1) = xbi, cc = cci registered (+CP pad stages), cleared by rs,
//         so(t+1) = rs ? (e0|e1|c0|c1|si|{nf,0}) : 0
//   rstg: o(t+1) = {i[65:1], rs ? i[0] : 0}
module tb_dsfd_sstn_reg;
    reg ck = 0; always #0.5 ck = ~ck;
    reg rs = 0;
`ifdef RSTG
    reg [65:0] i; wire [65:0] o;
    `DUT dut (.ck(ck), .i(i), .o(o), .rs(rs));
`else
    reg [14:0] cci; reg [282:0] xai; reg [265:0] xbi; reg [1:0] c0, e0, c1, e1, si; reg nf;
    wire [1:0] so; wire [282:0] xa; wire [265:0] xb; wire [14:0] cc;
`ifdef HAS_X2
    reg [`X2_W-1:0] x2i; wire [`X2_W-1:0] x2; reg [`X2_W-1:0] m_x2;
`endif
    `DUT dut (.cci(cci), .ck(ck), .rs(rs), .so(so), .xa(xa), .xai(xai), .xb(xb), .xbi(xbi), .c0(c0), .e0(e0)
`ifdef HAS_CC
        , .cc(cc)
`endif
`ifdef HAS_E1
        , .c1(c1), .e1(e1)
`endif
`ifdef HAS_SI
        , .si(si)
`endif
`ifdef HAS_NF
        , .nf(nf)
`endif
`ifdef HAS_X2
        , .x2i(x2i), .x2(x2)
`endif
    );
    reg [14:0] m_rc, m_cp; reg [282:0] m_xa; reg [265:0] m_xb; reg [1:0] m_so;
`endif
    reg [65:0] m_o;
    integer n, bad = 0, chk = 0, seed = 7;
    function automatic [63:0] r64(input integer d); r64 = {$random(seed), $random(seed)}; endfunction
    task drive;
        integer bit_index;
`ifdef RSTG
        i = {r64(0), r64(0)};
        if (!rs) i[0] = 1'b1;
`else
        cci = r64(0); xai = {r64(0), r64(0), r64(0), r64(0), r64(0)}; xbi = {r64(0), r64(0), r64(0), r64(0), r64(0)};
        c0 = $random(seed); e0 = $random(seed); c1 = $random(seed); e1 = $random(seed); si = $random(seed); nf = $random(seed);
        if (!rs) xai[282] = 1'b1;
`ifdef HAS_X2
        for (bit_index = 0; bit_index < `X2_W; bit_index = bit_index + 1) x2i[bit_index] = $random(seed);
        if (!rs) begin x2i[`X2_RESET_0] = 1'b1; x2i[`X2_RESET_1] = 1'b1; end
`endif
`endif
    endtask
    initial begin
        drive; #2.2;
        for (n = 0; n < 4000; n = n + 1) begin
            @(posedge ck);
            // model update at this edge (inputs as driven before it)
`ifdef RSTG
            m_o = {i[65:1], rs ? i[0] : 1'b0};
`else
            m_xa = {rs ? xai[282] : 1'b0, xai[281:0]}; m_xb = xbi;
`ifdef HAS_X2
            m_x2 = x2i; m_x2[`X2_RESET_0] = rs ? x2i[`X2_RESET_0] : 1'b0;
            m_x2[`X2_RESET_1] = rs ? x2i[`X2_RESET_1] : 1'b0;
`endif
            m_cp = rs ? m_rc : 15'd0; m_rc = rs ? cci : 15'd0;
            m_so = rs ? (e0 | c0
`ifdef HAS_E1
                         | e1 | c1
`endif
`ifdef HAS_SI
                         | si
`endif
`ifdef HAS_NF
                         | {nf, 1'b0}
`endif
                         ) : 2'b00;
`endif
            #0.1;
            begin // every observed edge after the declared initial reset interval
`ifdef RSTG
                if (o !== m_o) begin bad = bad + 1; if (bad < 5) $display("SSTN_REG mismatch %0d o %h want %h", n, o, m_o); end
`else
                if (xa !== m_xa || xb !== m_xb || so !== m_so) begin bad = bad + 1; if (bad < 5) $display("SSTN_REG mismatch %0d xa[282] %b want %b so %b want %b", n, xa[282], m_xa[282], so, m_so); end
`ifdef HAS_X2
                if (x2 !== m_x2) begin bad = bad + 1; if (bad < 5) $display("SSTN_REG x2 mismatch %0d got %h want %h", n, x2, m_x2); end
`endif
`ifdef HAS_CC
`ifdef CP
                if (cc !== m_cp) begin bad = bad + 1; if (bad < 5) $display("SSTN_REG cc mismatch %0d", n); end
`else
                if (cc !== m_rc) begin bad = bad + 1; if (bad < 5) $display("SSTN_REG cc mismatch %0d", n); end
`endif
`endif
`endif
                chk = chk + 1;
            end
            // column reset: release right after an edge, assert asynchronously mid-cycle
            if (!rs && ($random(seed) & 7) == 0) rs = 1'b1;
            drive;
            if (rs && ($random(seed) & 63) == 0) begin #0.2 rs = 1'b0;
`ifdef RSTG
                m_o[0] = 1'b0;
`else
                m_xa[282] = 1'b0; m_rc = 0; m_cp = 0; m_so = 0;
`ifdef HAS_X2
                m_x2[`X2_RESET_0] = 0; m_x2[`X2_RESET_1] = 0;
`endif
`endif
                #0.1;
`ifdef RSTG
                if (o[0] !== 1'b0) begin bad = bad + 1; $display("SSTN_REG async clear missing"); end
`else
                if (xa[282] !== 1'b0 || so !== 2'b00) begin bad = bad + 1; $display("SSTN_REG async clear missing"); end
`ifdef HAS_X2
                if (x2[`X2_RESET_0] !== 1'b0 || x2[`X2_RESET_1] !== 1'b0) begin bad = bad + 1; $display("SSTN_REG x2 async clear missing"); end
`endif
`endif
                drive;
            end
            // Change the input after the falling edge as well: a falling-edge
            // payload mutant must not pass a rising-edge station calendar.
            @(negedge ck); #0.2; drive;
        end
        if (bad) begin $display("SSTN_REG FAIL %0d mismatches", bad); $fatal(1); end
        $display("SSTN_REG PASS %0d edges exact incl. async column reset", chk);
`ifdef HAS_X2
        $display("SSTN_REG X2 COVERAGE width=%0d words=%0d checked_bits=%0d reset_bits=%0d,%0d normal_data_edges=1", `X2_W, chk, `X2_W*chk, `X2_RESET_0, `X2_RESET_1);
`endif
        $finish;
    end
endmodule
