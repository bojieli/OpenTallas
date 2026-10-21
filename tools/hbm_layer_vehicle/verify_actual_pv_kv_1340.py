#!/usr/bin/env python3
"""Bind an existing native KV capture to the selected semantic PV record.

This validates input provenance only. Captured P/O are comparison data; no
probability input image or runtime output stimulus is emitted.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify(capture_dir, fixture_dir, layer=0):
    cap=Path(capture_dir);fixture=Path(fixture_dir)
    meta=json.loads((cap/'att_kv.json').read_text())
    semantic=json.loads((fixture/'records.json').read_text())
    if meta['layer']!=layer or semantic['layer']!=layer:raise ValueError('layer mismatch')
    if sha(cap/'att_kv.npz')!=meta['npz_sha256']:raise ValueError('capture NPZ digest mismatch')
    pv=next(r for r in meta['records'] if r['rank']==0 and r['op']=='ATT.PV' and r['occ']==0)
    base=next(r for r in semantic['records']['0'] if r['op']=='ATT.PV' and r['occ']==0)
    if pv['tag']!=base['tag'] or any(pv['eff'][k]!=base['desc'][k] for k in ('A','B','O')):
        raise ValueError('semantic effective A/B/O reference mismatch')
    with np.load(cap/'att_kv.npz') as z:
        for entry in pv['arrays'].values():
            a=z[entry['key']]
            if list(a.shape)!=entry['shape'] or str(a.dtype)!=entry['dtype'] or hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()!=entry['sha256']:
                raise ValueError('captured array shape/dtype/content mismatch')
        K=z[pv['arrays']['K']['key']]
        if K.shape!=(base['desc']['A'][1],base['desc']['O'][1]) or K.dtype!=np.float32:
            raise ValueError('decoded K rows must fit genuine PV input/output dimensions')
        # ds_layer_fixtures reads B at descriptor width128; ATT expands hd512.
        # The selected L0 ring starts at0, so the captured row prefix reproduces
        # the original declared HBM operand bytes exactly.
        if pv['ring']['first']!=0 or pv['ring']['n']!=pv['ring']['m']:
            raise ValueError('raw B projection needs an explicit ring slot mapping')
        raw_rows=pv['ring']['n'];raw_bytes=base['inputs']['B']['bytes']
        if raw_bytes%(4*raw_rows):raise ValueError('unaligned FP32 raw B footprint')
        raw_cols=raw_bytes//(4*raw_rows)
        raw_view=np.ascontiguousarray(K[:raw_rows,:raw_cols])
        raw_sha=hashlib.sha256(raw_view.tobytes()).hexdigest()
        if raw_view.nbytes!=raw_bytes or raw_sha!=base['inputs']['B']['sha256']:
            raise ValueError('captured K raw B projection differs from declared semantic HBM digest')
        qk=next(r for r in meta['records'] if r['rank']==0 and r['op']=='ATT.QK' and r['occ']==0)
        if not np.array_equal(K.view(np.uint32),z[qk['arrays']['K']['key']].view(np.uint32)):
            raise ValueError('actual shared QK/PV K arrays mismatch')
    for role,kind in [('A','inputs'),('O','outputs')]:
        if pv['arrays'][role]['sha256']!=base[kind][role]['sha256']:
            raise ValueError('capture differs from selected fixture P/O identity')
    return dict(status='PASS_EXISTING_INPUT_CAPTURE_BINDING_ONLY',hardware_executed=False,
        capture_npz_sha256=meta['npz_sha256'],capture_metadata_sha256=sha(cap/'att_kv.json'),
        semantic_records_sha256=sha(fixture/'records.json'),semantic_k=base['k'],
        actual_B_reference=base['desc']['B'],declared_raw_B=base['inputs']['B'],decoded_K=pv['arrays']['K'],
        K_accessor='ds_att_kv.py -> machine.att_rows(M,rd,die,L,hd); att_images.load_ds(capture_parent,layer,rank0)',
        raw_B_projection=dict(rows=raw_rows,columns=raw_cols,bytes=raw_bytes,sha256=raw_sha,declared_digest_matches=True),
        raw_vs_decoded='ATT expands actual head width512; selected B descriptor captures128columns. Verified K[:, :128] matches declared65536byte raw B digest exactly.',
        captured_P_and_O='identity/scoreboard comparison only; no M/xw/output stimulus emitted',
        probability_preloads=0,selected_PV_retire_qualified=False,
        remaining='current selected SM3 PV pipeline/retirement profile and actual connected producer/copy/page-consumer execution OPEN')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture',type=Path,required=True);p.add_argument('--fixture',type=Path,required=True)
    p.add_argument('--layer',type=int,default=0);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();x=verify(a.capture,a.fixture,a.layer);a.out.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))


if __name__=='__main__':main()
