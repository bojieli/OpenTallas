#!/usr/bin/env python3
"""Add only the default-off typed completion successor to the selected native top.

Required whole-plan coverage and visibility authority pins remain external;
this installer neither selects the stage graph nor manufactures those pins.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOIN = 'rtl/rom/wavefront/completion/ot_dsrom_wf_typed_completion_join.sv'


def one(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'selected native boundary missing/ambiguous: {old!r}')
    return text.replace(old, new, 1)


def rewrite(source):
    s = one(source, '    parameter integer NATIVE_RESULT_READ=0,',
            '    parameter integer WFC_TYPED_COMPLETION_JOIN=0,\n    parameter integer NATIVE_RESULT_READ=0,')
    ports = '''    // REQUIRED Arch-owned complete-plan and real visibility authority pins.
    // Unbound valid pins fail closed; never tie coverage/visibility to one.
    input wire wf_join_request_v, wf_join_request_binding_valid, wf_join_request_kind,
    // Actual typed handoff consumer ACK; token controller acceptance stays separate.
    input wire wf_join_handoff_accepted,
    output wire wf_join_request_ready,
    input wire [46:0] wf_join_request_identity,
    input wire [13:0] wf_join_terminal_entry, wf_join_producer_pc, wf_join_end_pc,
    input wire wf_join_coverage_valid, wf_join_wholeplan_complete,
    input wire [46:0] wf_join_coverage_identity,
    input wire wf_join_visibility_valid, wf_join_visibility_fault,
    input wire [46:0] wf_join_visibility_identity,
    input wire [4:0] wf_join_visibility,
    output wire wf_join_pending, wf_join_fault,
    // Actual descriptor/engine edges for the finite source-plan coverage owner.
    // FIELD retirement alone never asserts wholeplan coverage.
    output wire wf_join_descriptor_take, wf_join_native_launch,
    output wire [46:0] wf_join_descriptor_identity, wf_join_launch_identity,
    output wire [13:0] wf_join_descriptor_entry, wf_join_launch_entry,
    output wire wf_join_native_engine_start, wf_join_native_retire,
    output wire [46:0] wf_join_retire_identity,
    output wire [13:0] wf_join_retire_entry,
    output wire wf_join_done, wf_join_terminal_kind, wf_join_token_result_valid, wf_join_stage_handoff_done,
    output wire [20:0] wf_join_next_token,
    output wire [31:0] wf_join_next_value,
'''
    s = one(s, '    input wire wf_stage_done,', ports + '    input wire wf_stage_done,')
    for pin, result in [('wf_stage_done','joined_stage_done'),
                        ('wf_stage_next_token','joined_stage_token'),
                        ('wf_stage_next_val','joined_stage_value')]:
        s = one(s, f'.{pin}({pin})', f'.{pin}(WFC_TYPED_COMPLETION_JOIN ? {"joined_controller_done" if pin == "wf_stage_done" else result} : {pin})')
    # Reuse the exact existing selected native producer/END readouts. This is
    # an opt-in extension of observation selection, not a new numerical source.
    for name in ('active','done','producer_take','am_any','end_take'):
        old = f'assign native_result_{name} = NATIVE_RESULT_READ &&'
        s = one(s, old, f'assign native_result_{name} = (NATIVE_RESULT_READ || WFC_TYPED_COMPLETION_JOIN) &&')
    s = one(s, 'assign native_result_selected = NATIVE_RESULT_READ != 0;',
            'assign native_result_selected = (NATIVE_RESULT_READ || WFC_TYPED_COMPLETION_JOIN) != 0;')
    body = '''
    wire joined_stage_done;
    wire [20:0] joined_stage_token;
    wire [31:0] joined_stage_value;
    assign wf_join_descriptor_take = WFC_TYPED_COMPLETION_JOIN && start && c8_offer_ready;
    assign wf_join_descriptor_identity = {c8_position_identity[46:31],user,pos};
    assign wf_join_descriptor_entry = c8_entry;
    assign wf_join_native_launch = WFC_TYPED_COMPLETION_JOIN && c8_context_v && c8_context_restored;
    assign wf_join_launch_identity = c8_context_identity;
    assign wf_join_launch_entry = c8_context_entry;
    assign wf_join_native_engine_start = WFC_TYPED_COMPLETION_JOIN && c8_engine_start;
    assign wf_join_native_retire = WFC_TYPED_COMPLETION_JOIN && c8_retire_v;
    assign wf_join_retire_identity = c8_retire_identity;
    // C8 cannot launch another engine on the retirement edge. The old engine
    // entry remains stable while registered retire_v is sampled before edge.
    assign wf_join_retire_entry = c8_engine_entry;
    wire joined_terminal_kind, joined_token_result_valid, joined_stage_handoff_done;
    // An intermediate controller forwards HIDDEN/carry records, not a new
    // token result. Raw core-carried payload remains byte-for-byte unchanged.
    // A SOURCE/reducing/RESULT-producing controller must use TOKEN_RESULT.
    localparam integer HANDOFF_CONTROLLER = !SOURCE && !SEND_RESULT && !COMBINE_IN;
    wire joined_controller_done = joined_stage_done &&
                                  (!joined_terminal_kind || HANDOFF_CONTROLLER);
    assign wf_join_done = joined_stage_done;
    assign wf_join_terminal_kind = joined_terminal_kind;
    assign wf_join_token_result_valid = joined_token_result_valid;
    assign wf_join_stage_handoff_done = joined_stage_handoff_done;
    assign wf_join_next_token = joined_stage_token;
    assign wf_join_next_value = joined_stage_value;
    initial if (WFC_TYPED_COMPLETION_JOIN && (!PKG_WAVE || !C8_CONTEXT || !S81_CAPTURE))
        $fatal(1,"finite completion join requires selected WAVE/C8/native capture");
    ot_dsrom_wf_typed_completion_join #(.ENABLE(WFC_TYPED_COMPLETION_JOIN)) u_wf_stage_completion (
        .clk(clk), .rst_n(rst_n),
        .request_v(wf_join_request_v), .request_binding_valid(wf_join_request_binding_valid),
        .request_kind(wf_join_request_kind),
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
        .stage_accepted(joined_terminal_kind ?
            (wf_join_handoff_accepted || (HANDOFF_CONTROLLER && wf_stage_accepted)) : wf_stage_accepted),
        .terminal_kind(joined_terminal_kind), .token_result_valid(joined_token_result_valid),
        .stage_handoff_done(joined_stage_handoff_done), .stage_done(joined_stage_done),
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
                  default_WFC_TYPED_COMPLETION_JOIN=0, source_clock='selected clk unchanged',
                  native_END_result_C8_capture_collective_hooks_bound=True,
                  wholeplan_coverage_authority_bound=False, real_visibility_authorities_bound=False,
                  numerical_sources_changed=False, physical_context_qualified=False,
                  required_Arch_hooks=['saved accepted whole-request identity/terminal entry/producer PC/END PC with binding_valid',
                                       'complete wholeplan coverage valid/identity/complete; not fragment END',
                                       'real continuation/KV/index/remote/allcopy valid/identity/visibility[4:0]/fault',
                                       'request retention until request_ready; typed handoff consumer uses wf_join_stage_handoff_done and actual wf_join_handoff_accepted, ignores native raw payload; token controller uses token_result_valid and wf_stage_accepted'])
    (output / 'source_binding.json').write_text(json.dumps(record, indent=2)+'\n')
    return record


def bind_compiled_field_keys(dispatch_path, stage=37):
    """Consume actual compiler keys without turning field coverage into a plan.

    Runtime context and provider/nonfield/HEAD keys are deliberately not filled
    in here. These records bind the exported native edges to immutable fields;
    they do not drive coverage_valid, request_binding_valid, or visibility.
    """
    path = Path(dispatch_path)
    raw = path.read_bytes()
    dispatch = json.loads(raw)
    groups = dispatch['ownerorderedgroups_by_stage'][str(stage)]
    offers = dispatch['offers']
    expected = dispatch['node_order_by_stage'][str(stage)]
    if len(groups) != len(expected) or dispatch['required_ranks'] != [0, 1, 2, 3]:
        raise ValueError('actual TP4 source group/rank order required')
    bound = []
    seen = set()
    for ordinal, indices in enumerate(groups):
        if len(indices) != 4:
            raise ValueError('incomplete actual TP4 group')
        rank_keys = []
        for rank, index in enumerate(indices):
            offer = offers[index]
            if (index in seen or offer['stage'] != stage or offer['rank'] != rank or
                    offer['die_id'] != stage * 4 + rank or offer['node'] != expected[ordinal][rank]):
                raise ValueError('foreign/repeated/reordered compiled source key')
            seen.add(index)
            entry, producer, end = (offer[k] for k in ('entry', 'producer_pc', 'end_pc'))
            if not (0 <= entry <= producer < end < 1 << 14):
                raise ValueError('compiled entry/producer/END outside native program')
            rank_keys.append({k: offer[k] for k in
                              ('node', 'source_ordinal', 'stage', 'rank', 'die_id',
                               'entry', 'producer_pc', 'end_pc', 'fragment_ordinal', 'key')})
        bound.append(dict(group_ordinal=ordinal, ranks=rank_keys))
    return dict(source_dispatch_sha256=hashlib.sha256(raw).hexdigest(),
                compiler_commit=dispatch.get('implementation_commit'), stage=stage,
                scope='compiled FIELD fragments only; not wholeplan/token completion',
                native_edge_keys=bound, field_groups_per_rank=len(bound),
                program_sha256={k: v for k, v in dispatch['artifacts'].items()
                                if k.startswith(f's{stage}_r') and k.endswith('/prog.hex')},
                runtime_identity=None, terminal=dispatch.get('terminal'),
                wholeplan_coverage_bound=False, visibility_bound=False,
                request_binding_valid_driven=False,
                stage_handoff=dict(end_node=dispatch['source_order'][-2]['node'],
                                   final_fence=dispatch['source_order'][-1]['node'],
                                   scope='intermediate layer/stage handoff; not token result',
                                   native_end_keys_bound=False, final_fence_producer_bound=False,
                                   requires_HEAD_global_argmax=False),
                missing_terminal=dispatch.get('missing_terminal'),
                missing_provider_operations=[dict(node=n['node'], required_provider=n.get('required_provider'),
                                                 missing=n.get('missing', []))
                                             for n in dispatch['source_order']
                                             if n.get('missing')],
                required_next_owner_bindings=['Arch accepted runtime context and real visibility/coverage ports',
                                             'Arendt complete provider/nonfield entries and stage handoff END/fence keys',
                                             'HEAD/globalargmax only for token nativeReadResult'])


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--selected',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--dispatch',type=Path)
    ap.add_argument('--stage',type=int,default=37)
    a=ap.parse_args()
    record = install(a.selected,a.out)
    if a.dispatch:
        keys = bind_compiled_field_keys(a.dispatch, a.stage)
        (a.out / 'compiled_field_keys.json').write_text(json.dumps(keys, indent=2)+'\n')
    print(json.dumps(record,indent=2))
