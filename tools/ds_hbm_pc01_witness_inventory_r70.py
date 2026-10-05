"""Finite source identity census, without provider construction or numerical execution.
This prices neither provider closure nor JSON scanner/allocator workspace.
"""
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NATIVE='results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
REFERENCE='results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/independent_prefix_expected_outputs.json'
NATIVE_SHA='c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264'
REFERENCE_SHA='91c803a93df18e011cd7ee6c5e0a84c8fc091136718ca329e5f2928349b3f342'

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def first_instructions(path,count):
    """Parse top-level keys structurally; retain only one decoded instruction at a time."""
    decoder=json.JSONDecoder()
    with gzip.open(path,'rt',encoding='utf-8') as f:
        buf='';pos=0
        def fill():
            nonlocal buf,pos
            block=f.read(65536)
            if not block:raise ValueError('truncated native JSON')
            buf=buf[pos:]+block;pos=0
        def token(expected=None):
            nonlocal pos
            while True:
                while pos<len(buf) and buf[pos].isspace():pos+=1
                if pos<len(buf):break
                fill()
            value=buf[pos];pos+=1
            if expected is not None and value!=expected:raise ValueError('native JSON structure')
            return value
        def value():
            nonlocal pos
            while True:
                while pos<len(buf) and buf[pos].isspace():pos+=1
                try:r,end=decoder.raw_decode(buf,pos);pos=end;return r
                except json.JSONDecodeError:fill()
        token('{')
        while True:
            key=value();token(':')
            if key=='instructions':
                token('[');out=[]
                for i in range(count):
                    if i:token(',')
                    out.append(value())
                return out
            value()
            if token()!=',':raise ValueError('instructions key missing')

def model(root=ROOT):
    root=Path(root);native=root/NATIVE;refpath=root/REFERENCE
    if digest(native)!=NATIVE_SHA or digest(refpath)!=REFERENCE_SHA:
        raise ValueError('exact original native/reference required')
    ops=first_instructions(native,2)
    ref=json.loads(refpath.read_bytes())
    rows=[r for r in ref['expectations'] if r['PC']==1]
    generations={r['generation'] for r in rows}
    if generations!={1}:raise ValueError('explicit source generation changed')
    keys=[];counts={}
    for pc,op in enumerate(ops):
        if op['pc']!=pc:raise ValueError('native prefix order')
        ranks=[b['rank'] for b in op['rank_bindings'] if not b.get('empty_owned_extent')]
        if len(ranks)!=len(set(ranks)):raise ValueError('duplicate native rank')
        current=[(pc,w['version'],rank,1,'data') for w in op['writes'] for rank in ranks]
        if len(current)!=len(set(current)):raise ValueError('duplicate output key')
        keys.extend(current);counts[str(pc)]={'nonempty_ranks':len(ranks),'writes':len(op['writes']),'outputs':len(current)}
    offered={(r['PC'],r['version'],r['rank'],r['generation'],r['field']) for r in rows}
    if offered!={k for k in keys if k[0]==1}:raise ValueError('PC1 reference/native identity mismatch')
    if counts['0']['outputs']!=384 or counts['1']['outputs']!=192:raise ValueError('source PC01 count changed')
    serialized=json.dumps(sorted(keys),sort_keys=True,separators=(',',':')).encode()
    sources=[NATIVE,REFERENCE,'tools/ds_hbm_prefix_observed_outputs_r42.py',
             'tools/ds_hbm_checkpoint_phases_r70.py','tools/ds_hbm_pc01_child_r70.py']
    return dict(schema='R70_SOURCE_PC01_WITNESS_IDENTITY_CENSUS',counts=counts,
        boundary_seen_keys={'PC0':384,'PC1':576},
        combined_seen_key_canonical_bytes=len(serialized),combined_seen_key_SHA256=hashlib.sha256(serialized).hexdigest(),
        source_sha256={p:digest(root/p) for p in sources},
        scope='Source-required keys only; no observed payload or producer closure supplied.',
        generation=1,generation_source='pinned PC1 independent reference; actual constructor generation must match',
        required_actual_seen_equality=True,actual_observations=False,
        provider_closure_bound_complete=False,complete_source_phase_bounds=False,
        RAM_admission=False,remote_GO=False,
        remaining=['actual provider/quiescent closure metadata typed upper bounds',
                   'witness provenance and journal-summary object allocation bounds',
                   'JSON parse/scanner/allocator and serialization coexistence bounds',
                   'physical RAM and peer growth lease', 'exact persistent staging and refreshed disk'])

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',type=Path)
    a=p.parse_args();result=model()
    if a.verify and result!=json.loads(a.verify.read_text()):raise ValueError('witness census replay differs')
    if a.out:a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result['counts'],sort_keys=True))
