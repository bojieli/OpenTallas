#!/usr/bin/env python3
"""Derive correctly named hard views without modifying released evidence."""
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
    suffixes = ['.lef', '_ss.lib', '_ff.lib']
    if (source / 'qfd_link_rx128_tt.lib').exists():
        suffixes.append('_tt.lib')
    for suffix in suffixes:
        src = source / ('qfd_link_rx128' + suffix)
        raw = src.read_bytes()
        text = raw.decode()
        if suffix == '.lef':
            assert 'MACRO ot_qwen_die_cdc_ch\n' in text
            assert 'SIZE 302.4 BY 388.8' in text
        else:
            assert 'cell ("ot_qwen_die_cdc_ch")' in text
        text = text.replace('ot_qwen_die_cdc_ch', 'qfd_cdc1024').replace('qfd_link_rx128', 'qfd_cdc1024')
        dst = out / ('qfd_cdc1024' + suffix)
        dst.write_text(text)
        originals[str(src)] = hashlib.sha256(raw).hexdigest()
        files[dst.name] = hashlib.sha256(dst.read_bytes()).hexdigest()
    record = dict(schema='opentallas.derived_hard_view_identity.v1', name='qfd_cdc1024',
                  rtl_module='ot_qwen_die_cdc_ch', parameters=dict(W=1024, IBUF=4, OCRED=4, AD=8, PIPE=2),
                  source_record='results/closure_loop/qfd_cdc1024_a-1a9caff1a-tc/verdict.json',
                  original_sha256=originals, files=files,
                  tt_library_exported='_tt.lib' in suffixes,
                  changes='library/cell/macro identifiers only; timing, pins and geometry retained byte-for-byte otherwise',
                  setup_corner='TT', tt_setup_ps=127.06, ff_hold_ps=1.16, drc=0,
                  ss_sensitivity_ps=-119.61, qualification='owner option B; SS sensitivity fails')
    (out / 'abstract.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('out', type=Path)
    args = ap.parse_args()
    print(json.dumps(normalize(args.source, args.out), indent=2))
