"""Add the opt-in compiler-owned BF issue edge without changing the qx arithmetic.

Used only for the split BF front core. The caller owns all programme register
ages; these ports describe the edge at which c_issue is asserted.
"""

def transform(fc):
    def replace(old, new):
        nonlocal fc
        assert fc.count(old) == 1, (old, fc.count(old))
        fc = fc.replace(old, new)

    replace('    parameter INSTANCE = ""', '''    // Programme ports are synchronous to the actual core issue edge. No
    // availability signal may qualify this strobe or advance its calendar.
    parameter integer STATIC_PROGRAM = 0,
    parameter INSTANCE = ""''')
    replace('    input  wire [NB-1:0] c_qy_bkf', '''    input  wire [NB-1:0] c_qy_bkf,
    input  wire          prog_issue_pin,
    input  wire [13:0]   prog_addr_pin,
    input  wire [14:0]   prog_operand_pin, // {family, position[2:0], block[2:0], unit[7:0]}
    input  wire [$clog2(NSEG)-1:0] prog_segment_pin,
    input  wire          prog_half_pin,
    input  wire [$clog2(NCH)-1:0] prog_chain_pin''')
    replace('    wire issue = w_run && f_cnt != 0 && !((QX >= 5) ? hazard_r : hazard) && !pp_block && !(BP != 0 && bp_hold != 3\'d0);', '''    // A programmed issue is unconditional. The original issue predicate is
    // retained only for legacy operation and as a static contract checker.
    wire issue_available = w_run && f_cnt != 0 && !((QX >= 5) ? hazard_r : hazard) && !pp_block && !(BP != 0 && bp_hold != 3'd0);
    wire issue = (STATIC_PROGRAM != 0) ? prog_issue_pin : issue_available;''')
    replace('    reg ffault;', '''    reg ffault_dynamic;
    reg programme_fault;
    wire ffault = ffault_dynamic | programme_fault;
    // Check the identity actually captured alongside the FIFO data, rather
    // than deriving an expected identity from a count of successful issues.
    wire [7:0] programme_unit = c_u0[w_c] + 8'(w_uabs);
    wire [14:0] programme_operand = {fam, w_pos, w_b, programme_unit};
    wire programme_bad = !issue_available || go_e ||
        prog_addr_pin != a_ctr || prog_operand_pin != programme_operand ||
        prog_segment_pin != w_s || prog_half_pin != w_h ||
        prog_chain_pin != w_cnt || f_identity[f_rd] != programme_operand;
    // Free clock: even a stray programme strobe while the ICG is closed is
    // diagnosed. Fault state cannot gate any issue or walker/retire enable.
    always @(posedge clk or negedge rst_n)
        if (!rst_n) programme_fault <= 1'b0;
        else if (STATIC_PROGRAM != 0 && prog_issue_pin && programme_bad)
            programme_fault <= 1'b1;''')
    # The original sticky fault still records FIFO overflow and BP violations.
    fc = fc.replace('ffault <=', 'ffault_dynamic <=')
    replace('    reg [XW:0]  f_cnt;', '''    reg [XW:0]  f_cnt;
    reg [14:0] f_identity [0:XF-1];
    reg [14:0] fw_identity;
    reg [31:0] xbu_identity;
    reg [5:0] xbb_identity;
    always @(posedge gclk) begin
        fw_identity <= {1'b0, xs_pos_e, xs_b_e, xs_p_e};
        xbu_identity <= xb_u_e;
        xbb_identity <= {xb_pos_e, xb_b_e};
    end
    wire [31:0] b_identity_units = FAST != 0 ? xbu_identity : xb_u_e;
    wire [5:0] b_identity_pb = FAST != 0 ? xbb_identity : {xb_pos_e, xb_b_e};''')
    replace('''            f_q0[f_wr] <= FAST != 0 ? fw_q0 : xs_q0_e; f_e0[f_wr] <= FAST != 0 ? fw_e0 : xs_e0_e;''', '''            f_identity[f_wr] <= FAST != 0 ? fw_identity : {1'b0, xs_pos_e, xs_b_e, xs_p_e};
            f_q0[f_wr] <= FAST != 0 ? fw_q0 : xs_q0_e; f_e0[f_wr] <= FAST != 0 ? fw_e0 : xs_e0_e;''')
    replace('''            if (bmu[bk]) f_q0[f_wr + bpre[bk]] <= xbd[256*bk +: 256];''', '''            if (bmu[bk]) begin
                f_q0[f_wr + bpre[bk]] <= xbd[256*bk +: 256];
                f_identity[f_wr + bpre[bk]] <= {1'b1, b_identity_pb, b_identity_units[8*bk +: 8]};
            end''')
    return transform_fclk(transform_frd(fc))


