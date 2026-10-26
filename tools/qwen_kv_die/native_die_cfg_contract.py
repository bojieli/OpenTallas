#!/usr/bin/env python3
"""Derive active ECTL identities and inactive DCFG defaults from native RTL.

This is not a timing image generator. Age words and capability must come from
the current compiler contract. Inactive reset words preserve the actual field
flop reset value; they do not invent regional-reset delays.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def module(text, name):
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    found = re.findall(r'\bmodule\s+' + re.escape(name) + r'\b.*?\bendmodule\b', text, re.S)
    if len(found) != 1:
        raise ValueError(f'expected exactly one {name} module')
    return found[0]


def derive(ctl_text, cfg_text, fields_text, ectl_text, hroot_text, relays_text, cfg_sinks):
    ctl = module(ctl_text, 'qkd_kvs_ctl')
    cfg = module(cfg_text, 'qkd_kv_die_cfg_a_c32')
    fields = module(fields_text, 'qkd_kv_die_cfg_c32_fld')
    hroot = module(hroot_text, 'qkd_kvs_hroot')
    relay = re.sub(r'\s+', '', module(relays_text, 'qkd_kv_stack_relays_l'))
    if ('fan_c<=dn[HW-((MUT==1)?1:0)+:FW];' not in relay or
            'fan<=fan_c;' not in relay or 'MUT=0)' not in relay):
        raise ValueError('hroot relay fan mapping is no longer the audited identity')
    call = re.search(r'qkd_kv_stack_relays_l\s*#\((.*?)\)\s+u_rly\s*\((.*?)\);', hroot, re.S)
    if not call:
        raise ValueError('hroot relay instance absent')
    relay_params = {k:int(v) for k,v in re.findall(r'\.(HW|FW|MUT)\((\d+)\)', call[1])}
    if relay_params.get('HW') != 784 or relay_params.get('FW') != 334 or relay_params.get('MUT', 0) != 0:
        raise ValueError('hroot relay dimensions or mutation mode changed')
    if not re.search(r'\.dn\(i_ctl\)', call[2]) or not re.search(r'\.fan\(w_rly__fan\)', call[2]):
        raise ValueError('hroot relay input/output binding changed')
    for name in ('qkd_ectl_a_tp8_direct', 'qkd_ectl_b_tp8_direct', 'qkd_ectl_c_tp8_direct'):
        role = module(ectl_text, name)
        if not re.search(r'\.cfg_s\(cfg\[1:0\]\)', role) or not re.search(r'\.cfg_e\(cfg\[4:2\]\)', role):
            raise ValueError(f'{name}: ECTL element/stack identity encoding changed')
    match = re.search(r'qkd_kv_die_cfg_a_c32\s*#\((.*?)\)\s+u_dcfg\s*\((.*?)\);', ctl, re.S)
    if not match:
        raise ValueError('native DCFG instance missing')
    params = {k: int(v) for k, v in re.findall(r'\.(NRST|CAP|AGES)\((\d+)\)', match[1])}
    if params != dict(NRST=43, CAP=1, AGES=1):
        raise ValueError(f'unexpected native DCFG ABI {params}')
    compact = re.sub(r'\s+', '', cfg)
    if 'localparamintegerNA=(AGES!=0)?19:0;' not in compact or 'localparamintegerNW=A0+NA;' not in compact:
        raise ValueError('native age-word count/seal location contract changed')
    if not re.search(r'if\s*\(!rn\)\s*q\s*<=\s*\{W\{1\x27b0\}\}', fields):
        raise ValueError('field reset default is not the proven all-zero value')
    if not re.search(r'qkd_kv_die_cfg_c32_fld\s*#\(\.W\(8\)\)\s+u_r\b', cfg):
        raise ValueError('reset words no longer use the audited eight-bit field')
    inactive = {}
    for port, width in [('rst_dly', 344), ('ectl_b_cfg', 160), ('ectl_c_cfg', 160)]:
        m = re.search(r'\.' + port + r'\((\w+)\)', match[2])
        if not m:
            raise ValueError(f'{port} output connection absent')
        wire = m[1]
        uses = len(re.findall(r'\b' + re.escape(wire) + r'\b', ctl))
        if uses != 2:  # one declaration, one producer output; any reader is forbidden
            raise ValueError(f'{wire}: expected no readers, found {uses-2} additional references')
        if not re.search(r'\bwire\s*\[' + str(width-1) + r':0\]\s*' + re.escape(wire) + r'\s*;', ctl):
            raise ValueError(f'{wire}: exact private wire declaration absent')
        inactive[port] = dict(bits=width, real_readers=0, architectural_reset_value=0)
    # The actual output slice map determines stack order; do not assume that
    # array order and cfg={element,stack} have the same numeric encoding.
    stacks = {}
    for st in ('WS', 'WN', 'ES', 'EN'):
        assignment = re.search(r'assign\s+o_hroot_' + st + r'\s*=\s*(.*?);', ctl, re.S)
        if not assignment:
            raise ValueError(f'{st} hroot assignment absent')
        leading = re.match(r'\s*\{\s*\{\s*(?:w_dcfg__ectl_a_cfg\[\d+:\d+\]\s*,\s*){8}', assignment[1])
        if not leading:
            raise ValueError(f'{st} ECTL config is no longer the leading packed field')
        slices = [(int(a), int(b)) for a, b in re.findall(r'w_dcfg__ectl_a_cfg\[(\d+):(\d+)\]', assignment[1])]
        if len(slices) != 8 or any(a-b != 4 or b % 5 for a, b in slices):
            raise ValueError(f'{st} ECTL identity slice map changed')
        indexes = sorted(b//5 for _, b in slices)
        if [b//5 for _, b in slices] != list(reversed(indexes)):
            raise ValueError(f'{st} ECTL group bit order changed')
        stack = indexes[0]//8
        if indexes != list(range(8*stack, 8*stack+8)):
            raise ValueError(f'{st} group indexes are not a complete stack')
        port_width = re.search(r'output\s+wire\s*\[(\d+):0\]\s*o_hroot_' + st + r'\b', ctl)
        input_width = re.search(r'input\s+wire\s*\[(\d+):0\]\s*i_ctl\b', hroot)
        if not port_width or not input_width or port_width[1] != input_width[1]:
            raise ValueError(f'{st} ctl/hroot packed word widths differ')
        cfg_lsb = int(port_width[1]) + 1 - 40
        for group in range(8):
            endpoint = re.search(r'assign\s+o_c' + str(group) + r'\s*=\s*w_rly__fan\[(\d+):(\d+)\]\s*;', hroot)
            if not endpoint or int(endpoint[1])-int(endpoint[2]) != 4 or int(endpoint[2])+relay_params['HW'] != cfg_lsb+5*group:
                raise ValueError(f'{st} hroot o_c{group} selects another config group')
            for bit in range(5):
                key = f'ectl_{st}_{group}.cfg[{bit}]'
                value = cfg_sinks.get(key)
                expected = f'kvs_hroot_{st}.o_c{group}[{bit}]'
                if not isinstance(value, list) or len(value) != 4 or value[0] != 'pin' or value[1] != expected or value[3] is not False:
                    raise ValueError(f'{key}: actual native binding does not select {expected}')
        stacks[st] = stack
    if sorted(stacks.values()) != list(range(4)):
        raise ValueError('stack identity map is not a permutation of four stacks')
    a = [None]*32
    for st, stack in stacks.items():
        for group in range(8):
            a[8*stack+group] = (group << 2) | stack
    return dict(schema='opentallas.kv.native_die_cfg_contract.v1', abi=params,
                required_target10_words=32+params['NRST']+params['CAP']+19+1, stack_index=stacks,
                ectl_cfg_encoding='cfg_e[4:2]=group, cfg_s[1:0]=stack',
                ectl_a=a, ectl_b=[0]*32, ectl_c=[0]*32,
                reset_words=[0]*43, inactive_fields=inactive,
                hroot_to_ectl_cfg_bits_checked=160,
                capability='required compiler input; not inferred here',
                age_words='19 required current compiler words; not inferred here',
                qualification='source ABI/default census only, not boot or token qualification')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('ctl', type=Path);p.add_argument('cfg', type=Path);p.add_argument('fields', type=Path)
    p.add_argument('ectl', type=Path)
    p.add_argument('hroot', type=Path);p.add_argument('relays', type=Path);p.add_argument('cfg_sinks', type=Path)
    p.add_argument('--out', type=Path, required=True);a=p.parse_args()
    inputs=[a.ctl,a.cfg,a.fields,a.ectl,a.hroot,a.relays]
    r=derive(*(x.read_text() for x in inputs), json.loads(a.cfg_sinks.read_text()))
    inputs.append(a.cfg_sinks)
    r['sources']={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in inputs}
    a.out.write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps({k:r[k] for k in ('required_target10_words','stack_index','inactive_fields')}))


if __name__=='__main__':main()
