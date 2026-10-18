#!/usr/bin/env python3
"""Exhaustively check the wire permutation and physical ownership of1068 BF bits.

The immutable original die wrapper is the independent ABI reference. All1068
one-hot words are checked against the actual candidate assignments and concat;
all3269 original pin shapes are checked against the immutable request.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SEED = '5fce4c7b5607c476c206908187ebf6371fbb73ba'


def original(path):
    return subprocess.check_output(['git','show',f'{SEED}:{path}'],cwd=ROOT)


def audit(mutant=None):
    reference=original('rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_static.sv').decode()
    candidate=(ROOT/'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_roots.sv').read_text()
    request=json.loads((ROOT/'physical/ref_tile_specs/s81_bf_native_1015/front_five_roots/pin_request.json').read_text())
    old=json.loads(original('physical/ref_tile_specs/s81_bf_native_1015/static_pins_c10s/pin_request.json'))
    if mutant=='concat':
        candidate=candidate.replace('{xb_data,xb_meta}','{xb_meta,xb_data}')
    if mutant=='wire_swap':
        candidate=candidate.replace('assign w_go_bf = xb[0];','assign w_go_bf = xb[1];')
    concat=re.search(r'wire\s+\[1067:0\]\s+xb\s*=\s*\{(\w+),(\w+)\}',candidate)
    assert concat, 'actual reconstruction missing'
    widths={'xb_data':1024,'xb_meta':44}
    # The input is the immutable legacy-order stream. The compiler physically
    # emits lower44 control bits on S and upper1024 data bits on N.
    input_word={}
    assignment=re.compile(r'assign\s+(\w+(?:\[\d+\])?)\s*=\s*xb\[(\d+)\]\s*;')
    ref=dict((n,int(i)) for n,i in assignment.findall(reference))
    cand=dict((n,int(i)) for n,i in assignment.findall(candidate))
    assert len(ref)==1068 and set(ref)==set(cand), '1068 real assignments required'
    for bit in range(1068):
        word=1<<bit
        input_word['xb_data']=word>>44
        input_word['xb_meta']=word&((1<<44)-1)
        hi,lo=concat.groups()
        reconstructed=(input_word[hi]<<widths[lo])|input_word[lo]
        for wire,index in ref.items():
            assert ((word>>index)&1)==((reconstructed>>cand[wire])&1), f'bit{bit} actualwire{wire}'
    pins=request['pins']
    assert len(pins)==3272 and len(old['pins'])==3269
    for name,p in old['pins'].items():
        if name.startswith('xb['):
            i=int(name[3:-1]);new=f'xb_meta[{i}]' if i<44 else f'xb_data[{i-44}]'
            if mutant=='physical_alias' and i==0:new='xb_data[0]'
            assert pins[new]==p, f'physical shape/order changed: {name}->{new}'
            assert pins[new]['face']==('S' if i<44 else 'N'), f'wrong clock face: {new}'
        else:
            assert pins[name]==p, f'old physical pin changed: {name}'
    return dict(bits=1068,one_hot_checks=1068*1068,unchanged_old_pin_shapes=3269,
                source_sha256=hashlib.sha256(candidate.encode()).hexdigest(),
                reference_sha256=hashlib.sha256(reference.encode()).hexdigest())


def main():
    p=argparse.ArgumentParser(__doc__)
    p.add_argument('--mutant',choices=['concat','wire_swap','physical_alias'])
    a=p.parse_args()
    try:
        result=audit(a.mutant)
    except AssertionError as error:
        if a.mutant:
            print(f'MUTANT BF actual ABI {a.mutant} FAIL: {error}')
            raise SystemExit(1)
        raise
    if a.mutant:raise SystemExit('ERROR: mutant unexpectedly survived')
    print('PASS BF actual ABI '+json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
