#!/usr/bin/env python3
"""Per-pin ETM constraints for BE candidate pairs; unknown clocks stay unknown.

Uses the project's pinreg_audit Liberty parser and residual convention O-R and
S+R. Raw ETM arcs are real exported timing values. Without routed per-clock
boundary means, residuals remain explicit estimates; global clock/reset binding,
actual parent load/SPEF and selected-view eligibility still gate qualification.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pinreg_audit as P
AUDIT=ROOT/'results/arch/s81_be_view_audit_1014'
PLAN=ROOT/'results/arch/s81_be_native_mc_placement_1014/request.json'
BE_VIEW='physical/s81_ph_views/vm_master/routes/s81vm-besl4-c15e2bf6a-tc-rd-pd45/dsfd_vm_be_sl'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_views(manifest):
    views={};provenance={}
    for top,v in manifest.items():
        directory=ROOT/v['dir'];ins=None
        if v.get('insertion'):ins=json.loads((ROOT/v['insertion']).read_text())
        rows={}
        for corner in ['tt','ss','ff']:
            path=directory/f'{top}_{corner}.lib'
            if not path.exists():continue
            lib=P.parse_lib(path);refs=P.clock_refs(lib,ins,corner)
            rows[corner]=dict(metrics=P.pin_metrics(lib,refs),raw=P.pin_metrics(lib,{}),refs=refs)
            provenance[str(path.relative_to(ROOT))]=sha(path)
        views[top]=dict(corners=rows,metadata=v)
        if v.get('insertion'):provenance[v['insertion']]=sha(ROOT/v['insertion'])
    return views,provenance

def endpoint(e,corner,views):
    if not e:return dict(status='missing endpoint identity')
    top=e['master'];view=views.get(top)
    if not view:return dict(status='missing routed ETM',endpoint=e)
    data=view['corners'].get(corner)
    if not data:return dict(status='missing corner ETM',endpoint=e)
    pin=data['metrics'].get(e['pin']);raw=data['raw'].get(e['pin'])
    if not pin:return dict(status='missing pin ETM',endpoint=e)
    clocks={clock:data['refs'].get(clock) for clock in pin['clk']}
    measured=bool(clocks) and all(r and r['src']=='insertion.json boundary mean' for r in clocks.values())
    return dict(status='measured local reference' if measured else 'local reference estimate',endpoint=e,
                residual=pin,raw=raw,clock_references=clocks,
                exported_period_ps={clock:view['metadata'].get('period_ps',{}).get(clock) for clock in clocks},
                exported_period_scope=view['metadata'].get('period_scope'),view_eligible=view['metadata'].get('eligible',False),
                globally_bound=False)

def build(plan,manifest):
    views,provenance=load_views(manifest);rows=[]
    for pair in plan['pairs']:
        row=dict(net=pair['net'],kind=pair['kind'],length_um=pair['routed_length_um'],source=pair['source_endpoint'],destination=pair['destination_endpoint'],qualified=False)
        launch_domain=row['source'].get('logical_clock')
        capture_domain=row['destination'].get('logical_clock')
        if row['destination']['master']=='dsfd_vm_be_sl':capture_domain='cks' if row['destination']['pin'].startswith('rns_in') else 'ck'
        row['RTL_clock_domains']=dict(launch=launch_domain,capture=capture_domain,source='actualhardparentRTLconnections; candidateBGRroot remainsprovisional',physically_bound=False)
        row['corners']={}
        for corner in ['tt','ss']:
            a=endpoint(row['source'],corner,views);b=endpoint(row['destination'],corner,views)
            w=P.WIRE[corner];wire=w*row['length_um']
            budgets=dict(status='OPEN',wire_model_ps_per_um=w,wire_ps=round(wire,6),launch=a,capture=b)
            periods=[x for x in b.get('exported_period_ps',{}).values() if x is not None]
            # Only exported local period is known here; it cannot bind the
            # actual parent clock or establish a launch/capture relationship.
            period=min(periods) if periods else None
            residual=b.get('residual',{}).get('inp')
            launch=a.get('residual',{}).get('out')
            if period is not None and residual is not None:
                scenarios={}
                for skew in [90,150]:
                    available=period-60-skew
                    scenarios[str(skew)]=dict(exported_local_period_ps=period,available_ps=available,
                         required_launch_residual_max_ps=round(available-wire-residual,6),
                         conditional_setup_margin_ps=round(available-wire-residual-launch,6) if launch is not None else None,
                         conditional_max_length_um=round((available-residual-launch)/w,6) if launch is not None else None,
                         qualification='conditional ETM/lightest-load estimate only; local R, global relation and parentSPEF must bind')
                budgets['conditional_exported_period_scenarios']=scenarios
            else:
                budgets['reason']='per-pin launch/capture ETM or actual clock period unavailable'
            row['corners'][corner]=budgets
        a=endpoint(row['source'],'ff',views);b=endpoint(row['destination'],'ff',views)
        launch=a.get('residual',{}).get('lmin');hold=b.get('residual',{}).get('hold')
        row['ff']=dict(status='OPEN',launch=a,capture=b,required_L_minus_H_ps=100,
            conditional_L_minus_H_ps=round(launch-hold,6) if launch is not None and hold is not None else None,
            required_launch_L_min_ps=round(hold+100,6) if hold is not None else None,
            qualification='no minimum wire-delay credit; actualFFreference/globalskew mustbind')
        rows.append(row)
    return dict(schema='opentallas.be_pair_timing.v1',status='OPEN',plan_source=sha(PLAN),views=manifest,liberty_sha256=provenance,
        equation=dict(setup='(O_A-R_A)+wire_ps_per_um*actual_routed_length+(S_B+R_B)<=T-60-skew',hold='(L_A-R_A)-(H_B-R_B)>=100ps'),
        actual_global_clock_bindings=plan['clock_bindings'],actual_global_reset_bindings=plan['reset_bindings'],
        scope='real exported per-pin arcs; conditional localR estimates and exported-period scenarios are explicitly unqualified; no blanket500um timing verdict',
        missing_masters=sorted({e['master'] for p in plan['pairs'] for e in [p['source_endpoint'],p['destination_endpoint']] if e['master'] not in views}),
        pairs=rows,summary=dict(pairs=len(rows),BE_input_sink_pairs=sum(p['kind'].endswith('sink') for p in rows),qualified_pairs=0),
        pass_=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,default=PLAN);ap.add_argument('--views-json',type=Path);ap.add_argument('--out',type=Path,default=AUDIT/'pair_timing.json');a=ap.parse_args()
    if a.views_json:manifest=json.loads(a.views_json.read_text())
    else:
        sta_path=ROOT/BE_VIEW/'corner_sta.json';sta=json.loads(sta_path.read_text())
        period=float(re.search(r'create_clock -name core_clk -period ([\d.]+)',sta['sdc'])[1])
        sdc_path=ROOT/'physical/s81_ph_views/vm_master/be_sl_clock.sdc'
        assert 'period] * 3.0 / 4.0' in sdc_path.read_text()
        manifest={'dsfd_vm_be_sl':dict(dir=BE_VIEW,eligible=False,
            period_ps={'ck[0]':period,'cks[0]':period*3/4},
            period_source_sha256={str(sta_path.relative_to(ROOT)):sha(sta_path),str(sdc_path.relative_to(ROOT)):sha(sdc_path)},
            period_scope='actuallegacy6_finalSDCsnippet coreperiod; sourcebe_sl_clockSDCstrperiod3/4; actualglobalclockbinding absent')}
    d=build(json.loads(a.plan.read_text()),manifest);d['plan_source']=sha(a.plan)
    a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(dict(summary=d['summary'],missing_masters=d['missing_masters'],status=d['status']),indent=2));return 1
if __name__=='__main__':raise SystemExit(main())
