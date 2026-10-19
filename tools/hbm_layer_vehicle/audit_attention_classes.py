#!/usr/bin/env python3
"""Class property of every compiler-emitted magic word; source proof and fixture census."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import att_images as A
from attention_mode_contract import analyse


def source_proof(path, function, hold=False):
    raw = path.read_bytes()
    tree = ast.parse(raw)
    fun = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function)
    assignments = [n for n in ast.walk(fun) if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mode' for t in n.targets)]
    assert len(assignments) == 1
    expr = assignments[0].value
    assert not any(isinstance(n, (ast.Call,ast.Attribute,ast.Subscript)) for n in ast.walk(expr))
    setters, fills = [], []
    for n in ast.walk(fun):
        if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Attribute):
            continue
        base = n.func.value
        if isinstance(base,ast.Name) and base.id=='cal' and n.func.attr=='set':
            required = any(k.arg=='mode' and isinstance(k.value,ast.Name) and k.value.id=='mode' for k in n.keywords)
            if hold:
                required = any(k.arg is None and isinstance(k.value,ast.Name) and k.value.id=='hold' for k in n.keywords)
            assert required, f'word setter line{n.lineno} lacks constant mode'
            setters.append(n.lineno)
        if isinstance(base,ast.Name) and base.id=='d' and n.func.attr=='setdefault' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='mode':
            assert isinstance(n.args[1],ast.Name) and n.args[1].id=='mode'
            fills.append(n.lineno)
        if isinstance(base,ast.Name) and base.id=='hold':
            raise AssertionError('hold dict mutated')
    assert setters and fills
    if hold:
        hs=[n for n in ast.walk(fun) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='hold' for t in n.targets)]
        assert len(hs)==1 and isinstance(hs[0].value,ast.Call)
        assert any(k.arg=='mode' and isinstance(k.value,ast.Name) and k.value.id=='mode' for k in hs[0].value.keywords)
    modes={}
    for qk in (True,False):
        for kv4 in ((False,True) if not hold else (False,)):
            mode=eval(compile(ast.Expression(expr),str(path),'eval'),{'__builtins__':{}},{'qk':qk,'kv4':kv4})
            assert mode>>2==1 and mode!=3
            modes[f'{"qk" if qk else "pv"}_kv{4 if kv4 else 8}']=mode
    return dict(source=str(path),sha256=hashlib.sha256(raw).hexdigest(),function=function,
                mode_expression=ast.unparse(expr),variant_modes=modes,
                all_cal_set_lines=setters,fill_lines=fills,
                property='every field-bearing command is A2 magic with constant per-call mode and attention class1',
                scope='universal source property, independent of operand values, row count and result calibration; not an arithmetic fixture replay')


def run(a):
    root=Path(__file__).resolve().parents[2]
    out=dict(source_proofs=[source_proof(root/'tools/hbm_sm_attention/sm_elem_bench.py','compile_op'),
                           source_proof(root/'tools/hbm_layer_vehicle/qwen_att_unit.py','compile_q',True)],fixtures=[])
    front=root/'rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_front_static.sv'
    if front.exists():
        text=front.read_text()
        assert 'wire attention=mode[2];' in text and 'if(!attention && mode==3)schedule_fault<=1;' in text
        out['actual_frontend']=dict(path=str(front),sha256=hashlib.sha256(front.read_bytes()).hexdigest(),
                                    classification='mode[2]',invalid_mode=3,runtime_invalid_mode_witness='separate full-service run required')
    first_rec=None
    if a.kv:
        for layer in a.layers.split(','):
            rec,src=A.load_ds(Path(a.kv),int(layer))
            if first_rec is None:first_rec=rec
            counts=[]
            for sub in (0,8,32):
                ops,_=A.plan_d4g(rec,sub=sub)
                for op in ops:
                    cal,exp=A.E.compile_op(rec,op[:5],dict(A.E.DEFAULT_LAT),op[1]=='pv')
                    words=[A.E.cmd_word(**f) for f in cal.cyc]
                    proof=analyse(words)
                    assert proof['extra_descriptors']==0 and all(int(m)>>2==1 for m in proof['mode_counts'])
                    counts.append(dict(name=op[0],subrun_rows=sub,word_count=proof['words'],magic_words=proof['magic_words'],mode_counts=proof['mode_counts'],literal_sha256=proof['literal_sha256']))
            out['fixtures'].append(dict(source=src,programmes=counts,total_programmes=len(counts),total_magic_words=sum(x['magic_words'] for x in counts)))
    if a.compat_receipt:
        import attention_prel_svg as P
        import smb_unit as S
        assert first_rec is not None
        directory=Path(a.compat_dir);directory.mkdir(parents=True,exist_ok=True)
        S.write_events(P.compile_attention(first_rec),directory)
        got={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.hex')}
        want=json.loads(Path(a.compat_receipt).read_text())['event_sha256']
        assert got==want, 'default event bytes changed'
        out['default_compatibility']=dict(exact=True,event_sha256=got,receipt=str(a.compat_receipt))
        plain=P.compile_attention(first_rec)
        mixed=P.compile_attention(first_rec,mixed_context=True)
        assert plain['xw']==mixed['xw'] and plain['mem']==mixed['mem'] and plain['ids']==mixed['ids'] and plain['n_end']==mixed['n_end']
        diffs=0
        for (t,w),(mt,mw) in zip(plain['ing'],mixed['ing']):
            assert t==mt and ((w^mw)&~(7<<(41+195)))==0
            diffs+=w!=mw
        out['mixed_metadata_only']=dict(exact=True,changed_descriptor_rows=diffs,
            modes=[b['descriptor_mode'] for b in mixed['blocks']],
            note='only existing mode195:197 descriptor bits change; literal programme/HBM/XW/timing unchanged')
        out['native_api_profiles']=[]
        for ce,ca,de in ((2,0,0),(4,2,2)):
            native=P.compile_attention(first_rec,native_padding=19,command_extra=ce,calendar_extra=ca,programme_done_extra=de)
            assert native['mem']==plain['mem']
            for i,(old,new) in enumerate(zip(plain['blocks'],native['blocks'])):
                assert new['go_at']-old['go_at']==19+i*ce
                assert new['first_abs']-old['first_abs']==19+(i+1)*ce
                assert new['first_read_pin_abs']-old['first_read_pin_abs']==19+i*ce+ca
                assert new['cal'].cyc==old['cal'].cyc
            out['native_api_profiles'].append(dict(timing=native['budget']['timing'],
                go_to_command=7+ce,go_to_read_pin=6+ca,run_edges=native['budget']['run_edges'],
                status='compiler/API proof only; actual native hardware not selected by this audit'))
    w=lambda mode:(0xa2<<184)|(mode<<181)
    out['legal_mixed_mode_only_split']=analyse([w(0),w(4),w(0)],block_lines=64,calendar_extra=2,command_only_extra=2)
    out['post_mrel_generic_positive']=analyse([w(0),w(0)],descriptor_mode=4,mrel=True)
    out['pass']=True
    Path(a.out).write_text(json.dumps(out,indent=2)+'\n')
    print('ATTENTION_CLASS_AUDIT_PASS fixtures='+str(len(out['fixtures'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kv');p.add_argument('--layers',default='2,14');p.add_argument('--out',required=True)
    p.add_argument('--compat-receipt');p.add_argument('--compat-dir')
    run(p.parse_args())
