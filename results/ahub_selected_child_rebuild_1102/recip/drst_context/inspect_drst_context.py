#!/usr/bin/env python3
"""Passive, exact artifact check. No frontend, synthesis or functional solver."""
from pathlib import Path
import copy, hashlib, json, re
R=Path(__file__).resolve().parent
SHA='1d079d78fe5591017937ae0ab20c5ca3997fae97571b9cb69e399b4029776dcc'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(s):
    out={}
    for m in re.finditer(r'^module (\S+)\n(.*?)^end\s*$',s,re.M|re.S):
        body=m[2]
        params=dict(re.findall(r'^  parameter \\(\w+)\s+([^\n]+)',body,re.M))
        cells=[]
        for c in re.finditer(r'^  cell (\S+) (\S+)\n(.*?)^  end\s*$',body,re.M|re.S):
            cells.append(dict(type=c[1],name=c[2],body=c[3],params=dict(re.findall(r'^    parameter \\(\w+)\s+([^\n]+)',c[3],re.M))))
        out[m[1]]=dict(params=params,cells=cells,body=body)
    return out
def check(mods):
    reached=[]; leaves=set(); active=set()
    def walk(t,path):
        assert t in mods, ('unresolved module',t)
        assert t not in active, ('recursive module',t)
        active.add(t); m=mods[t]
        for c in m['cells']:
            typ=c['type']; p=path+'.'+c['name'].lstrip('\\')
            if typ in mods:
                if 'ot_hdc_fp32_add_lat' in typ or 'ot_hdc_fp32_mul_lat' in typ:
                    assert not c['params'], ('unresolved caller override',p)
                    assert mods[typ]['params'].get('DRST')=='1', ('DRST not resolved to 1',p)
                    reached.append(dict(instance=p,type=typ,resolved_parameters=mods[typ]['params'],caller_parameters=c['params']))
                walk(typ,p)
            else:
                assert typ.startswith('$') and not typ.startswith('$paramod'), ('unresolved module',typ)
                leaves.add(typ)
        active.remove(t)
    walk('\\ot_qkh_recip_leaf','ot_qkh_recip_leaf')
    add=[x for x in reached if 'add_lat' in x['type']]
    mul=[x for x in reached if 'mul_lat' in x['type']]
    assert len(add)==3 and len(mul)==6, (len(add),len(mul))
    for t in {x['type'] for x in add}:
        cc=[c for c in mods[t]['cells'] if c['name']=='\\u_cc']
        assert len(cc)==1
        assert re.search(r'connect \\d \{ \\s2_v \\s2_byp \\s2_zero \\s2_sign \\s2_err \\s2_code',cc[0]['body'])
    return reached,sorted(leaves)
def normalize(s):
    s=re.sub(r'/\*.*?\*/','',s,flags=re.S)
    return re.sub(r'\s+','',re.sub(r'//[^\n]*','',s))
def main():
    p=R/'1_1_yosys_canonicalize.rtlil'; assert digest(p)==SHA
    mods=parse(p.read_text()); reached,primitives=check(mods)
    # Boundary controls of this receipt parser, not RTL mutants or EQ proofs.
    controls={}
    add=next(t for t in mods if 'ot_hdc_fp32_add_lat' in t)
    for label,value in [('DRST0','0'),('missing_DRST',None)]:
        bad=copy.deepcopy(mods)
        if value is None: bad[add]['params'].pop('DRST')
        else: bad[add]['params']['DRST']=value
        try: check(bad)
        except AssertionError: controls[label]='REJECTED'
        else: raise AssertionError(label)
    old=R.parent/'recorded_sources/rtl/hdc/ot_hdc_fp32_add_lat.sv'; new=R/'Q6_ot_hdc_fp32_add_lat.sv'
    expected=json.loads((R.parent/'Q6_LOGIC_COMPARISON.json').read_text())['common']['ot_hdc_fp32_add_lat.sv']
    assert digest(old)==expected['selected_old'] and digest(new)==expected['Q6_native_source']
    line="wire [1:0] s2_err_c = DRST ? s2_err : {1'b0, s2_err[0]};"
    src=new.read_text(); assert src.count(line)==1
    stripped=re.sub(r'//[^\n]*','',src)
    assert len(re.findall(r'\bs2_err_c\b',stripped))==2
    reduced=re.sub(r'\bs2_err_c\b','s2_err',src.replace(line,''))
    assert normalize(old.read_text())==normalize(reduced)
    comparison=json.loads((R.parent/'Q6_LOGIC_COMPARISON.json').read_text())
    assert not comparison['Q6_only'] and not comparison['selected_old_only']
    assert sum(x['byte_equal'] for x in comparison['common'].values())==8 and len(comparison['common'])==9
    result=dict(status='PASS_PASSIVE_CURRENT_ELABORATION_CONTEXT',scope='Actual Q6/native216 context only; original published archive compiler context UNKNOWN',canonical_sha256=SHA,root='ot_qkh_recip_leaf',defines='-DSYNTHESIS',reached=reached,primitive_types=primitives,controls=controls,other_sources_byte_equal=8,source_hashes=dict(old=digest(old),Q6=digest(new)),DRST1_exact_active_source_equal=True,native_u_cc_uses_s2_err=True,normal_EQ_or_old_archive_identity_claim=False)
    (R/'CONTEXT_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','controls','DRST1_exact_active_source_equal','normal_EQ_or_old_archive_identity_claim']}))
if __name__=='__main__': main()
