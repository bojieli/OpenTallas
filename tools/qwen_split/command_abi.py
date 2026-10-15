#!/usr/bin/env python3
"""Extract the REAL cmd packing from its production SystemVerilog source."""
import ast
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'rtl/physical/ot_qfd_tt_ctlm_split.sv'


def _integer(expression):
    node = ast.parse(expression, mode='eval').body
    def ev(n):
        if isinstance(n,ast.Constant) and isinstance(n.value,int):return n.value
        if isinstance(n,ast.BinOp):
            a,b=ev(n.left),ev(n.right)
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Mult):return a*b
        raise ValueError('nonconstant production port width')
    return ev(node)


def me_fields():
    text=SOURCE.read_text()
    concat=re.search(r'assign cmd = \{([^}]+)\};',text).group(1)
    names=[n.strip() for n in concat.split(',')][::-1]
    declarations={}
    for bounds,variables in re.findall(r'wire\s*(?:\[([^\]]+)\])?\s+([^;]+);',text):
        if not re.fullmatch(r'\s*\w+(?:\s*,\s*\w+)*\s*',variables):continue
        declared=[name.strip() for name in variables.split(',')]
        if not set(declared)&set(names):continue
        width=1
        if bounds:
            high,low=bounds.split(':');width=_integer(high)-_integer(low)+1
        for name in declared:declarations[name]=width
    rows=[];offset=0
    for signal in names:
        name='go' if signal=='u_me_go' else 'me_'+signal.removeprefix('u_me_i_')
        width=declarations[signal]
        rows.append(dict(name=name,rtl_signal=signal,offset=offset,width=width))
        offset+=width
    if offset!=380:raise ValueError(f'actual production command width changed: {offset}')
    return rows


def pack_me(resolved_fields,go=1):
    value=0
    for row in me_fields():
        v=go if row['name']=='go' else resolved_fields[row['name']]
        if not 0<=v<1<<row['width']:raise ValueError(row['name']+' exceeds real RTL width')
        value|=v<<row['offset']
    return value


def unpack_me(value):
    return {r['name']:(value>>r['offset'])&((1<<r['width'])-1) for r in me_fields()}


def native_template(program,pc=11):
    import sys
    sys.path.insert(0,str(ROOT/'tools'))
    import hdc_qwen_fullshape_isa_w12 as ISA
    f=ISA.decode_instruction(int(program.decode().split()[pc],16))
    if f['unit']!=1 or not f['me_wsrc'] or any(v for k,v in f.items() if k.startswith('me_d_')):
        raise ValueError('native template needs actual WSRC1 instruction with no unresolved DYN selector')
    value=pack_me(f)
    fields=unpack_me(value)
    if fields['me_xbase']!=f['me_xbase'] or fields['me_obase']!=f['me_obase']:
        raise AssertionError('source ABI packing drift')
    return dict(schema='opentallas.qwen-native380-template.v1',program_sha256=hashlib.sha256(program).hexdigest(),
                source=str(SOURCE.relative_to(ROOT)),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                pc=pc,command_hex=f'{value:095x}',bits=380,fields=fields,layout=me_fields(),
                context_variable_command_bits=[],context='epoch16/stage6/token18/pos13 from real host control, separate from descriptor')
