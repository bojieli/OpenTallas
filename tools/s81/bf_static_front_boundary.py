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
    text = text.replace(anchor, '    input wire io_clk, // independent physical pin/seam clock root\n    input wire [37:0] f_prog, // fixed core-edge programme, pin->issue +1 edge\n' + anchor, 1)
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
    text = text[:pin_start] + pins + text[pin_end:]
    text = text.replace('(.clk(clk), .rst_n(rst_n),\n            .d({c_issue',
                        '(.clk(pin_clk), .rst_n(rst_n),\n            .d({c_issue')
    start = text.index('        ot_v41_bf_front_core #(')
    end = text.index('));', start) + 3
    inst = text[start:end]
    anchor = '.INSTANCE(INSTANCE)) u_front ('
    assert anchor in inst
    inst = inst.replace(anchor, '.INSTANCE(INSTANCE), .STATIC_PROGRAM(STATIC_PROGRAM)) u_front (', 1)
    inst = inst.replace('            .clk(eclk),', '''            .prog_issue_pin(programme_pin_q[0]), .prog_addr_pin(programme_pin_q[14:1]),
            .prog_operand_pin(programme_pin_q[29:15]), .prog_segment_pin(programme_pin_q[32:30]),
            .prog_half_pin(programme_pin_q[33]), .prog_chain_pin(programme_pin_q[37:34]),
            .clk(eclk),''', 1)
    return text[:start] + inst + text[end:]
