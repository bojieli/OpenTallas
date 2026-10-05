#!/usr/bin/env python3
"""Source-bound ordinary-GPU elementwise calendars; no tensor evaluation."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PIN='609af8387'
PROGRAM='results/rtl/w19_hbm_tp96_program_oreduce.json'
NORM_PIN='5a55e676b'


def blob(rev,path):
    return subprocess.check_output(['git','show',f'{rev}:{path}'],cwd=ROOT)


def provider():
    """Reuse immutable instruction and RF/shared calendar functions verbatim."""
    ns={'Counter':Counter}
    for rev,path,names in [
        ('14c57fd85','tools/w19_gpu_simd_contract.py',{'instruction'}),
        (NORM_PIN,'tools/w19_gpu_norm_calendar.py',{'op','bf16_round','calendar','ARITY','CONSTANTS'})]:
        tree=ast.parse(blob(rev,path))
        selected=[]
        for n in tree.body:
            if isinstance(n,ast.FunctionDef) and n.name in names:selected.append(n)
            elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets):selected.append(n)
        exec(compile(ast.Module(body=selected,type_ignores=[]),path,'exec'),ns)
    ns['CONSTANTS']=ns['CONSTANTS']|{'@F32_POS_ZERO'}
    return ns


def moe_recipe(p):
    op=p['op'];recipe=[]
    for expert in range(7):
        recipe += [op('LOAD','b',shared=True,source=f'e{expert}.d[rank_local_row] BF16'),
                   op('WIDEN','v',['b']),
                   op('FADD','acc',['@F32_POS_ZERO' if expert==0 else 'acc','v'])]
    return recipe+p['bf16_round']('acc','bf16')+[op('STORE16',src=['bf16'],shared=True,byte_enable=True,source_bits='31:16')]


def build():
    p=provider();recipe=moe_recipe(p);raw=json.loads(blob(PIN,PROGRAM))
    ops=[o for layer in raw['layers'] for o in layer['ops'] if o.get('fn')=='moe_sum']
    if len(ops)!=40 or raw['tp']!=96:raise ValueError('unexpected MoE programme/TP')
    # Assert actual producer datatype and complete expert-slot coverage.
    for layer in raw['layers']:
        if layer['layer']=='head':continue
        producers=[o for o in layer['ops'] if o.get('out','').endswith('.d')]
        if [o['out'] for o in producers]!=[f'e{e}.d' for e in range(7)] or any(o['out_dtype']!='bf16' for o in producers):
            raise ValueError('MoE input datatype/order changed')
    rows=[5120*(r+1)//96-5120*r//96 for r in range(96)]
    paths=[(PIN,PROGRAM),(PIN,'tools/w19_hbm_tp96_isa.py'),
           (NORM_PIN,'tools/w19_gpu_norm_calendar.py'),('14c57fd85','tools/w19_gpu_simd_contract.py'),
           (PIN,'tools/hdc_golden.py'),(PIN,'tools/hdc_golden_v41.py')]
    return dict(schema='opentallas.w19.gpu-elementwise-calendar.v1',
        status='MODELED_LOCAL_INSTRUCTION_CALENDAR_NOT_RTL',
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        source_pins={path:dict(commit=rev,sha256=hashlib.sha256(blob(rev,path)).hexdigest()) for rev,path in paths},
        source_graph_binding=[dict(layer=o['layer'],op=o['id'],function='moe_sum') for o in ops],
        recipe=recipe,calendar=p['calendar'](recipe,2),clock_hz=900000000,
        rank_rows=rows,active_SM_per_rank=1,warps_per_active_SM=2,
        constants={'@F32_POS_ZERO':dict(bits='0x00000000',dtype='F32',readonly=True)},
        arithmetic='Golden f_moe_sum initializes +0 then seven ordered FADDs in routed-id order followed by shared slot; BF16 RNE only after sum. No tree reassociation.',
        staging=dict(input_bytes_per_rank_max=max(rows)*7*2,output_bytes_per_rank_max=max(rows)*2,
                     accumulator_RF_bits_per_rank_max=max(rows)*32,
                     shared_bytes_with4096control=max(rows)*8*2+4096,shared_capacity=65536),
        missing=['actual producer-to-consumer staging/finite port+bank conflicts',
            'refill/NoC/CDC/resultstage/drain costs','production opcode/RF exactness and contextual SS/FF'],
        other_elementwise_classes=['swiglu','router_act','route','argmax_local'],
        physical_admission=False,hardware_adopted=False,full_token_cycles=None)


if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(build(),indent=2)+'\n')
