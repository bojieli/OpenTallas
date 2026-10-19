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
  stack); attn_root.fused_program_capability <- the boot image capability bit (as attention_programme's): RTL-BUILD-KV/FAULT
  10-18 capability_join = the die cfg capability word (qkd_kv_die_cfg CAP=1).
Bench + mutants: tools/qwen_kv_die/attn_result_face_gate.py.  Never a die netlist.
"""
import os
import kv_static as K
import kv_static_boot_join as B
import kv_static_kvjf_join as F

ROOT_M = ('rtl/qwen_sys/split_20261014/qkd_attn_service_root.sv', 'qkd_attn_service_root')
FACE_M = ('rtl/qwen_sys/split_20261014/qkd_attn_result_face.sv', 'qkd_attn_result_face')
# KV-PLAN-FIN 10-17: OT_KV_PVFIN=1 (default ON under OT_KV_STATIC_DIE=1) joins the BEAT-STREAM face qkd_attn_result_face_s:
# its f_valid / f_beat / f_epoch / f_data (512 b) are fed by the stream final join qkd_pv_fin_s (die element pvfin,
# results/arch/qwen_kv_pvfin_1017/plan.json); F_DLY (pin stage + die relay edges pvfin -> face) is compiler-priced.
FACE_S_M = ('rtl/qwen_sys/split_20261014/qkd_attn_result_face_s.sv', 'qkd_attn_result_face_s')
STREAM = __import__('os').environ.get('OT_KV_PVFIN', __import__('os').environ.get('OT_KV_STATIC_DIE', '0')) == '1'
NF = 10
ROOT_FROM_PROG = ('request_valid', 'request_epoch', 'request_layer', 'request_position', 'request_calendar',
                  'q_valid', 'q_beat')
FACE_FROM_ROOT = (('running', 'running'), ('start_qk', 'start_qk'), ('age', 'age'), ('ep', 'ep'), ('layer', 'layer'),
                  ('cal', 'cal'), ('root_local_fault', 'local_fault'), ('root_io_fault', 'io_fault'))
PROG_FROM_FACE = ('result_valid', 'result_beat', 'result_data', 'result_epoch', 'result_layer', 'result_done',
                  'service_fault')


def attention_result_join(graph, root=K.ROOT, prog='attention_programme', rname='attn_root', fname='attn_face', stream=None):
    stream = STREAM if stream is None else stream
    ins, width_of, ep = F._ctx(graph, root)
    if prog not in ins:
        raise ValueError(f'template instance {prog} missing')
    # KV-ATTNKIT 10-18: OT_KV_ATTN_LAND -> CAL_PIPE=1 (kv_static_die.ATTN_LAND)
    cp = 1 if os.environ.get('OT_KV_ATTN_LAND', '0') == '1' else 0
    r = F._add_unpriced(graph, ins, rname, ROOT_M, dict(PV_LEAD=None, CAL_PIPE=cp, MUT=0), root)
    f = (F._add_unpriced(graph, ins, fname, FACE_S_M, dict(NF=NF, RESULT_RELAY=None, F_DLY=None, CAL_PIPE=cp, MUT=0), root) if stream else
         F._add_unpriced(graph, ins, fname, FACE_M, dict(NF=NF, RESULT_RELAY=None, MUT=0), root))
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
    graph.setdefault('joins_added', []).append(dict(producer=f'{rname}:{ROOT_M[1]} + {fname}:{(FACE_S_M if stream else FACE_M)[1]}',
        bound_inputs=len(bound), owner_note='KVJ-SMALL (a) 10-17: attention result face + service root beside the '
        'programme; finalize out_* and unit faults are die joins (KVJ-G2); PV_LEAD / RESULT_RELAY compiler-priced'))
    return bound


CALGEN_M = ('rtl/qwen_sys/split_20261014/qkd_attn_cal_gen.sv', 'qkd_attn_cal_gen')
# KVJ-G2b 10-17: the die image's STRETCH=1 parameters (kv_static_programme die report: profile die, d_qk = QK_ISSUE_AGE 62 -
# 34, d_rl = RL 95 - 19, service_end 1777, compiled_rx_cmd 2; G3S2 = the v1.4.3 staged head ingress)
# KV-ECTL4 10-18: D_QK = the die's QK_ISSUE_AGE (K_RT_BUDGET + 11, one K round trip for every ECTL frame) - 34
import kv_static_ages as _AGES   # noqa: E402
CALGEN_P = dict(G3S2=1, RX_CMD=2, STRETCH=1, D_QK=_AGES.K_RT_BUDGET + _AGES.QK_WRITE_BEFORE_READ - _AGES.QK_ISSUE_AGE_KIT,
                D_RL=76, SERVICE_END=1777, MUT=0)
PROG_FROM_CALGEN = (('compiled_calendar', 'cal'), ('compiled_rx_cmd', 'rx_cmd'), ('compiled_tx_first', 'tx_first'),
                    ('compiled_end', 'end_age'))


def cal_gen_join(graph, root=K.ROOT, prog='attention_programme', lp='layer_programme', name='attn_cal'):
    """qkd_attn_cal_gen STRETCH=1 in the attention control tile: go <- the layer programme's stage_start (the compiler
    places it CAL_GEN_LAT = 10 edges before the first issue; margin 867 in the die report), ctx_t / epoch <- the layer
    programme; the programme's compiled_calendar / rx_cmd / tx_first / end <- the generator's held outputs."""
    ins, width_of, ep = F._ctx(graph, root)
    for need in (prog, lp):
        if need not in ins:
            raise ValueError(f'template instance {need} missing')
    c = F._add_unpriced(graph, ins, name, CALGEN_M, dict(CALGEN_P), root)
    p = ins[prog]
    bound = []

    def bind(i, port, items):
        B._bind(i, port, items, width_of)
        bound.append(f'{i["name"]}.{port}')
    bind(c, 'go', [ep(lp, 'stage_start')])
    bind(c, 'ctx_t', [ep(lp, 'ctx_t')])
    bind(c, 'epoch', [ep(lp, 'epoch')])
    for q, s in PROG_FROM_CALGEN:
        bind(p, q, [ep(name, s)])
    graph.setdefault('joins_added', []).append(dict(producer=f'{name}:{CALGEN_M[1]}', bound_inputs=len(bound),
        owner_note='KVJ-G2b 10-17: attention calendar generator STRETCH=1 (D_QK 28, D_RL 76, SERVICE_END 1777) feeds '
        'the programme compiled_* (replaces the boot-image constants)'))
    return bound


CAP_CONSUMERS = ('attention_programme', 'attn_root')


def capability_join(graph, root=K.ROOT, cfg='diecfg'):
    """RTL-BUILD-KV/FAULT 10-18 (P8): the boot image's fused attention-programme capability bit has a real producer: the
    die cfg's capability word (qkd_kv_die_cfg CAP=1, pre-boot target 10 word 32 + NRST, POR-held, 0 until sealed) ->
    attention_programme.fused_program_capability (registered there into capability_q) and
    attn_root.fused_program_capability (checked on every request: 0 -> local_fault).  A configuration net: static after
    the seal, no production path launches from it."""
    ins, width_of, ep = F._ctx(graph, root)
    if cfg not in ins or ins[cfg]['parameters'].get('CAP') != 1:
        raise ValueError(f'{cfg}: qkd_kv_die_cfg CAP=1 required')
    bound = []
    for n in CAP_CONSUMERS:
        if n not in ins:
            raise ValueError(f'{n} missing')
        if ins[n]['inputs'].get('fused_program_capability', 0) is not None:
            raise ValueError(f'{n}.fused_program_capability already bound')
        B._bind(ins[n], 'fused_program_capability', [ep(cfg, 'fused_program_capability')], width_of)
        bound.append(f'{n}.fused_program_capability')
    graph.setdefault('joins_added', []).append(dict(producer=f'{cfg}.fused_program_capability', bound_inputs=len(bound),
        owner_note='RTL-BUILD-KV/FAULT 10-18 (P8): boot-loaded capability word of the die cfg (target 10) -> attention '
        'programme + service root (replaces the open boot-image capability bit)'))
    return bound


def build(root=K.ROOT):
    graph, bound = F.build(root)
    bound += attention_result_join(graph, root)
    bound += cal_gen_join(graph, root)
    bound += capability_join(graph, root)
    return graph, bound
