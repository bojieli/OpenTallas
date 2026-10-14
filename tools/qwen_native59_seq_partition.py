#!/usr/bin/env python3
"""Generate a default-off retained-program partition; legacy source is read-only.

Independent candidate clock pins are tied together only in the functional bench.
Pin timing, placement slots, CTS, and production-program binding remain unproved.
"""
import argparse
import hashlib
import re
from pathlib import Path

SOURCE = Path('rtl/physical/ot_qfd_seq_su_bi_native8_tag59_candidate.sv')
DST = Path('rtl/physical/ot_qfd_native59_retained_partition_candidate.sv')
BENCH = Path('rtl/test/tb_qfd_native59_retained_partition.sv')
PARAMS = dict(W=16, G=3072, AW=24, NW=18, PAW=12, SW=64, LV=7,
              D=8, SMIN=7, SMAX=11, TCUT=7, IS=1, OS=1, RT=4,
              RLY=0, CRED=32, RRG=0, PCUT=0, OLAG=0, PSRAM=0,
              PMUT=0, HQ2=0, RB=3)


def generate():
    src = SOURCE.read_text()
    assert hashlib.sha256(src.encode()).hexdigest() == 'f948f7af33e39946884dfd685f40ef778095601cdef180fc3590e15e47b305ce'
    ports = src[src.index(') (') + 4:src.index(');\n    wire rs;')]
    for k, v in PARAMS.items():
        ports = re.sub(r'\b' + k + r'\b', str(v), ports)
    names = re.findall(r'\b(?:input|output)\s+wire\s+(?:\[[^\]]+\]\s*)?(\w+)', ports)
    assert len(names) > 80 and names[0] == 'clk'
    body = src[src.index('    wire rs;'):src.rindex('endmodule')]
    start, end = body.index('    wire prog_re;'), body.index('    wire wrom_re_w;')
    replacement = '''    wire prog_re; wire [11:0] prog_addr, prog_base;
    wire desc_re; wire [5:0] desc_addr; reg [63:0] desc_q;
    reg [63:0] desc_mem [0:7];
    wire [11:0] prog_a = prog_base + prog_addr;
    reg prog_re_r; reg [11:0] prog_a_r;
    reg [63:0] pw_row2; reg [15:0] pw_word2; reg [63:0] pw_d2;
    always @(posedge clk or negedge rsv[7]) if (!rsv[7]) prog_re_r <= 1'b0; else prog_re_r <= prog_re;
    always @(posedge clk) prog_a_r <= prog_a;
    always @(posedge clk) begin
        if (q_dw_v) desc_mem[q_dw_addr] <= q_dw_data;
        if (desc_re) desc_q <= (desc_addr < 8) ? desc_mem[desc_addr[2:0]] : 64'd0;
        pw_row2 <= q_pw_v ? (64'd1 << q_pw_addr[9:4]) : 64'd0;
        pw_word2 <= 16'd1 << q_pw_addr[3:0];
        pw_d2 <= q_pw_data;
    end
    assign p_read_valid = prog_re_r;
    assign p_read_addr = prog_a_r;
    assign p_write_rows = pw_row2;
    assign p_write_words = pw_word2;
    assign p_write_data = pw_d2;
'''
    body = body[:start] + replacement + body[end:]
    # Keep the original IS/OS edges, but harden their state under a separate
    # clock pin. This removes3415 station FF bits from the control root.
    station_pattern = re.compile(r'ot_hdc_delay\s+#\([^;]+?\)\s+u_[io]_[^;]+?;', re.S)
    stations = station_pattern.findall(body)
    assert len(stations) > 60
    raw_inputs = set(re.findall(r'\binput\s+wire\s+(?:\[[^\]]+\]\s*)?(\w+)', ports))
    raw_outputs = set(names) - raw_inputs
    widths = {}
    for typ, width, declaration in re.findall(r'\b(input\s+wire|output\s+wire|wire|reg)\s+(\[[^\]]+\]\s*)?([^;\n]+);',
                                             body + '\n' + ports.replace(',\n', ';\n') + ';'):
        for item in declaration.split(','):
            match = re.match(r'\s*(\w+)', item)
            if match:
                widths[match[1]] = width or ''
    # Port lines have trailing comments; parse those separately as authoritative.
    for width, name in re.findall(r'\b(?:input|output)\s+wire\s+(\[[^\]]+\]\s*)?(\w+)', ports):
        widths[name] = width or ''
    for name in widths:
        for key, value in PARAMS.items():
            widths[name] = re.sub(r'\b' + key + r'\b', str(value), widths[name])
    dvars, qvars = set(), set()
    for st in stations:
        for pin, target in [('d', dvars), ('q', qvars)]:
            expression = re.search(r'\.' + pin + r'\(([^()]*)\)', st).group(1)
            target.update(n for n in re.findall(r'\b\w+\b', expression) if n in widths)
    io_to_control = sorted(qvars - raw_outputs)
    control_to_io = sorted(dvars - raw_inputs - set(io_to_control))
    cross = set(io_to_control + control_to_io)
    assert len(cross) > 70
    body = station_pattern.sub('', body)

    def remove_cross_wires(match):
        width, declaration = match.groups()
        remaining = [item for item in declaration.split(',')
                     if re.match(r'\s*(\w+)', item).group(1) not in cross]
        return 'wire ' + (width or '') + ','.join(remaining) + ';' if remaining else ''

    body = re.sub(r'\bwire\s+(\[[^\]]+\]\s*)?([^;]+);', remove_cross_wires, body)
    crossing_ports = [('%s wire %s%s' % ('input' if n in io_to_control else 'output', widths[n], n))
                      for n in sorted(cross)]
    control_ports = '    input wire clk, input wire rst_n,\n    ' + ',\n    '.join(crossing_ports)
    extra = '''    input wire [1023:0] prog_q,
    output wire p_read_valid, output wire [11:0] p_read_addr,
    output wire [63:0] p_write_rows, output wire [15:0] p_write_words,
    output wire [63:0] p_write_data'''
    control = ('(* keep_hierarchy = "yes" *) module ot_qfd_native59_control_state_leaf (\n' +
               control_ports + ',\n' + extra + '\n);\n' +
               '    localparam integer ' + ', '.join('%s=%d' % p for p in PARAMS.items()) + ';\n' +
               body + 'endmodule\n')
    io_ports = ports + ',\n    ' + ',\n    '.join(
        '%s wire %s%s' % ('output' if n in io_to_control else 'input', widths[n], n) for n in sorted(cross))
    io_body = '\n'.join(stations).replace('rsv[3]', 'rs').replace('rsv[4]', 'rs').replace('rsv[5]', 'rs').replace('rsv[6]', 'rs')
    assert 'rsv[' not in io_body
    io = ('(* keep_hierarchy = "yes" *) module ot_qfd_native59_station_leaf (\n' + io_ports + '\n);\n' +
          '    localparam integer ' + ', '.join('%s=%d' % p for p in PARAMS.items()) + ';\n' +
          '    wire rs; ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk),.rst_n(rst_n),.rst_q(rs));\n' +
          io_body + '\nendmodule\n')
    bank = '''(* keep_hierarchy = "yes" *) module ot_qfd_native59_program_lane_leaf (
    input wire clk, input wire read_valid, input wire [11:0] read_addr,
    input wire [63:0] write_rows, input wire write_word, input wire [63:0] write_data,
    output reg [63:0] read_data
);
    reg [63:0] rows [0:63];
    integer row;
    always @(posedge clk) begin
        for (row=0; row<64; row=row+1)
            if (write_rows[row] && write_word) rows[row] <= write_data;
        if (read_valid) read_data <= (read_addr < 64) ? rows[read_addr[5:0]] : 64'd0;
    end
endmodule
'''
    parent_ports = ports.replace('input  wire clk,', 'input wire clk_control, input wire clk_station,\n    input wire [15:0] clk_program,', 1)
    assert parent_ports != ports
    connections = ',\n        '.join('.%s(%s)' % (n, 'clk_station' if n == 'clk' else n) for n in names)
    cross_connections = ',\n        '.join('.%s(%s)' % (n, n) for n in sorted(cross))
    cross_wires = '\n'.join('    wire %s%s;' % (widths[n], n) for n in sorted(cross))
    parent = ('module ot_qfd_native59_retained_partition_candidate (\n' + parent_ports + '\n);\n' +
              cross_wires + '\n' + '''    wire [1023:0] prog_q;
    wire p_read_valid; wire [11:0] p_read_addr;
    wire [63:0] p_write_rows, p_write_data; wire [15:0] p_write_words;
    ot_qfd_native59_control_state_leaf u_control (
        .clk(clk_control), .rst_n(rst_n),
        ''' + cross_connections + ''',
        .prog_q(prog_q), .p_read_valid(p_read_valid), .p_read_addr(p_read_addr),
        .p_write_rows(p_write_rows), .p_write_words(p_write_words), .p_write_data(p_write_data));
    ot_qfd_native59_station_leaf u_station (
        ''' + connections + ',\n        ' + cross_connections + ''');
    genvar lane;
    generate for (lane=0; lane<16; lane=lane+1) begin : g_program
        ot_qfd_native59_program_lane_leaf u_bank (
            .clk(clk_program[lane]), .read_valid(p_read_valid), .read_addr(p_read_addr),
            .write_rows(p_write_rows), .write_word(p_write_words[lane]), .write_data(p_write_data),
            .read_data(prog_q[64*lane+:64]));
    end endgenerate
endmodule
''')
    assert not re.search(r'\b(reg|always|always_ff|always_comb)\b', parent)
    header = ('// Generated by tools/qwen_native8_seq_partition.py from native59 source-bound functional clone.\n'
              '// Retained-state partition ONLY: no assigned slots, pin timing, CTS, or physical qualification.\n'
              '// Program read-address/data mux pin registration and native tag ABI remain explicit gaps.\n'
              '// No CROM5 or VL adoption; functional bench uses a common-phase clock adapter.\n')
    tb = Path('rtl/test/tb_qfd_seq_su_native8_candidate.sv').read_text().replace('ot_qfd_seq_su_bi_native8_candidate','ot_qfd_seq_su_bi_native8_tag59_candidate')
    tb=tb.replace('wire [32-1:0] c_tag_0, c_tag_1;', 'wire [59-1:0] c_tag_0, c_tag_1;')
    tb=tb.replace('.stage_in(6\'d0),', '.coll_epoch(16\'d17), .r_tag(c_tag_0), .cb_st_rdy_tpos(tp_pos), .stage_in(6\'d1),')
    tb=tb.replace('.cb_st_rdy_stage(6\'d0)', '.cb_st_rdy_stage(6\'d1)')
    tb=re.sub(r'(tp_token = [^;]+;)', r'\1 tp_token=tp_token%151936;',tb)
    tb=re.sub(r'(tp_pos = [^;]+;)', r'\1 tp_pos=tp_pos%8192;',tb)
    tb = tb.replace('module tb_qfd_seq_su_native8_candidate;', 'module tb_qfd_native59_retained_partition;')
    tb, count = re.subn(r'ot_qfd_seq_su_bi_native8_tag59_candidate #\([^\n]+\) u1 \(',
                       'ot_qfd_native59_retained_partition_candidate u1 (', tb)
    assert count == 1
    begin = tb.index('ot_qfd_native59_retained_partition_candidate u1 (')
    tail = tb[begin:].replace('.clk(clk)', '.clk_control(clk), .clk_station(clk), .clk_program({16{clk}})', 1)
    tb = tb[:begin] + tail
    for name in ('u_seq', 'q_r_rank', 'u_ctrl'):
        tb = tb.replace('u1.' + name, 'u1.u_control.' + name)
    tb = tb.replace('u1.u_control.q_r_rank', 'u1.u_station.q_r_rank')
    tb = ('// Retained-program partition vs original native8 flop-store reference.\n'
          '// Candidate is fixed-profile; inherited U1_* parameters are not adopted.\n'
          '// Rank input truncation and temporary late-bank-read source mutation are negatives.\n'
          '// Common-phase adapter only; no physical or actual checkpoint-program qualification.\n' + tb)
    return header + control + io + bank + parent, tb


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    rtl, tb = generate()
    if a.check:
        assert DST.read_text() == rtl and BENCH.read_text() == tb
    else:
        DST.write_text(rtl)
        BENCH.write_text(tb)


if __name__ == '__main__':
    main()
