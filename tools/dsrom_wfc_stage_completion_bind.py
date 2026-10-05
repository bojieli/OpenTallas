#!/usr/bin/env python3
"""Add only the default-off finite completion join to the selected native top.

Required whole-plan coverage and visibility authority pins remain external;
this installer neither selects the stage graph nor manufactures those pins.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOIN = 'rtl/rom/wavefront/completion/ot_dsrom_wf_stage_completion_join.sv'


def one(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'selected native boundary missing/ambiguous: {old!r}')
    return text.replace(old, new, 1)


def rewrite(source):
    s = one(source, '    parameter integer NATIVE_RESULT_READ=0,',
            '    parameter integer WFC_COMPLETION_JOIN=0,\n    parameter integer NATIVE_RESULT_READ=0,')
    ports = '''    // REQUIRED Arch-owned complete-plan and real visibility authority pins.
    // Unbound valid pins fail closed; never tie coverage/visibility to one.
    input wire wf_join_request_v, wf_join_request_binding_valid,
    output wire wf_join_request_ready,
    input wire [46:0] wf_join_request_identity,
    input wire [13:0] wf_join_terminal_entry, wf_join_producer_pc, wf_join_end_pc,
    input wire wf_join_coverage_valid, wf_join_wholeplan_complete,
    input wire [46:0] wf_join_coverage_identity,
    input wire wf_join_visibility_valid, wf_join_visibility_fault,
    input wire [46:0] wf_join_visibility_identity,
    input wire [4:0] wf_join_visibility,
    output wire wf_join_pending, wf_join_fault,
'''
    s = one(s, '    input wire wf_stage_done,', ports + '    input wire wf_stage_done,')
    for pin, result in [('wf_stage_done','joined_stage_done'),
                        ('wf_stage_next_token','joined_stage_token'),
                        ('wf_stage_next_val','joined_stage_value')]:
        s = one(s, f'.{pin}({pin})', f'.{pin}(WFC_COMPLETION_JOIN ? {result} : {pin})')
    # Reuse the exact existing selected native producer/END readouts. This is
    # an opt-in extension of observation selection, not a new numerical source.
    for name in ('active','done','producer_take','am_any','end_take'):
        old = f'assign native_result_{name} = NATIVE_RESULT_READ &&'
        s = one(s, old, f'assign native_result_{name} = (NATIVE_RESULT_READ || WFC_COMPLETION_JOIN) &&')
    s = one(s, 'assign native_result_selected = NATIVE_RESULT_READ != 0;',
            'assign native_result_selected = (NATIVE_RESULT_READ || WFC_COMPLETION_JOIN) != 0;')
    body = '''
    wire joined_stage_done;
    wire [20:0] joined_stage_token;
    wire [31:0] joined_stage_value;
    initial if (WFC_COMPLETION_JOIN && (!PKG_WAVE || !C8_CONTEXT || !S81_CAPTURE))
        $fatal(1,"finite completion join requires selected WAVE/C8/native capture");
    ot_dsrom_wf_stage_completion_join #(.ENABLE(WFC_COMPLETION_JOIN)) u_wf_stage_completion (
        .clk(clk), .rst_n(rst_n),
        .request_v(wf_join_request_v), .request_binding_valid(wf_join_request_binding_valid),
        .request_ready(wf_join_request_ready), .request_identity(wf_join_request_identity),
        .request_terminal_entry(wf_join_terminal_entry), .request_producer_pc(wf_join_producer_pc),
        .request_end_pc(wf_join_end_pc),
        .native_active(native_result_active), .native_producer_take(native_result_producer_take),
        .native_end_take(native_result_end_take), .native_done(native_result_done),
        .native_am_any(native_result_am_any), .native_identity(native_result_identity),
        .native_entry(native_result_entry), .native_pc(native_result_pc),
        .native_next_token(native_result_token), .native_next_value(native_result_value),
        .coverage_valid(wf_join_coverage_valid), .coverage_wholeplan_complete(wf_join_wholeplan_complete),
        .coverage_identity(wf_join_coverage_identity), .visibility_valid(wf_join_visibility_valid),
        .visibility_fault(wf_join_visibility_fault), .visibility_identity(wf_join_visibility_identity),
        .visibility(wf_join_visibility), .c8_write_quiet(c8_write_quiet),
        .c8_quarantine(c8_write_quarantine || c8_stage_quarantine), .c8_fault(c8_write_fault),
        .capture_live(capture_live), .capture_drained(capture_drained), .capture_fault(capture_fault),
        .collective_busy(dut.coll_busy), .collective_fault(dut.die_coll_fault), .native_fault(fault),
        .stage_accepted(wf_stage_accepted), .stage_done(joined_stage_done),
        .stage_next_token(joined_stage_token), .stage_next_value(joined_stage_value),
        .pending(wf_join_pending), .fault(wf_join_fault));
'''
    return one(s, '\nendmodule', body + '\nendmodule')


def install(selected, output):
    selected, output = Path(selected), Path(output)
    if output.exists():
        raise FileExistsError(output)
    source = selected.read_text()
    rewritten = rewrite(source)
    output.mkdir(parents=True)
    generated = output / selected.name
    generated.write_text(rewritten)
    record = dict(selected=str(selected), generated=str(generated), join_source=JOIN,
                  input_sha256=hashlib.sha256(source.encode()).hexdigest(),
                  output_sha256=hashlib.sha256(rewritten.encode()).hexdigest(),
                  default_WFC_COMPLETION_JOIN=0, source_clock='selected clk unchanged',
                  native_END_result_C8_capture_collective_hooks_bound=True,
                  wholeplan_coverage_authority_bound=False, real_visibility_authorities_bound=False,
                  numerical_sources_changed=False, physical_context_qualified=False,
                  required_Arch_hooks=['saved accepted whole-request identity/terminal entry/producer PC/END PC with binding_valid',
                                       'complete wholeplan coverage valid/identity/complete; not fragment END',
                                       'real continuation/KV/index/remote/allcopy valid/identity/visibility[4:0]/fault',
                                       'request retention until request_ready; original stage_accepted retires old result before simultaneous new request'])
    (output / 'source_binding.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--selected',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(install(a.selected,a.out),indent=2))
