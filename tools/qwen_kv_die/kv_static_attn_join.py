#!/usr/bin/env python3
"""KVJ-SMALL (a) 2026-10-17: attention service control + RESULT face joins (static-join gap item 9).

Builds on kv_static_kvjf_join.build() (template + boot + boot CDC + host admission + ownership + die cfg).  Adds the
attention service's calendar root and its result face beside attention_programme (attention control tile =
programme + qkd_attn_cal_gen + qkd_attn_service_root + qkd_attn_result_face):

  attn_root = qkd_attn_service_root (PV_LEAD compiler-priced = die relay edges to pvw_0/1)
    request_valid / request_epoch / request_layer / request_position / request_calendar / q_valid / q_beat
                                          <- attention_programme (same names)
    attention_programme.request_ready     <- attn_root.request_ready (boot count only; the programme treats it as an
                                             assertion, never as a slot mover)
  attn_face = qkd_attn_result_face (RESULT_RELAY compiler-priced: registered edges face -> programme; NF = 10)
    running / start_qk / age / ep / layer / cal / root_local_fault / root_io_fault <- attn_root
    attention_programme.result_valid / result_beat / result_data / result_epoch / result_layer / result_done /
      service_fault                       <- attn_face (same names)
  Remaining opens (die joins, KVJ-G2): attn_face.f_valid / f_data / f_epoch <- the PV final join
  ot_qwen_tp8_pv256_finalize_static_cal out_valid / out_data / out_epoch; attn_face.unit_fault <- the 10 sticky
  service-unit faults (stacks, hub, PV pairs, finalize, V request, e-read identity, rz-late, K identity, legacy pv,
  stack); attn_root.fused_program_capability <- the boot image capability bit (as attention_programme's).
Bench + mutants: tools/qwen_kv_die/attn_result_face_gate.py.  Never a die netlist.
"""
import kv_static as K
import kv_static_boot_join as B
import kv_static_kvjf_join as F

ROOT_M = ('rtl/qwen_sys/split_20261014/qkd_attn_service_root.sv', 'qkd_attn_service_root')
FACE_M = ('rtl/qwen_sys/split_20261014/qkd_attn_result_face.sv', 'qkd_attn_result_face')
NF = 10
ROOT_FROM_PROG = ('request_valid', 'request_epoch', 'request_layer', 'request_position', 'request_calendar',
                  'q_valid', 'q_beat')
FACE_FROM_ROOT = (('running', 'running'), ('start_qk', 'start_qk'), ('age', 'age'), ('ep', 'ep'), ('layer', 'layer'),
                  ('cal', 'cal'), ('root_local_fault', 'local_fault'), ('root_io_fault', 'io_fault'))
PROG_FROM_FACE = ('result_valid', 'result_beat', 'result_data', 'result_epoch', 'result_layer', 'result_done',
                  'service_fault')


def attention_result_join(graph, root=K.ROOT, prog='attention_programme', rname='attn_root', fname='attn_face'):
    ins, width_of, ep = F._ctx(graph, root)
    if prog not in ins:
        raise ValueError(f'template instance {prog} missing')
    r = F._add_unpriced(graph, ins, rname, ROOT_M, dict(PV_LEAD=None, MUT=0), root)
    f = F._add_unpriced(graph, ins, fname, FACE_M, dict(NF=NF, RESULT_RELAY=None, MUT=0), root)
    p = ins[prog]
    bound = []

    def bind(i, port, items):
        B._bind(i, port, items, width_of)
        bound.append(f'{i["name"]}.{port}')
    for q in ROOT_FROM_PROG:
        bind(r, q, [ep(prog, q)])
    bind(p, 'request_ready', [ep(rname, 'request_ready')])
    for q, s in FACE_FROM_ROOT:
        bind(f, q, [ep(rname, s)])
    for q in PROG_FROM_FACE:
        bind(p, q, [ep(fname, q)])
    graph.setdefault('joins_added', []).append(dict(producer=f'{rname}:{ROOT_M[1]} + {fname}:{FACE_M[1]}',
        bound_inputs=len(bound), owner_note='KVJ-SMALL (a) 10-17: attention result face + service root beside the '
        'programme; finalize out_* and unit faults are die joins (KVJ-G2); PV_LEAD / RESULT_RELAY compiler-priced'))
    return bound


def build(root=K.ROOT):
    graph, bound = F.build(root)
    bound += attention_result_join(graph, root)
    return graph, bound
