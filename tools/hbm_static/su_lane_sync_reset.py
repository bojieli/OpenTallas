"""Reset-only transforms for the generated static SU lane and insertion line.

The native arithmetic remains unchanged. OT_SU_SYNC_RST inserts per-clock
reset relays and synchronous consumers; the default preserves legacy behavior.
"""
import re

RESET_HEADER = '''// OT_SU_SYNC_RST: local reset relays drive synchronous arithmetic consumers.
`ifndef OT_SU_ARST
`ifdef OT_SU_SYNC_RST
`define OT_SU_ARST(r)
`else
`define OT_SU_ARST(r) or negedge r
`endif
`endif
'''


def reset_macro(text):
    text = text.replace('or negedge rst_n', '`OT_SU_ARST(rst_n)')
    return text if '`define OT_SU_ARST' in text else RESET_HEADER + text


def lane_regions(text):
    text = reset_macro(text)
    marker = '    /* verilator hier_block */'
    pos = text.index(marker) if marker in text else text.index('    localparam')
    text = text[:pos] + '''    wire [7:0] rst_stage_n;
    wire [3:0] rst_insert_n;
`ifdef OT_SU_SYNC_RST
    for (genvar r = 0; r < 8; r = r + 1) begin : g_rst_stage
        ot_sync_rst_relay u_reset (.clk_sync(clk_stage[0]), .clk(clk_stage[r]), .rst_n_in(rst_n), .rst_n(rst_stage_n[r]));
    end
    for (genvar r = 0; r < 4; r = r + 1) begin : g_rst_insert
        ot_sync_rst_relay u_reset (.clk_sync(clk_stage[0]), .clk(clk_insert[r]), .rst_n_in(rst_n), .rst_n(rst_insert_n[r]));
    end
`else
    assign rst_stage_n = {8{rst_n}};
    assign rst_insert_n = {4{rst_n}};
`endif
''' + text[pos:]
    text = text.replace('`OT_SU_ARST(rst_n)', '`OT_SU_ARST(rst_stage_n[0])')
    pattern = r'(always @\(posedge clk_stage\[(0|7)\][^\n]*\)(?: begin)?\n?)(.*?)(?=\n    (?:always|wire|reg|assign|generate|ot_|endgenerate)|\Z)'
    text = re.sub(pattern, lambda m: m[1].replace('rst_stage_n[0]', f'rst_stage_n[{m[2]}]') +
                  m[3].replace('!rst_n', f'!rst_stage_n[{m[2]}]'), text, flags=re.S)
    text = re.sub(r'(\.clk\(clk_stage\[(\d)\]\), \.rst_n\()rst_n(\))',
                  lambda m: m[1] + f'rst_stage_n[{m[2]}]' + m[3], text)
    text = re.sub(r'(\(clk_stage\[(\d)\], )rst_n(,)',
                  lambda m: m[1] + f'rst_stage_n[{m[2]}]' + m[3], text)
    text = text.replace('.clk(clk_insert), .rst_n(rst_n)', '''.clk(clk_insert), .rst_n(rst_n),
`ifdef OT_SU_SYNC_RST
                    .rst_regions_n(rst_insert_n),
`endif
                   ''')
    return text.replace('                   , .v(', '                    .v(')


def insertion_regions(text):
    text = reset_macro(text)
    text = text.replace('    input  wire         rst_n,', '''    input  wire         rst_n,
`ifdef OT_SU_SYNC_RST
    input wire [3:0] rst_regions_n,
`endif''')
    text = text.replace('                wire [W-1:0] nx', '''`ifdef OT_SU_SYNC_RST
                wire local_rst_n = rst_regions_n[(p-1)/48];
`else
                wire local_rst_n = rst_n;
`endif
                wire [W-1:0] nx''')
    return text.replace('`OT_SU_ARST(rst_n)', '`OT_SU_ARST(local_rst_n)').replace('if (!rst_n)', 'if (!local_rst_n)')
