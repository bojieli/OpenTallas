"""Add a registered compiler-programme boundary to the generated BF front.

The legacy mode stays historical. Static mode's programme is captured once at
its own free-clock pin flops, then sampled directly by the core next edge;
operand/go/config staging stays the actual front staging, priced separately.
"""
def apply(text):
    param = '    parameter integer CPIN = 0,'
    assert text.count(param) == 1
    text = text.replace(param, param + '\n    parameter integer STATIC_PROGRAM = 0,', 1)
    anchor = '    output wire         busy,\n'
    assert anchor in text
    text = text.replace(anchor, '    input wire io_clk, // independent physical pin/seam clock root\n    input wire [37:0] f_prog, // fixed core-edge programme, pin->issue +2 edges (pin flop, core flop)\n' + anchor, 1)
    end = text.index('\n);\n', text.index('module ot_s81_bf_front #(')) + 4
    text = text[:end] + '''
    // Keep all programme fields together at the physical face. The core samples
    // the previous registered word; no ready/busy/clock-enable participates.
    wire pin_clk = (STATIC_PROGRAM != 0) ? io_clk : clk;
    (* keep = 1 *) reg [37:0] programme_pin_q;
    generate if (STATIC_PROGRAM != 0) begin : g_static_programme_pin
        always @(posedge pin_clk or negedge rst_n)
            if (!rst_n) programme_pin_q <= 38'd0;
            else programme_pin_q <= f_prog;
    end endgenerate
    // Clock structure (2026-10-15, gate ec84ce526 hold repair 119k buffers): io_clk (pin/seam root, ~200-250 ps) and
    // ck (core root, gated subtrees ~260-310 ps) are two physical roots of ONE die clock (the die ties both to the
    // column clock). Every io_clk -> ck crossing is register -> lockup latch (transparent while io_clk is low) ->
    // register with no fan-out in between, so its hold margin is ~T/2 by construction instead of buffers on every
    // core endpoint. The programme used to fan from programme_pin_q straight into the issue cone (thousands of core
    // endpoints); it now lands in the core's own programme register (u_front prog_*_q on the core clock fclk)
    // first: +1 edge, absorbed by the producer (ot_s81_bf_prog_seq DELTA -1: issue edges vs go unchanged).
    // Core -> io_clk crossings (the CPIN seams) pass one shared lockup-latch bank transparent while clk is low.
    reg [37:0] programme_lat;
    generate if (STATIC_PROGRAM != 0) begin : g_static_programme_core
        always_latch if (!pin_clk) programme_lat = programme_pin_q;
    end endgenerate
''' + text[end:]
    pin_start = text.index('    if (PINREG != 0) begin : g_pin')
    pin_end = text.index('    end else begin : g_nopin', pin_start)
    pins = text[pin_start:pin_end]
    # HALF0 is the actual full-rate production front. Static programme does
    # not share a clock root with its arithmetic; fixed parameter selection
    # eliminates clock muxes at elaboration.
    pins = pins.replace('posedge clk', 'posedge pin_clk')
    pins = pins.replace('posedge pclk', 'posedge pin_clk')
    pins = pins.replace('if (!pclk)', 'if (!pin_clk)')
    pins = pins.replace('always_latch if (!clk)', 'always_latch if (!pin_clk)')
    # control pins cross io_clk -> ck through the same lockup latches as the payload (static programme only; the
    # legacy single-root front keeps its direct path)
    ctl = [('cfg_v', 1), ('cfg_a', 5), ('cfg_d', 48), ('go', 1), ('go_bf', 1), ('xs_v', 1), ('xb_v', 1)]
    anchor = '        assign cfg_v_i = r_cfg_v;\n'
    assert pins.count(anchor) == 1
    decl = ''.join(f'        reg {"[%d:0] " % (w - 1) if w > 1 else ""}r_lc_{n};\n' for n, w in ctl)
    body = ' '.join(f'r_lc_{n} = r_{n};' for n, w in ctl)
    blk = (decl + '        if (STATIC_PROGRAM != 0 && PINLAT != 0) begin : g_lat_ctl\n'
           '            always_latch if (!pin_clk) begin\n'
           '`ifdef BF_CTL_LAT_MUTANT_GO\n'
           '                ' + body.replace('r_lc_go = r_go;', "r_lc_go = 1'b0;") + '   // negative control: go lost\n'
           '`else\n'
           '                ' + body + '\n'
           '`endif\n'
           '            end\n'
           '        end else begin : g_nolat_ctl\n'
           '            always @* begin ' + body + ' end\n'
           '        end\n')
    pins = pins.replace(anchor, blk + anchor)
    for n, w in ctl:
        a = f'        assign {n}_i = r_{n};\n'
        assert pins.count(a) == 1, a
        pins = pins.replace(a, f'        assign {n}_i = r_lc_{n};\n')
    text = text[:pin_start] + pins + text[pin_end:]
    text = text.replace('(.clk(clk), .rst_n(rst_n),\n            .d({c_issue',
                        '(.clk(pin_clk), .rst_n(rst_n),\n            .d({c_issue')
    # core -> seam: one shared lockup-latch bank on the core root (transparent while clk is low) feeds both faces'
    # seam registers (static only).
    seam_anchor = '        localparam integer CW = 1+14+3+CTW+2*256+2*10+1+2*5*NSEG+16*NSEG;\n'
    assert text.count(seam_anchor) == 1
    lat = (seam_anchor +
           '        localparam integer CLW = 1+14+3+CTW+2*256+2*10+1+2*5*NSEG+16*NB*NSEG;\n'
           '        wire [CLW-1:0] c_raw = {c_issue, c_a_ctr, c_i1_v, c_i1_bk, c_i1_bf, c_i1_t, c_i2x_q0, c_i2x_e0, c_i2x_q1, c_i2x_e1, c_ze_d, c_so_idx, c_so_n, c_so_row};\n'
           '        reg [CLW-1:0] c_lk;\n'
           '        if (STATIC_PROGRAM != 0) begin : g_seam_lk\n'
           '`ifdef BF_SEAM_LK_MUTANT\n'
           "            always_latch if (!clk) c_lk = c_raw ^ {1'b1, {(CLW-1){1'b0}}};   // negative control: latched issue bit flipped\n"
           '`else\n'
           '            always_latch if (!clk) c_lk = c_raw;\n'
           '`endif\n'
           '        end else begin : g_seam_nolk\n'
           '            always @* c_lk = c_raw;\n'
           '        end\n'
           '        wire c_issue_l, c_i1_v_l, c_i1_bk_l, c_i1_bf_l, c_ze_d_l; wire [13:0] c_a_ctr_l; wire [CTW-1:0] c_i1_t_l;\n'
           '        wire [255:0] c_i2x_q0_l, c_i2x_q1_l; wire [9:0] c_i2x_e0_l, c_i2x_e1_l; wire [5*NSEG-1:0] c_so_idx_l, c_so_n_l;\n'
           '        wire [16*NB*NSEG-1:0] c_so_row_l;\n'
           '        assign {c_issue_l, c_a_ctr_l, c_i1_v_l, c_i1_bk_l, c_i1_bf_l, c_i1_t_l, c_i2x_q0_l, c_i2x_e0_l, c_i2x_q1_l, c_i2x_e1_l, c_ze_d_l, c_so_idx_l, c_so_n_l, c_so_row_l} = c_lk;\n')
    text = text.replace(seam_anchor, lat, 1)
    a = text.index(lat) + len(lat); b = text.index('assign c_qy_bkf = c_qy_bkf_in;', a)
    seg = text[a:b]
    for s in ('c_issue', 'c_a_ctr', 'c_i1_v', 'c_i1_bk', 'c_i1_bf', 'c_i1_t', 'c_i2x_q0', 'c_i2x_e0', 'c_i2x_q1', 'c_i2x_e1', 'c_ze_d', 'c_so_idx', 'c_so_n'):
        seg = seg.replace('{' + s + ', ', '{' + s + '_l, ').replace(', ' + s + ', ', ', ' + s + '_l, ')
    seg = seg.replace('c_so_row[16*NSEG*', 'c_so_row_l[16*NSEG*')
    text = text[:a] + seg + text[b:]
    start = text.index('        ot_v41_bf_front_core #(')
    end = text.index('));', start) + 3
    inst = text[start:end]
    anchor = '.INSTANCE(INSTANCE)) u_front ('
    assert anchor in inst
    inst = inst.replace(anchor, '.INSTANCE(INSTANCE), .STATIC_PROGRAM(STATIC_PROGRAM)) u_front (', 1)
    inst = inst.replace('            .clk(eclk),', '''            .prog_issue_pin(programme_lat[0]), .prog_addr_pin(programme_lat[14:1]),
            .prog_operand_pin(programme_lat[29:15]), .prog_segment_pin(programme_lat[32:30]),
            .prog_half_pin(programme_lat[33]), .prog_chain_pin(programme_lat[37:34]),
            .clk(eclk),''', 1)
    text = text[:start] + inst + text[end:]
    assert text.count("        always @(posedge pin_clk or negedge rst_n)\n            if (!rst_n) begin r_busy <= 1'b0; r_fault <= 1'b0; end\n            else begin r_busy <= busy_e; r_fault <= fault_e; end\n") == 1
    return text.replace("        always @(posedge pin_clk or negedge rst_n)\n            if (!rst_n) begin r_busy <= 1'b0; r_fault <= 1'b0; end\n            else begin r_busy <= busy_e; r_fault <= fault_e; end\n", "        // Core -> boundary status uses the same physical lockup protection as\n        // the payload seams. The source-low latch preserves sampled edges.\n        wire busy_pin_d, fault_pin_d;\n        if (STATIC_PROGRAM != 0) begin : g_static_status_lockup\n            reg busy_l, fault_l;\n            always_latch if (!clk) begin busy_l <= busy_e; fault_l <= fault_e; end\n            assign busy_pin_d = busy_l;\n            assign fault_pin_d = fault_l;\n        end else begin : g_status_direct\n            assign busy_pin_d = busy_e;\n            assign fault_pin_d = fault_e;\n        end\n        always @(posedge pin_clk or negedge rst_n)\n            if (!rst_n) begin r_busy <= 1'b0; r_fault <= 1'b0; end\n            else begin r_busy <= busy_pin_d; r_fault <= fault_pin_d; end\n")