def transform_frd(fc):
    """Clock-structure pass 2026-10-15 (gate ec84ce526: f_rd[1] drove 4,378 read-mux loads, f_rd[0] 2,191): in the
    static programme every read slice selects with its own copy of the read pointer (0 cycles)."""
    def replace(old, new):
        nonlocal fc
        assert fc.count(old) == 1, (old, fc.count(old))
        fc = fc.replace(old, new)

    replace('    reg [XW-1:0] f_wr, f_rd;', """    reg [XW-1:0] f_wr, f_rd;
    // FIFO read data. Static programme: 17 kept read-pointer copies (16 x 32-bit q0/q1 slices + the exponent/identity
    // slice), each loaded with f_rd's own next state on the same edge (0 cycles, <= ~270 mux loads per copy bit);
    // physical/common_flow/ot_keep_regs.tcl keeps the copies apart. Legacy: the original single pointer.
    wire [255:0] rd_q0, rd_q1;
    wire [9:0] rd_e0, rd_e1;
    wire [14:0] rd_id;""")
    replace("prog_chain_pin != w_cnt || f_identity[f_rd] != programme_operand;",
            "prog_chain_pin != w_cnt || rd_id != programme_operand;")
    replace("""        i1_q0 <= (use_hi && QPIPE == 0) ? f_q1[f_rd] : f_q0[f_rd];
        i1_e0 <= (use_hi && QPIPE == 0) ? f_e1[f_rd] : f_e0[f_rd];""", """        i1_q0 <= (use_hi && QPIPE == 0) ? rd_q1 : rd_q0;
        i1_e0 <= (use_hi && QPIPE == 0) ? rd_e1 : rd_e0;""")
    replace("        i1_q1 <= f_q1[f_rd]; i1_e1 <= f_e1[f_rd];", "        i1_q1 <= rd_q1; i1_e1 <= rd_e1;")
    replace("""    // QPIPE: the FP8 half select is applied one stage later (i1 holds both slices and the select)
    reg i1_uh;""", """    if (STATIC_PROGRAM != 0) begin : g_frd
        localparam integer FRC = 17;
        (* keep *) reg [FRC*XW-1:0] f_rdc;
        always @(posedge gclk or negedge rst_n)
            if (!rst_n) f_rdc <= '0;
            else if (go_em) f_rdc <= '0;
            else if (pop) for (int k = 0; k < FRC; k++)
`ifdef BF_FRD_MUTANT_COPY
                if (k != 0) f_rdc[XW*k +: XW] <= f_rdc[XW*k +: XW] + 1'b1;     // negative control: slice 0 copy stalls
`else
                f_rdc[XW*k +: XW] <= f_rdc[XW*k +: XW] + 1'b1;
`endif
        genvar fs;
        for (fs = 0; fs < 8; fs = fs + 1) begin : g_s
            assign rd_q0[32*fs +: 32] = f_q0[f_rdc[XW*fs +: XW]][32*fs +: 32];
            assign rd_q1[32*fs +: 32] = f_q1[f_rdc[XW*(8+fs) +: XW]][32*fs +: 32];
        end
        assign rd_e0 = f_e0[f_rdc[XW*16 +: XW]]; assign rd_e1 = f_e1[f_rdc[XW*16 +: XW]];
        assign rd_id = f_identity[f_rdc[XW*16 +: XW]];
`ifdef BF_FRD_CHECK
        always @(negedge clk) if (rst_n) for (int k = 0; k < FRC; k++) if (f_rdc[XW*k +: XW] !== f_rd) begin
            $display("BF_FRD_CHECK FAIL: copy %0d %0d != f_rd %0d at %t", k, f_rdc[XW*k +: XW], f_rd, $time); $fatal(1);
        end
`endif
    end else begin : g_frd1
        assign rd_q0 = f_q0[f_rd]; assign rd_q1 = f_q1[f_rd]; assign rd_e0 = f_e0[f_rd]; assign rd_e1 = f_e1[f_rd];
        assign rd_id = f_identity[f_rd];
    end
    // QPIPE: the FP8 half select is applied one stage later (i1 holds both slices and the select)
    reg i1_uh;""")
    return fc


