"""Translate an unchanged BF kernel's replay by source-traced, uniform input delays.

This composes component evidence; it never asserts a new frame replay or physical qualification.
"""
import copy
import hashlib
import json
from pathlib import Path

KERNELS = (
    'rtl/v41rom/ot_v41_bf_front_core_roots.sv',
    'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_roots.sv',
    'rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv',
    'rtl/v41die/ot_s81_cfg7_seq_bfp.sv',
    'rtl/dsrom_sys/s81_die_bind/ot_s81_bf_prog_seq.sv',
)
INPUTS = ('cfg', 'f_prog', 'go', 'x0', 'x1', 'xb_data', 'xb_meta')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def input_shifts(inputs):
    """Every value/descriptor at one front moves together; no fitted output offset."""
    old, new = inputs['old'], inputs['current']
    if old.keys() != new.keys():
        raise ValueError('BF front identity changed')
    shifts = {}
    for cell, ports in old.items():
        pair = cell.rsplit('.u_e', 1)[-1]
        if pair == cell or not pair.isdigit():
            raise ValueError('BF front has no pair identity')
        delta = set()
        for port in INPUTS:
            before, after = dict(ports[port]), dict(new[cell][port])
            if not before or before.keys() != after.keys():
                raise ValueError('BF input producer changed: ' + cell + '.' + port)
            delta.update(after[k] - before[k] for k in before)
        if len(delta) != 1:
            raise ValueError('BF inputs do not share one translation: ' + cell)
        shift = delta.pop()
        if pair in shifts:
            raise ValueError('BF pair identity is ambiguous')
        shifts[pair] = shift
    return shifts

def translate(base, inputs):
    q = base.get('asbuilt_source_qualification', {})
    if (not base.get('ok') or q.get('status') != 'PASS_STATIC_REPLAY'
            or q.get('clock_ps') != 833 or not q.get('native_family_hold')
            or not q.get('payload_control_caught') or not q.get('one_edge_control_caught')):
        raise ValueError('BF component has no qualified replay/controls')
    shifts = input_shifts(inputs)
    if not set(base['fits']) <= set(shifts):
        raise ValueError('BF input/replay pair sets differ')
    # A replay may cover only the three production pairs of a four-pair frame.
    # Never invent a partial for an unexercised extra pair.
    shifts = {p: shifts[p] for p in base['fits']}
    out = copy.deepcopy(base)
    # The old whole-frame replay stays in its own record; only kernel emission is composed.
    for key in list(out):
        if key.startswith('ret_') or key in ('ret_composed', 'log'):
            out.pop(key)
    for pair, fit in out['fits'].items():
        for key in ('go_edge', 'first_issue_edge', 'last_issue_edge'):
            if key in fit:
                fit[key] += shifts[pair]
    for leaf, edges in out['pv'].items():
        pair = leaf[1:-3]
        out['pv'][leaf] = [e + shifts[pair] for e in edges]
        for row in out.get('pv_all', {}).get(leaf, []):
            row['edge'] += shifts[pair]
    out['calendar'] = 'component_composition_bf_idle_q'
    return out, shifts

def qualify(rec, source_root, replay_root, schedule_path, frame_instance):
    q = rec['asbuilt_source_qualification']
    c = q.get('component_composition', {})
    if q.get('status') != 'COMPONENT_COMPOSITION' or c.get('frame') != frame_instance:
        raise ValueError('BF composition selects another frame or scope')
    replay = (Path(replay_root) / c['replay_file']).resolve()
    if digest(replay) != c['replay_file_sha256']:
        raise ValueError('BF component replay changed')
    base = json.loads(replay.read_text())[rec['key']]
    for name in KERNELS:
        if digest(Path(source_root) / name) != base['asbuilt_source_qualification']['source_sha256'][name]:
            raise ValueError('BF arithmetic/programme kernel changed: ' + name)
    if digest(schedule_path) != q['schedule_sha256']:
        raise ValueError('BF composition return schedule changed')
    sch = json.loads(Path(schedule_path).read_text())
    if not frame_instance or sch.get('bound_plan', {}).get('frame_instance') != frame_instance:
        raise ValueError('BF composition schedule selects another frame')
    required = set(sch.get('source_sha256', {})) | set(KERNELS)
    if not required <= q['source_sha256'].keys():
        raise ValueError('BF composition source closure is incomplete')
    for name, expected in q['source_sha256'].items():
        if digest(Path(source_root) / name) != expected:
            raise ValueError('BF composition selected source changed: ' + name)
    trace = Path(replay_root) / c['input_trace_file']
    if digest(trace) != c['input_trace_file_sha256']:
        raise ValueError('BF source-traced input evidence changed')
    rows = [r for r in json.loads(trace.read_text()) if r['class_'] == c['source_trace_class']]
    if len(rows) != 1 or rows[0]['inputs'] != c['inputs']:
        raise ValueError('BF input translation differs from source trace')
    if rows[0]['current_seam_extra'] != sch.get('bound_plan', {}).get('seam_extra_stages'):
        raise ValueError('BF input trace selects another source seam class')
    predicted, shifts = translate(base, c['inputs'])
    if c.get('input_shifts') != shifts:
        raise ValueError('BF composition input translation changed')
    for key in ('pv', 'pv_all', 'fits', 'desc', 'lat_issue_to_pv', 'leaf_ret_corr'):
        if rec.get(key) != predicted.get(key):
            raise ValueError('BF composition differs from component prediction: ' + key)
    return 'component_composition_bf_idle_q'
