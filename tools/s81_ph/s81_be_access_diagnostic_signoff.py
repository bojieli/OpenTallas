#!/usr/bin/env python3
"""Diagnostic-only BE actualcap/AP/corner verdict; never updates CLOSED views."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import child_lint as C

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    run=a.run.resolve();access=run/'access_candidate';access.mkdir(exist_ok=True)
    raw=run/'view/dsfd_vm_be_sl.lef';clean=access/'dsfd_vm_be_sl.lef'
    with (access/'abstract_postprocess.log').open('w') as log:
        subprocess.run([sys.executable,str(ROOT/'tools/hier_contract/abstract_pin_stub.py'),str(raw),str(clean)],stdout=log,stderr=subprocess.STDOUT,check=True)
    lint=C.lint(str(clean),libs=str(run/'view'),cap='M7',strict_pockets=True)
    (access/'child_lint_M7.json').write_text(json.dumps(lint,indent=2)+'\n')
    target=ROOT/'results/arch/s81_be_pinface_successor_1014/selected_Efaces_slot48/target_contacts_unrouted.lef'
    expected=C.parse_lef(target.read_text());actual=C.parse_lef(raw.read_text());missing=[]
    expected_ids={n for n,p in expected['pins'].items() if p['use']=='SIGNAL'}
    actual_ids={n for n,p in actual['pins'].items() if p['use']=='SIGNAL'}
    for n in sorted(expected_ids):
        for rect in expected['pins'][n]['rects']:
            if not any(r[0]==rect[0] and all(abs(x-y)<=.001 for x,y in zip(r[1:],rect[1:])) for r in actual['pins'].get(n,{}).get('rects',[])):
                missing.append(dict(pin=n,required_contact=rect))
    contact_match=bool(expected_ids==actual_ids and not missing)
    (access/'actual_contact_matching.json').write_text(json.dumps(dict(pass_=contact_match,expected=len(expected_ids),actual=len(actual_ids),missing_contacts=missing),indent=2)+'\n')
    # Readonly reference export raw and isolated clean candidate remain separate.
    subprocess.run([sys.executable,str(ROOT/'tools/s81_ph/s81_be_pin_access_probe.py'),str(clean),str(access/'AP_M7'),'--aligned-tracks'],check=False)
    AP=json.loads((access/'AP_M7/record.json').read_text())
    subprocess.run([sys.executable,str(ROOT/'tools/s81_ph/s81_be_pin_access_probe.py'),str(clean),str(access/'AP_global_parent'),'--parent-be-slots','--be-x-shift=-.048'],check=False)
    parent_AP=json.loads((access/'AP_global_parent/record.json').read_text())
    sta=json.loads((run/'corner_sta.json').read_text());physical=json.loads((run/'physical.json').read_text())
    ss=(sta.get('setup_ss') or {}).get('worst_slack_ps');ff=(sta.get('hold_ff') or {}).get('worst_slack_ps')
    drcs=[]
    def find_drc(obj):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if 'drc' in k.lower() and isinstance(v,(int,float)) and not isinstance(v,bool):drcs.append(v)
                find_drc(v)
        elif isinstance(obj,list):
            for v in obj:find_drc(v)
    find_drc(physical);drc=max(drcs) if drcs else None
    metrics=dict(ss_ps=ss,ff_ps=ff,drc=drc)
    qualified=bool(ss is not None and ff is not None and drc is not None and ss>=15 and ff>=15 and drc==0 and contact_match and lint['verdict']=='PASS' and AP['pass_'] and parent_AP['pass_'])
    record=dict(schema='opentallas.be_access_diagnostic_verdict.v1',status='DIAGNOSTIC_PASS' if qualified else 'DIAGNOSTIC_FAIL',metrics=metrics,
        actual_cap='M7',actual_contact_match=contact_match,actual_child_lint=lint['verdict'],actual_AP_pass=AP['pass_'],actual_requested_global_slot_AP_pass=parent_AP['pass_'],global_clocks_and_reset_refs_bound=False,
        slot_allocated=False,M6_eligibility_waived=False,old_CLOSED_replaced=False,diagnostic_checks_pass=qualified,adopted=False)
    a.out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
    # A complete negative diagnostic reaches the loop's verdict checks, which
    # reject it. Missing artifacts/execution failures remain real stage errors.
    return 0
if __name__=='__main__':raise SystemExit(main())
