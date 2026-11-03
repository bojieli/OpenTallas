#!/usr/bin/env python3
"""Actual mixed broadcast history, with native CFG class filtering and checkpoint Q gold."""
from pathlib import Path
import argparse, hashlib, json, re
from check_native_go_pair import inspect

def main():
    p=argparse.ArgumentParser()
    for k in ('root','field','out'): p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args(); assert not a.out.exists(); a.out.mkdir(parents=True)
    programme=json.loads((a.root/'programme/programme.json').read_text())
    phases=programme['programmes']['old']['phases']
    assert [v['phase'] for v in phases]==[0,106,0]
    gold=json.loads((a.root/'independent_gold.json').read_text())
    cfgfiles=[a.field/'images'/f'u_f_0L01_c0_{b}.viamap.hex' for b in range(7)]
    cfg=[[int(v,16) for v in f.read_text().split()] for f in cfgfiles]
    def word(k):
        address=k//7
        return sum(((cfg[k%7][address//8]>>(8*b+address%8))&1)<<b for b in range(72))
    # Same physical native CW25/IL7 layout; no inferred class aliases.
    active=[any(word(v['phase']*25+8+s)&1 for s in range(8)) for v in phases]
    assert active==[True,False,True]
    # OPTAG=1 is independently source-pinned by the checkpoint-gold helper.
    # CFG7 increments tag on EVERY go_x, then filters go_e with act.
    tags=[(gold['first_operation_tag']+i)%4 for i,on in enumerate(active) if on]
    assert tags==[1,3]
    # Same source cut/phase0 as native boundary receipt: first actual direct capture763.
    # This anchor is measured; relative dates are independently fixed by this calendar.
    expected_edges=[763+v['launch']-phases[0]['launch'] for v,on in zip(phases,active) if on]
    names=['original_direct','current_direct','wrong_class','wrong_date','wrong_tag']
    cases={n:inspect(a.root,n,gold,sum(active),tags) for n in names}
    for n,c in cases.items():
        text=(a.root/(n+'.log')).read_text()
        broadcasts=[int(t) for t in re.findall(r'^XS_CONTROL (\d+) cfg=\d go=1$',text,re.M)]
        c['broadcast_edges']=broadcasts
        if len(broadcasts)!=3: c['errors'].append('not three actual XS broadcast GOs')
        if [v[0] for v in c['core']]!=expected_edges: c['errors'].append('Q capture count/date violates native class-filtered calendar')
        if 'native_ring_fixture' in programme:
            c['native_ring_terminal']=re.search(r'^RING_END enabled=1 fault=0$',text,re.M) is not None
            path=a.root/('wrong_class_programme' if n=='wrong_class' else 'programme')/('old' if n in ['original_direct','wrong_date'] else 'advance1')/'producer.txt'
            fragments=[(int(t),int(v,16))for t,k,v in (line.split()for line in path.read_text().splitlines())if int(k)==2]
            expected=[]
            for j in range(0,len(fragments),4):
                group=fragments[j:j+4]; assert len(group)==4
                assert [v>>276 for t,v in group]==[1,0,0,0]
                assert [t for t,v in group]==list(range(group[0][0],group[0][0]+4))
                beat=sum((v&((1<<276)-1))<<(276*i)for i,(t,v)in enumerate(group))
                assert beat&1 and (beat>>1)&7 in [1,2]
                expected.append((group[0][0]+6,((beat>>1)&7)-1,(beat>>13)&127,(beat>>21)&((1<<1024)-1)))
            actual=[(int(t),int(f),int(i),int(v,16))for t,f,i,v in re.findall(r'^RING_GATHER (\d+) family=(\d+) index=(\d+) data=([0-9a-f]+)$',text,re.M)]
            c['native_fragment_header_gather_exact']=actual==expected
            c['native_fragment_gather_beats']=len(actual)
            if not c['native_ring_terminal'] or actual!=expected:c['errors'].append('actual native rstop header/fragment/gather mismatch or fault')
        if c['errors']: c['status']='FAIL'
    eq={k:cases['original_direct'][k]==cases['current_direct'][k] for k in ['core','partial_words','feedback','cfg','stream']}
    controls={n:cases[n]['status']=='FAIL' for n in names[2:]}
    passed=all(cases[n]['status']=='PASS' for n in names[:2]) and all(eq.values()) and all(controls.values())
    report=dict(status='PASS_NATIVE_MIXED_BROADCAST_HISTORY' if passed else 'FAIL_NATIVE_MIXED_BROADCAST_HISTORY',
        actual_phases=[0,106,0],native_Q_class_active=active,broadcasts=3,Q_captures=2,
        expected_Q_operation_tags=tags,expected_Q_capture_edges=expected_edges,
        per_Q_only_counter_control_rejected=tags!=[1,2],
        original_status=cases['original_direct']['status'],current_status=cases['current_direct']['status'],
        original_errors=cases['original_direct']['errors'],current_errors=cases['current_direct']['errors'],
        original_current_exact=eq,controls_caught=controls,
        native_CFG_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in cfgfiles},
        first_capture_anchor='measured source-pinned same-cut phase0 boundary763; relative calendar dates independent',
        native_ring_input_checks={n:{k:cases[n].get(k)for k in ['native_ring_terminal','native_fragment_header_gather_exact','native_fragment_gather_beats']}for n in names},
        native_ring_fixture=programme.get('native_ring_fixture'),
        BF_arithmetic_or_operand_source_qualified=False,constant_checkpoint_Q_activation=True,
        fresh_operand_versions_qualified=False,native_provider_qualified=False,production_enabled=False,
        RTL_changes=0,added_FF=0,added_cycles=0,
        scope='Selected native Q pair sees actual BF-only broadcast without Q capture; no native BF arithmetic or mission-provider qualification')
    (a.out/'check.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    print(json.dumps(report,indent=2)); return 0 if passed else 1

if __name__=='__main__': raise SystemExit(main())
