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
    // endpoints); it now lands in programme_core_q (core clock) first: +1 edge, absorbed by the producer
    // (ot_s81_bf_prog_seq DELTA -1: the compiled issue edges relative to go are unchanged).
    reg [37:0] programme_lat;
    (* keep = 1 *) reg [37:0] programme_core_q;
    generate if (STATIC_PROGRAM != 0) begin : g_static_programme_core
        always_latch if (!pin_clk) programme_lat = programme_pin_q;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) programme_core_q <= 38'd0;
`ifdef BF_PROG_MUTANT_CORE_BYPASS
            else programme_core_q <= f_prog;                // negative control: programme one edge early
`else
            else programme_core_q <= programme_lat;
`endif
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
    start = text.index('        ot_v41_bf_front_core #(')
    end = text.index('));', start) + 3
    inst = text[start:end]
    anchor = '.INSTANCE(INSTANCE)) u_front ('
    assert anchor in inst
    inst = inst.replace(anchor, '.INSTANCE(INSTANCE), .STATIC_PROGRAM(STATIC_PROGRAM)) u_front (', 1)
    inst = inst.replace('            .clk(eclk),', '''            .prog_issue_pin(programme_core_q[0]), .prog_addr_pin(programme_core_q[14:1]),
            .prog_operand_pin(programme_core_q[29:15]), .prog_segment_pin(programme_core_q[32:30]),
            .prog_half_pin(programme_core_q[33]), .prog_chain_pin(programme_core_q[37:34]),
            .clk(eclk),''', 1)
    return text[:start] + inst + text[end:]
