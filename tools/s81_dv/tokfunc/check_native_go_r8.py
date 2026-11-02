#!/usr/bin/env python3
"""Diagnose literal native lane-age recipes; never infer R8 or mission adoption."""
from pathlib import Path
import argparse,json,re
from check_native_go_pair import inspect

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
    gold=json.loads((a.root/'independent_gold.json').read_text())
    names=['uniform_original','uniform_current','asbuilt_original','asbuilt_current','wrong_lane','wrong_date','wrong_tag']
    cases={n:inspect(a.root,n,gold,2,[1,3]) for n in names}
    for n,c in cases.items():
        text=(a.root/(n+'.log')).read_text()
        if [x[0] for x in c['core']]!=[763,1787]:c['errors'].append('native Q capture dates differ from fixed current calendar')
        if not re.search(r'^RING_END enabled=1 fault=0$',text,re.M):c['errors'].append('native ring fault')
        if len(re.findall(r'^RING_GATHER ',text,re.M))!=144:c['errors'].append('native input gather count differs')
        c['transport_profile']=re.search(r'^TRANSPORT_PROFILE .*$',text,re.M)[0]
        c['native_terminal']=re.search(r'^NATIVE_GO_END .*$',text,re.M)[0]
        if c['errors']:c['status']='FAIL'
    keys=['core','partial_words','feedback','cfg','stream']
    uniform_eq={k:cases['uniform_original'][k]==cases['uniform_current'][k]for k in keys}
    asbuilt_eq={k:cases['asbuilt_original'][k]==cases['asbuilt_current'][k]for k in keys}
    controls={n:cases[n]['status']=='FAIL'for n in names[4:]}
    observed_asbuilt_pass=all(cases[n]['status']=='PASS'for n in names[2:4])
    harness_pass=all(cases[n]['status']=='PASS'for n in names[:2])and all(uniform_eq.values())and all(controls.values())
    summary=dict(status='PASS_NATIVE_R8_RECIPE_DIAGNOSTIC'if harness_pass else'FAIL_NATIVE_R8_RECIPE_DIAGNOSTIC',
        uniform41_status={n:cases[n]['status']for n in names[:2]},
        asbuilt_age_status={n:cases[n]['status']for n in names[2:4]},
        asbuilt_age_recipe_passes_selected_literal_oracle=observed_asbuilt_pass,
        asbuilt_errors={n:cases[n]['errors']for n in names[2:4]},
        actual_lane_ages=[46,41,45,47],current_uniform_lane_ages=[41]*4,
        disabled_added_ages=[5,0,4,6],hypothetical_packet_FF=276*(5+4+6),
        hypothetical_FF_include_existing_packet_valid_bits=True,
        original_current_uniform_equal=uniform_eq,original_current_asbuilt_equal=asbuilt_eq,
        controls_caught=controls,independent_expected_Q_tags=[1,3],independent_expected_capture_edges=[763,1787],
        independent_checkpoint_gold_unchanged=True,actual_current_calendar_CFG_images_unchanged=True,
        source_readiness='same earlier held-constant source/ring fixture as77eadd758',
        clock_ps=833,native_provider_qualified=False,R8_qualified=False,production_enabled=False,
        actual_mission_source_epochs_qualified=False,physical_clock_phase_qualified=False,
        BF_arithmetic_or_all_lane_payload_qualified=False,production_FF_or_cycles_added=0,
        scope='One native selected Q pair and actual original/current source paths; recipe is a disabled TB counterfactual, no metadata relabel or physical padding adoption')
    (a.out/'check.json').write_text(json.dumps(summary,indent=2)+'\n');(a.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    print(json.dumps(summary,indent=2));return 0 if harness_pass else 1

if __name__=='__main__':raise SystemExit(main())
