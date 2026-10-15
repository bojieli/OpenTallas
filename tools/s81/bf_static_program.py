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
    return fc
