#!/usr/bin/env python3
"""Generate the isolated default-off successor from its immutable source pin."""
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
PIN = ROOT / 'results/uarch/dsrom_c_w5_sequencer_20261003/source.json'


def generate():
    pin = json.loads(PIN.read_text())
    original = subprocess.check_output(['git', 'show', pin['commit'] + ':' + pin['path']], cwd=ROOT).decode()
    assert hashlib.sha256(original.encode()).hexdigest() == pin['sha256']
    replacements = [
        ('module ot_hdc_core_v41x #(\n', 'module ot_dsrom_c_w5_core_v41x #(\n    parameter bit W5_ENABLE_PG = 1\'b0,\n    parameter integer W5_GUARD_CYCLES = 2,\n'),
        ('    input  wire              rst_n,\n', '''    input  wire              rst_n,
    // W5 field/link supply intents; this sequencer and Engram remain AON.
    input wire w5_sleep_req, w5_neighbor_prewake,
    input wire [7:0] w5_retained_live_debt, w5_debt_known,
    input wire w5_isolation_ack, w5_power_good, w5_relock_ack, w5_inrush_grant,
    output wire w5_start_ready, w5_power_req, w5_isolation_req,
    output wire w5_clock_enable, w5_wake_request, w5_fault,
    output wire [31:0] w5_added_cycles,
    output wire [32:0] w5_total_cycles,
'''),
        ('    reg [3:0]  st;\n', '''    reg [3:0]  st;
    wire w5_core_start;
    wire [2*NW+PAW-1:0] w5_core_payload;
    wire [NW-1:0] w5_token, w5_pos;
    wire [PAW-1:0] w5_entry;
    assign {w5_token,w5_pos,w5_entry}=w5_core_payload;
    assign w5_total_cycles={1'b0,cycles}+{1'b0,w5_added_cycles};
    ot_dsrom_c_w5_seq_gate #(.ENABLE_PG(W5_ENABLE_PG),
        .PAYLOAD_W(2*NW+PAW), .GUARD_CYCLES(W5_GUARD_CYCLES)) w5_admission (
        .clk_aon(clk), .rst_n(rst_n), .start(start),
        .sequencer_idle(st == S_IDLE),
        .engines_idle((&idles) && win_idle && !coll_busy),
        .payload({token,pos,entry}), .sleep_req(w5_sleep_req),
        .neighbor_prewake(w5_neighbor_prewake),
        .retained_live_debt(w5_retained_live_debt), .debt_known(w5_debt_known),
        .isolation_ack(w5_isolation_ack), .power_good(w5_power_good),
        .relock_ack(w5_relock_ack), .inrush_grant(w5_inrush_grant),
        .start_ready(w5_start_ready), .core_start(w5_core_start),
        .core_payload(w5_core_payload), .power_req(w5_power_req),
        .isolation_req(w5_isolation_req), .clock_enable(w5_clock_enable),
        .wake_request(w5_wake_request), .fault(w5_fault),
        .added_cycles(w5_added_cycles));
'''),
        ('.start_v(start && st == S_IDLE), .start_tok(token)', '.start_v(w5_core_start && st == S_IDLE), .start_tok(w5_token)'),
        ('S_IDLE: if (start) begin', 'S_IDLE: if (w5_core_start) begin'),
        ('tok_r <= token; pos_r <= pos; pc <= entry;', 'tok_r <= w5_token; pos_r <= w5_pos; pc <= w5_entry;'),
        ('else if (start && st == S_IDLE) fault', 'else if (w5_core_start && st == S_IDLE) fault'),
        ('if (FULL_SHAPE && (coll_fault || rope_pf_fault)) st <= S_COLL_HALT;',
         'if (w5_fault || (FULL_SHAPE && (coll_fault || rope_pf_fault))) st <= S_COLL_HALT;'),
    ]
    source = original
    replacements.append(('    `include "ot_hdc_isa_v41_profiles.svh"',
        '''    // W5 controls ROM fields only. HA weight-service integration belongs
    // to its separate owner; it cannot enable this ROM candidate.
    initial if (W5_ENABLE_PG && W_HBM) $fatal(1, "W5 is ROM-only");
    `include "ot_hdc_isa_v41_profiles.svh"'''))
    for before, after in replacements:
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    # The inverse proves the successor has no unrelated engine/numeric edits.
    inverse = source
    for before, after in reversed(replacements):
        inverse = inverse.replace(after, before)
    assert inverse == original
    return source


if __name__ == '__main__':
    (ROOT / 'rtl/v41rom/ot_dsrom_c_w5_core_v41x.sv').write_text(generate())
