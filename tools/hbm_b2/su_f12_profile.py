#!/usr/bin/env python3
"""Materialize an opt-in B1 SU source candidate; never edit released RTL.

The native two-quadrant wiring retains QID2/3 for VM address identity. FULL
arithmetic selection must therefore be independent of QID==0. --full-qid is an
explicit candidate contract, pending the B1 role decision (-1 means both).
The lane and side arithmetic both use MLAT4/ALAT4 with the standard f12_l4 add.
Generated sources are unqualified until component timing/exactness/program gates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = 'rtl/hbm_accel/generic/adapters/static_su'
SOURCES = [f'{BASE}/top/{n}.sv' for n in (
    'ot_hbm_su_static_pgslice_lg', 'ot_hbm_su_static_pgslice',
    'ot_hbm_su_static_pgslice_lg_s', 'ot_hbm_su_static_pgslice_s')]
SOURCES += [f'{BASE}/arithmetic/{n}.sv' for n in (
    'ot_hbm_su_static_side', 'ot_hbm_su_static_side_s')]


def replace_once(text, old, new, label):
    if text.count(old) != 1:
        raise ValueError(f'{label}: expected one {old!r}, found {text.count(old)}')
    return text.replace(old, new, 1)


def side_depth(lm, la):
    exp = 7*lm+8*la+4
    softplus_sqrt = exp+la+19+lm+8*(lm+la)+lm+lm+la+31
    return dict(exp=exp, softplus_sqrt=softplus_sqrt)


def materialize(root, out, full_qid, wiring=None):
    if out.resolve().is_relative_to((root/'rtl').resolve()):
        raise ValueError('profile output must not overwrite released RTL')
    texts = {f:(root/f).read_text() for f in SOURCES}
    names = [n for text in texts.values()
             for n in re.findall(r'(?m)^\s*module\s+(\w+)', text)]
    if len(names) != len(set(names)):
        raise ValueError('ambiguous source modules')
    module_map = {n:n+'__b1f12' for n in names}
    records = []
    out.mkdir(parents=True, exist_ok=True)
    for f, original in texts.items():
        text = original
        if '/top/' in f:
            text = replace_once(text, 'parameter integer QID=0,G=0,',
                f'parameter integer FULL_QID={full_qid}, QID=0,G=0,', f)
            text = replace_once(text, 'MLAT=3,ALAT=3,', 'MLAT=4,ALAT=4,', f)
            if '_lg' in Path(f).stem:
                text = replace_once(text, '.G(G),.READ_RETURN',
                    '.G(G),.FULL_QID(FULL_QID),.READ_RETURN', f)
            else:
                text = replace_once(text, '(QID==0&&L==0)',
                    '((FULL_QID<0||QID==FULL_QID)&&L==0)', f)
                text = replace_once(text, 'if(QID==0&&G==0)',
                    'if((FULL_QID<0||QID==FULL_QID)&&G==0)', f)
        else:
            text = replace_once(text, 'localparam integer MLAT=3, ALAT=3;',
                                'localparam integer MLAT=4, ALAT=4;', f)
        # Rename the whole private source cohort, including the nested softplus
        # definitions. Generic lane/store/arithmetic dependencies stay canonical.
        text = re.sub(r'\b('+'|'.join(map(re.escape, sorted(names, key=len, reverse=True)))+r')\b',
                      lambda m:module_map[m.group(0)], text)
        dest = out/Path(f).name
        dest.write_text('// OPT-IN B1 F12 SOURCE CANDIDATE; no release qualification.\n'+text)
        records.append(dict(source=f, source_sha256=hashlib.sha256(original.encode()).hexdigest(),
                            generated=dest.name, sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
    old, new = side_depth(3,3), side_depth(4,4)
    record = dict(schema='opentallas.hbm.su_f12_candidate.v1',
        status='SOURCE_CANDIDATE_NOT_QUALIFIED', full_qid=full_qid,
        role_decision='pending B1 FULL role contract; QID address identity is preserved',
        module_map=module_map, sources=records,
        required_add_provider='rtl/hdc/ot_hdc_fastfp_lat_c12.sv (f12_l4, never lat4i)',
        core_clock_period_ps=833, lane_parameters=dict(MLAT=4,ALAT=4),
        side_cycles=dict(legacy=old, candidate=new,
                        delta={k:new[k]-old[k] for k in old}),
        legacy_default_rtl_changed=False,
        open_gates=['component bit exactness/mutant', 'compiler/static programme timing',
                    'fresh parent cut maps and physical core source profile', 'TT/FF sign-off'])
    if wiring is not None:
        changed=[]
        for n, cfg in wiring['remaster'].items():
            if not re.fullmatch(r'su_N[WE][0-3]', n):
                continue
            if cfg['master']!='ot_hbm_su_static_pgslice_lg':
                raise ValueError(f'{n}: unexpected source master {cfg["master"]}')
            for key,value in [('MLAT',4),('ALAT',4),('MULTIRATE',0),('RSYNC',0)]:
                if f'.{key}({value})' not in cfg['params']:
                    raise ValueError(f'{n}: native {key} contract not migrated')
            if '.FULL_QID(' in cfg['params']:
                raise ValueError(f'{n}: FULL role already selected')
            cfg['master']=module_map[cfg['master']]
            cfg['params']+=f', .FULL_QID({full_qid})'
            changed.append(n)
        if len(changed)!=8:
            raise ValueError(f'expected eight native SU groups, got {changed}')
        (out/'candidate_wiring.json').write_text(json.dumps(wiring,indent=1)+'\n')
        record['changed_instances']=changed
    (out/'profile.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--full-qid', required=True, type=int, choices=(-1,0,1,2,3))
    p.add_argument('--wiring', type=Path)
    a=p.parse_args()
    r=materialize(ROOT,a.out,a.full_qid,
                  json.loads(a.wiring.read_text()) if a.wiring else None)
    print(json.dumps({k:r[k] for k in ('status','full_qid','side_cycles','changed_instances') if k in r}))

if __name__=='__main__':main()
