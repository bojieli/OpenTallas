#!/usr/bin/env python3
"""Prove emitted/re-read source equations against the transformed graph.

Independent from emission: exhaust every emitted Boolean source gate over its
<=3 symbolic inputs, verify every real FF type and D/C/R/E/Q binding after synthesis, and
verify complete macro/native-buffer/public-pin bindings. Combined with
check_graph.py this is a structural sequential equivalence proof, not a trace
sampling claim. It explicitly covers source-compiler mistakes in the emitter.
"""
import argparse,itertools,json,re
from pathlib import Path
GATES={'$_AND_','$_OR_','$_XOR_','$_NOT_','$_MUX_'}
FF={'$_DFF_P_','$_DFF_PN0_','$_DFF_PN1_','$_DFFE_PP_',
    '$_DFFE_PN0P_','$_DFFE_PN0N_','$_SDFF_PP0_','$_SDFF_PN0_'}

def check(expected,compiled,source,top='qfd_sys_face_control_safe'):
    e=expected['modules'][top];modules=compiled['modules']
    if top.endswith('__safe_core'):
        outer=top[:-len('__safe_core')]
        actual_type=modules[outer]['cells']['core']['type']
        m=modules[actual_type]
        assert actual_type==top or m.get('attributes',{}).get('hdlname')==top, 'wrong explicit core module'
    else:m=modules[top]
    def wire(b):
        return b if isinstance(b,str) else m['netnames']['n'+str(b)]['bits'][0]
    def conn(c):return {p:[wire(b) for b in bb] for p,bb in c['connections'].items()}
    def gate(typ,v):
        if typ=='$_NOT_':return 1-v['A'] if v['A'] in [0,1] else 'x'
        if typ=='$_AND_' and 0 in [v['A'],v['B']]:return 0
        if typ=='$_OR_' and 1 in [v['A'],v['B']]:return 1
        if typ=='$_MUX_':
            if v['S']=='x':return v['A'] if v['A']==v['B'] else 'x'
            return v['B'] if v['S'] else v['A']
        if 'x' in v.values():return 'x'
        if typ=='$_AND_':return v['A']&v['B']
        if typ=='$_OR_':return v['A']|v['B']
        if typ=='$_XOR_':return v['A']^v['B']
        if typ=='$_NOT_':return 1-v['A']
        if typ=='$_MUX_':return v['B'] if v['S'] else v['A']
        raise AssertionError('unsupported Boolean primitive '+typ)
    statements=dict(re.findall(r'assign n(\d+) = ([^;]+);',source))
    token=r"(?:n\d+|1'b[01xz])"
    def evaluate(expr,assignment):
        def atom(t):
            if t.startswith('n'):return assignment[int(t[1:])]
            return int(t[-1]) if t[-1] in '01' else 'x'
        if re.fullmatch(token,expr):return atom(expr)
        if re.fullmatch('~'+token,expr):return gate('$_NOT_',{'A':atom(expr[1:])})
        mm=re.fullmatch('('+token+')([&|^])('+token+')',expr)
        if mm:return gate({'&':'$_AND_','|':'$_OR_','^':'$_XOR_'}[mm[2]],{'A':atom(mm[1]),'B':atom(mm[3])})
        mm=re.fullmatch('('+token+')\\?('+token+'):('+token+')',expr)
        assert mm,'unsupported emitted expression '+expr
        return gate('$_MUX_',{'S':atom(mm[1]),'B':atom(mm[2]),'A':atom(mm[3])})
    counts={'boolean_equations':0,'ff_equations':0,'macro_instances':0,'native_buffers':0,'public_pins':0}
    for i,(name,c) in enumerate(sorted(e['cells'].items())):
        typ=c['type'];wanted=conn(c)
        if typ in GATES:
            if 'sysface_safe_gate' in source:
                actual=m['cells']['g'+str(i)]; sub=modules[actual['type']]
                assert actual['connections']=={p:wanted.get(p,['0']) for p in ['A','B','S','Y']}, 'kept gate pin changed: '+name
                # Exhaust the actual re-read primitive network for every 0/1 assignment.
                pins={p:(pp['bits'] if isinstance(pp,dict) else pp)[0] for p,pp in sub['ports'].items()}
                for values in itertools.product([0,1],repeat=3):
                    env={pins[p]:v for p,v in zip(['A','B','S'],values)}
                    env.update({'0':0,'1':1,'x':'x','z':'x'})
                    todo=list(sub['cells'].values())
                    while todo:
                        ready=[x for x in todo if x['type'] in GATES and all(b in env for p,bb in x['connections'].items() if p!='Y' for b in bb)]
                        assert ready,'unproved or cyclic kept gate: '+name
                        for x in ready:
                            vv={p:env[bb[0]] for p,bb in x['connections'].items() if p!='Y'}
                            env[x['connections']['Y'][0]]=gate(x['type'],vv);todo.remove(x)
                    assert env[pins['Y']]==gate(typ,dict(zip(['A','B','S'],values))), 'native helper equation '+name
                counts['boolean_equations']+=1
                continue
            # Prove source expressions before synthesis's legitimate don't-care
            # optimization. Compiler-generated unused mux arms may become X;
            # those are not grounds for masking a meaningful pin or FF check.
            inputs={p:bb[0] for p,bb in c['connections'].items() if p!='Y'}
            symbols=sorted({b for b in inputs.values() if isinstance(b,int)})
            assert len(symbols)<=3
            for values in itertools.product([0,1],repeat=len(symbols)):
                assignment=dict(zip(symbols,values));v={p:(int(b) if b in ['0','1'] else 'x') if isinstance(b,str) else assignment[b] for p,b in inputs.items()}
                assert evaluate(statements[str(c['connections']['Y'][0])],assignment)==gate(typ,v), 'Boolean equation '+name
            counts['boolean_equations']+=1
        elif typ in FF:
            actual=m['cells']['f'+str(i)];sub=modules[actual['type']]
            primitive=[x for x in sub['cells'].values() if x['type'] in FF]
            assert len(primitive)==1,'extra/missing state in kept FF helper'
            primitive=primitive[0];assert primitive['type']==typ,'FF reset/enable kind changed: '+name
            aliases={b:actual['connections'][p][k] for p,v in sub['ports'].items() for k,b in enumerate(v['bits'])}
            result={p:[b if isinstance(b,str) else aliases[b] for b in bb] for p,bb in primitive['connections'].items()}
            assert result==wanted,'emitted D/clock/reset/enable/Q changed: '+name
            counts['ff_equations']+=1
        else:
            isbuf=typ=='BUFx2_ASAP7_75t_R';actual=m['cells'][('b' if isbuf else 'm')+str(i)]
            assert actual['type']==typ and actual['connections']==wanted,'macro/native binding changed: '+name
            counts['native_buffers' if isbuf else 'macro_instances']+=1
    for name,p in e['ports'].items():
        assert m['ports'][name]['direction']==p['direction']
        assert m['ports'][name]['bits']==[wire(b) for b in p['bits']], 'public pin changed: '+name
        counts['public_pins']+=len(p['bits'])
    counts['emitted_equations']='PASS'
    return counts

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--top',default='qfd_sys_face_control_safe');ap.add_argument('expected');ap.add_argument('compiled');ap.add_argument('--source',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    out=check(json.loads(Path(a.expected).read_text()),json.loads(Path(a.compiled).read_text()),Path(a.source).read_text(),top=a.top)
    Path(a.out).write_text(json.dumps(out,sort_keys=True,indent=2)+'\n');print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
