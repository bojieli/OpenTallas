#!/usr/bin/env python3
"""Check actual SVC kit clock consumers and unchanged data/reset/state text."""
import argparse,json,re,sys
from pathlib import Path

def body_span(text,inst):
    pat=re.compile(r'^\s*\w+(?:\s*#\([^\n]*\))?\s+'+re.escape(inst)+r'\s*\(',re.M)
    hits=list(pat.finditer(text));assert len(hits)==1,(inst,'instance count',len(hits))
    a=hits[0].end();i=a;depth=1
    while depth:
        depth+=(text[i]=='(')-(text[i]==')');i+=1
    return a,i-1

def connection(text,inst,pin):
    a,b=body_span(text,inst);pat=re.compile(r'(\.'+re.escape(pin)+r'\s*\()([^()]+)(\))')
    hits=list(pat.finditer(text[a:b]));assert len(hits)==1,(inst,pin,'pin count')
    return a,b,pat,hits[0]

def verify(original,actual,bmod,newmod,rows,expected):
    assert len(rows)==len(expected)==64
    assert {(r['port'],r['instance'],r['pin']) for r in rows}==expected
    text=re.sub(r'\b(module|endmodule\s*:)\s+'+re.escape(newmod)+r'\b',lambda m:m.group(1)+' '+bmod,actual)
    ports={r['port'] for r in rows};removed=[];lines=[]
    for line in text.splitlines(keepends=True):
        m=re.match(r'^\s*input wire (\w+),\s*// planned early-core clock\s*$',line)
        if m:
            assert m.group(1) in ports;removed.append(m.group(1))
        else:lines.append(line)
    assert set(removed)==ports and len(removed)==64
    text=''.join(lines)
    for r in rows:
        inst,pin,port=r['instance'],r['pin'],r['port']
        a,b,pat,m=connection(text,inst,pin)
        assert m.group(2).strip()==port,(port,inst,'wrong actual clock consumer',m.group(2))
        _,_,_,old=connection(original,inst,pin)
        assert old.group(2).strip()==r['previous_net']
        body=pat.sub(lambda z:z.group(1)+r['previous_net']+z.group(3),text[a:b],count=1)
        text=text[:a]+body+text[b:]
    assert text==original,'non-clock source body change'

def ports(text):
    return [(d,n,int(w)+1 if w else 1) for d,w,n in re.findall(r'^\s*(input|output)\s+wire\s*(?:\[(\d+):0\]\s*)?(\w+)\s*[,)]',text,re.M)]

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--root',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
    sys.path.insert(0,str(a.source/'tools/die_plan'));import schema as S,gen_phys as G
    plan=S.Plan(S.load(a.plan),a.plan);result=[]
    for tn in ['svc_hi_dsdv_svc_rs__t1','svc_lo_dsdv_svc_rs__t7']:
        k=a.root/'canaries'/tn/'rtl';meta=json.load(open(k/'kit_rtl.json'));rs=json.load(open(k/'kit_core_clocks.json'))['rows']
        b=Path(meta['bind_out']);br=json.load(open(b/'bind_report.json'));bmod=br['types'][meta['bound_type']]['module'];newmod=meta['bound_module']
        original=(b/'rtl'/f'{bmod}.sv').read_text();actual=(k/f'{newmod}.sv').read_text()
        expected={(port,inst.removeprefix('u_bound.'),pin) for port,inst,pin,_,_ in G.core_tap_rows(plan,tn)}
        verify(original,actual,bmod,newmod,rs,expected)
        wrapper=(k/f'{meta["plan_module"]}.sv').read_text();baseline=(a.baseline/tn/'rtl'/f'{meta["plan_module"]}.sv').read_text()
        assert ports(wrapper)==ports(baseline),'public module clock/data ABI changed'
        mutant=actual.replace('.clk(clk_c0)','.clk(clk_c1)',1);assert mutant!=actual
        try:verify(original,mutant,bmod,newmod,rs,expected)
        except AssertionError:pass
        else:raise AssertionError('wrong-clock mutant escaped')
        result.append(dict(type=tn,clock_consumers=64,public_ports=len(ports(wrapper)),public_abi='UNCHANGED',data_reset_state_text='EXACT after undoing only declared clock forwarding',wrong_clock_mutant='CAUGHT'))
    out=dict(verdict='PASS',rows=result,scope='Declared early-core clock ports now drive the exact named bound leaf pins. No state or cycles added; plan clock schedule and public pins unchanged.')
    (a.root/'clock_alias_proof.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(out))
