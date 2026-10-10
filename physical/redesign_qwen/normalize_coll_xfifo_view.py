#!/usr/bin/env python3
"""Name the retained native collective hard cell without altering its contract."""
import argparse
import hashlib
import json
from pathlib import Path


def normalize(source, out):
    source, out = Path(source), Path(out)
    if out.exists():
        raise ValueError('refuse to overwrite derived evidence')
    out.mkdir(parents=True)
    originals, files = {}, {}
    for suffix in ['.lef', '_ss.lib', '_ff.lib', '_tt.lib']:
        src = source / ('qfd_coll_xfifo_b' + suffix)
        raw = src.read_bytes()
        text = raw.decode()
        marker = 'MACRO ot_qwen_die_coll_xfifo\n' if suffix == '.lef' else 'cell ("ot_qwen_die_coll_xfifo")'
        assert marker in text
        text = text.replace('ot_qwen_die_coll_xfifo', 'qfd_coll_xfifo_b')
        dst = out / src.name
        dst.write_text(text)
        originals[str(src)] = hashlib.sha256(raw).hexdigest()
        files[dst.name] = hashlib.sha256(dst.read_bytes()).hexdigest()
    record = dict(schema='opentallas.derived_hard_view_identity.v1', name='qfd_coll_xfifo_b',
                  rtl_module='ot_qwen_die_coll_xfifo',
                  parameters=dict(WSQ=546, WCQ=516, N=4, MB=513, CQ_AD=64, PIPE=0),
                  initial_forward_credits=4, engine_input_buffer_required=4,
                  source_record='results/closure_loop/qfd_coll_xfifo_b-66fd85cda-tc/verdict.json',
                  original_sha256=originals, files=files, actual_tt_library=True,
                  changes='cell/macro identifier only; timing, pins and geometry retained otherwise',
                  tt_setup_ps=33.86, ff_hold_ps=5.73, drc=0, ss_sensitivity_ps=-282.63,
                  qualification='owner option B child; production reset/fault wiring and die qualification unresolved')
    (out / 'abstract.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('out', type=Path)
    args = ap.parse_args()
    print(json.dumps(normalize(args.source, args.out), indent=2))