def transform_fclk(fc):
    """BF clock-structure pass 2 (2026-10-15, route s81bf_front_static_clk-c2 EARLY_FAIL_HOLD): in the static
    programme every free-clock core register sits below one always-enabled ICG (u_fcg), the same gating depth as
    the gated core (u_cg clones), so free -> gated core paths stop crossing a ~90 ps two-level tree imbalance
    (hi0q_r 236.8 ps -> b_hi 329.1 ps). The ICG enable registers (u_z, u_ze) and the ICGs stay on the root clock.
    The programme word is registered here on that clock (was programme_core_q in the front, on the root)."""
    import re

    def replace(old, new, cnt=1):
        nonlocal fc
        assert fc.count(old) == cnt, (old, fc.count(old))
        fc = fc.replace(old, new)

    replace("    input  wire [$clog2(NCH)-1:0] prog_chain_pin\n);\n", """    input  wire [$clog2(NCH)-1:0] prog_chain_pin
);
    // fclk: free-running core clock below one always-enabled ICG (static programme), same depth as gclk.
    wire fclk;
    if (STATIC_PROGRAM != 0) begin : g_fcg
        // A real core-root reset state drives the low-phase enable latch. The bypass
        // keeps the first post-reset edge, then the latch takes over during low phase.
        (* keep *) reg fcg_arm, fcg_en;
        always @(posedge clk or negedge rst_n_pin) if (!rst_n_pin) fcg_arm <= 1'b0; else fcg_arm <= 1'b1;
        always_latch if (!clk) fcg_en <= fcg_arm;
        ot_hdc_cg u_fcg (.clk(clk), .en(fcg_en | !fcg_arm), .gclk(fclk));
    end else begin : g_nofcg
        assign fclk = clk;
    end
""")
    head, body = fc.split('    wire fclk;\n', 1)
    body = body.replace('posedge clk ', 'posedge fclk ').replace('posedge clk)', 'posedge fclk)')
    for k in ('u_gn', 'u_gw', 'u_gm'):
        body = body.replace(f'{k} (.clk(clk)', f'{k} (.clk(fclk)')
    fc = head + '    wire fclk;\n' + body
    # programme register (+1 edge, was in the front)
    anchor = '    wire issue = (STATIC_PROGRAM != 0) ? prog_issue_pin : issue_available;'
    names = [('issue', '1'), ('addr', '14'), ('operand', '15'), ('segment', '$clog2(NSEG)'), ('half', '1'), ('chain', '$clog2(NCH)')]
    decl = ''.join(f'    reg [{w}-1:0] prog_{n}_q;\n' for n, w in names)
    regs = ' '.join(f'prog_{n}_q <= prog_{n}_pin;' for n, w in names)
    zero = ' '.join(f"prog_{n}_q <= '0;" for n, w in names)
    sel = ''.join(f'    wire [{w}-1:0] prog_{n}_u = (BYP != 0) ? prog_{n}_pin : prog_{n}_q;\n' for n, w in names)
    blk = ('    // Programme word registered on the core clock (latched io_clk pin word -> core flop), +1 edge vs the pin flop;\n'
           '    // the producer emits one edge earlier (ot_s81_bf_prog_seq DELTA -1).\n' + decl +
           '    always @(posedge fclk or negedge rst_n)\n'
           f'        if (!rst_n) begin {zero} end\n'
           f'        else begin {regs} end\n'
           '`ifdef BF_PROG_MUTANT_CORE_BYPASS\n    localparam integer BYP = 1;                       // negative control: programme one edge early\n'
           '`else\n    localparam integer BYP = 0;\n`endif\n' + sel)
    replace(anchor, blk + anchor)
    i = fc.index(anchor) + len(anchor)
    fc = fc[:i - len(anchor)] + re.sub(r'prog_(issue|addr|operand|segment|half|chain)_pin', r'prog_\1_u', fc[i - len(anchor):])
    return fc
