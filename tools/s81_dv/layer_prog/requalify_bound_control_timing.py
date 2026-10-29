#!/usr/bin/env python3
"""Combine current local coupons with unchanged measured ring stages.

The real ring/XRT/ring coupon measures seven edges. The unchanged, previously
measured two-edge ring stages therefore leave three edges inside XRT. Changed
dependencies require a fresh coupon receipt; unknown changes fail closed.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re


def qualify(root, previous, xrt_run, seqhost, bk):
    rec = copy.deepcopy(previous)
    if rec.get('schema') != 'opentallas.s81.bound_control_local.v1' or rec.get('verdict') != 'PASS':
        raise ValueError('previous measured local timing receipt required')
    # Retaining stage2 is allowed only for the byte-identical measured rings.
    ring_sources = ['rtl/lib/ot_rst_relay.sv'] + [
        f'rtl/dsrom_sys/s81_dv/slice/{name}.sv' for name in ('ot_s81sl_rstop', 'ot_s81sl_rstopt_xo')]
    for source in ring_sources:
        if hashlib.sha256((root/source).read_bytes()).hexdigest() != rec['source_sha256'][source]:
            raise ValueError('ring changed: measure its stages again: '+source)
    for hb in (0, 1):
        text = (xrt_run/f'run{hb}.log').read_text()
        if not re.search(rf'^XRT_INJECT hb={hb} jobs=192 checks=4224 age=7 errors=0$', text, re.M) or not re.search(r'^PASS$', text, re.M):
            raise ValueError('current ring/XRT/ring coupon did not pass')
        if not re.search(r'^FAIL$', (xrt_run/f'age_mut{hb}.log').read_text(), re.M):
            raise ValueError('wrong-age control was not caught')
    if not re.search(r'^FAIL$', (xrt_run/'run_mut.log').read_text(), re.M):
        raise ValueError('actual forwarding-hop mutant was not caught')
    rows = [line.split() for line in (xrt_run/'sources.sha256').read_text().splitlines()]
    if len(rows) != 1 or rows[0][1] != 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv':
        raise ValueError('current XRT source identity missing')
    fresh = {rows[0][1]: rows[0][0]}
    manifests = []
    for component in (seqhost, bk):
        if component.get('verdict') != 'PASS' or component.get('schema') != rec['schema']:
            raise ValueError('current component timing coupon did not pass')
        manifests.append(component['selection_manifest'])
        for name, value in component['source_sha256'].items():
            if name in fresh and fresh[name] != value:
                raise ValueError('current coupons disagree on shared source '+name)
            fresh[name] = value
        rec['masters'].update(component['masters'])
    if manifests[0] != manifests[1]:
        raise ValueError('current coupons use different selected manifests')
    manifest = manifests[0]
    if hashlib.sha256((root/manifest['path']).read_bytes()).hexdigest() != manifest['sha256']:
        raise ValueError('selected manifest changed after component measurement')
    changed = []
    for name, old_hash in rec['source_sha256'].items():
        actual = hashlib.sha256((root/name).read_bytes()).hexdigest()
        if actual != old_hash:
            if fresh.get(name) != actual:
                raise ValueError('changed source has no current measurement: '+name)
            changed.append(name)
    for name, wanted in fresh.items():
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('coupon source paths must be repository relative')
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != wanted:
            raise ValueError('current coupon source changed: '+name)
    rec['source_sha256'].update(fresh)
    rec['selection_manifest'] = manifests[0]
    rec['current_requalification'] = dict(changed_sources=changed,
        xrt=dict(chain_edges=7, unchanged_ring_edges=2, derived_local_edges=3,
                 hb0_checks=4224, hb1_checks=4224, actual_hops_mutant_caught=True),
        seqhost_metrics=seqhost['metrics'], bk_words=bk['observed_words'],
        scope='Current local components only; actual bound transports remain separately checked')
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'prior', 'xrt-run', 'seqhost', 'bk', 'out'):
        ap.add_argument('--'+name, type=Path, required=True)
    a = ap.parse_args()
    read = lambda p: json.loads(p.read_text())
    rec = qualify(a.root, read(a.prior), a.xrt_run, read(a.seqhost), read(a.bk))
    with a.out.open('x') as out:
        out.write(json.dumps(rec, indent=1)+'\n')
    print('CURRENT_LOCAL_REQUALIFIED', rec['current_requalification']['changed_sources'])


if __name__ == '__main__':
    main()
