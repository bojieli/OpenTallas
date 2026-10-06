#!/usr/bin/env python3
"""Enroll the already measured controller interface without repeating JSON extraction."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def interface(text):
    match=re.search(r'\bmodule\s+ot_qwen_rom_core\s*\((.*?)\);',text,re.S)
    if not match:
        raise ValueError('missing emitted controller module')
    names=[n.strip().removeprefix('\\') for n in match[1].split(',')]
    declarations={}
    pattern=r'(?m)^\s*(input|output|inout)\s+(\[[^]]+\]\s+)?(\\?[^\s;]+)\s*;'
    for m in re.finditer(pattern,text):
        name=m[3].removeprefix('\\')
        if name in names:
            declarations[name]=(m[1],(m[2] or '').strip())
    if set(names)!=set(declarations):
        raise ValueError('incomplete port declarations')
    return match,names,declarations


def enroll(text, retained):
    match,names,declarations=interface(text)
    _,kept,target=interface(retained)
    if not set(kept)<=set(names):
        raise ValueError('retained interface port missing in successor')
    if {n:declarations[n] for n in kept}!=target:
        raise ValueError('retained port direction or width changed')
    removed=set(names)-set(kept)
    # Reuse spelling from the emitted header, including escape termination.
    spelling={n.strip().removeprefix('\\'):n.strip() for n in match[1].split(',')}
    identifiers=[spelling[n]+(' ' if spelling[n].startswith('\\') else '') for n in kept]
    text=text[:match.start(1)]+', '.join(identifiers)+text[match.end(1):]
    for name in removed:
        ident='\\'+name if '.' in name else name
        escaped=re.escape(ident)
        # Yosys emits a wire/reg declaration as well as each port declaration.
        if not re.search(r'(?m)^\s*(?:wire|reg)\s+(?:\[[^]]+\]\s+)?'+escaped+r'\s*;',text):
            raise ValueError(f'cannot demote port without retained net declaration: {name}')
        text,count=re.subn(r'(?m)^\s*(?:input|output|inout)\s+(?:\[[^]]+\]\s+)?'+escaped+r'\s*;\n','',text)
        if count!=1:
            raise ValueError(f'port declaration not unique: {name}')
    if interface(text)[2]!=target:
        raise ValueError('successor interface mismatch after enrollment')
    return text,removed


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--retained',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    raw=a.input.read_text();old=a.retained.read_text();text,removed=enroll(raw,old)
    a.out.write_text(text)
    a.report.write_text(json.dumps({'schema':'qwen.rom.controller_interface_enrollment.v1',
        'retained_interface_sha256':hashlib.sha256(old.encode()).hexdigest(),
        'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),
        'output_sha256':hashlib.sha256(text.encode()).hexdigest(),
        'port_directions_widths_names_equal':True,'removed_ports':sorted(removed),
        'repeat_JSON_or_cell_graph_proof':False,'clock_exceptions_added':False},indent=2)+'\n')
