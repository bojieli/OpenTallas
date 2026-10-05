#!/usr/bin/env python3
"""Enroll AQ ACT successor in a supplied actual parent sourcebook, default off."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NS = 'rtl/qwen_sys/service_aq_act_enrollment_20261005/'
REPLACE = {
    'rtl/qwen_sys/baseline_ar_stream4/ot_qwen_rom_rt_die_w12_stream4_tagged_ar.sv': NS + 'ot_qwen_rom_rt_die_w12_stream4_tagged_ar_aq_act_parent.sv',
    'rtl/hdc/kv/ot_qwen_hbm_stream4_tagged.sv': NS + 'ot_qwen_hbm_stream4_tagged_aq_act_parent.sv',
}
EXTRA = [NS + 'ot_qwen_service_stack_aq_act_select.sv',
    'rtl/hbm_accel/svc/aq_act_cut/ot_hbm_r14_stream_stack_aq_act_cut.sv',
    'rtl/hbm_accel/svc/aq_act_cut/ot_hbm_r14_stream_pc_aq_act_cut.sv']

def enroll(paths):
    paths = [str(Path(p).resolve().relative_to(ROOT)) if Path(p).is_absolute() else p for p in paths]
    if not set(REPLACE).issubset(paths):
        raise ValueError('requires actual enclosing baseline AR parent AND its STREAM4 controller')
    return list(dict.fromkeys([REPLACE.get(p, p) for p in paths] + EXTRA))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-list', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--enable-aq-act-cut', action='store_true')
    a = ap.parse_args()
    paths = enroll(a.source_list.read_text().splitlines())
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / 'sources.f').write_text('\n'.join(str(ROOT / p) for p in paths) + '\n')
    (a.output / 'selection.json').write_text(json.dumps(dict(
        top='ot_qwen_rom_rt_die_w12_stream4_tagged_ar_aq_act_parent',
        parameters={'AQ_ACT_CUT': int(a.enable_aq_act_cut)},
        source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths},
        model='results/uarch/qwen_service_parent_enrollment_20261005/model.json',
        physical_admission=False, runtime_qualification=False,
        scope='connected source enrollment; existing clocks/CDC/command edges unchanged'), indent=2)+'\n')
