"""Reuse actual26 cached data hull; reprice native-clock START only.
Rounded cached wander is expanded by 0.0500001 ps, preserving conservative bounds.
No new data STA claim: cached hull remains source-pinned diagnostic evidence.
"""
import json,sys,pathlib
BASE=pathlib.Path('/srv/opentallas-scratch2/claude/codex-qc-start-native-0251')
R=BASE/'midleg1';R.mkdir(exist_ok=True)
OLD=pathlib.Path('/srv/opentallas-scratch2/claude/codex-qc-start-provider-1029')
Q=pathlib.Path('/srv/opentallas-scratch2/claude/codex-qc-1029')
sys.path.insert(0,str(BASE/'src/tools/die_plan'))
import count_align_plan as P,count_align_bind as B
cached=json.load(open(OLD/'actual26/plan.json'))
rows=[]
for c in cached['crossings']:
 r={k:c[k] for k in ['port','src','dst','src_part','dst_part','d_ps','p_dn_ps','p_up_ps']}
 r.update(unshared_sta_ps=(c['wander_ps']+.0500001)/.05,_named=True,margin_ps=c['old_ring_margin_ps'])
 rows.append(r)
plan=Q/'physical_event/plan_start_native_h800.json'
captures=json.load(open(Q/'physical_event/capture_taps.json'))
assert len(captures)==313 and all(x.endswith('__clk') for x in captures.values()),'native RTL clk only'
ctx=P.clock_contexts(OLD/'actual26/proof',plan,['TT','FF'],'spice_edge','table','shared',OLD/'actual26/proof/droop_regions.json',202.5,'inv')
sys.path.insert(0,str(BASE))
import midleg_overrides as M,die_trial as DT,schema as S
failed=[e for e in json.load(open(BASE/'start_edges.json'))['edges'] if not e['clean_ok']]
site=DT.SiteMap(S.Plan(S.load(plan)))
overrides=M.propose(failed,ctx,site)
(R/'stage_placement_overrides.json').write_text(json.dumps(overrides))
ctx=M.contexts_with_geometry(ctx,overrides)
print('MIDLEG_GEOMETRY',len(overrides),max(v['provisional_clock_stub_um'] for v in overrides.values()),flush=True)
print('CTXREADY',len(rows),len(captures),flush=True)
root,edges,info=P.clock_start_edges(rows,ctx,retime_max=256,clean_by='width',retime_up=True,max_hop_um=400,capture_taps=captures)
print('START',json.dumps(info),flush=True)
(R/'start_edges.json').write_text(json.dumps(dict(root=root,edges=edges,info=info)))
summ,out,regs=P.plan(rows,start_edges=edges,start_root=root)
summ.update(period_ps=833,aperture_ps=833/8,sync_aperture_ps=26.5,pad=0,wander_frac=.05,sta_hull=cached['summary']['sta_hull'],cached_wander_expansion_ps=.0500001,scope='PROVISIONAL STAGE SITING: clock stubs newly added; no measured loaded stage-clock phase claim')
summ['start_tree'].update(info)
doc=dict(summary=summ,crossings=out,regions=regs,start_edges=edges)
(R/'plan.json').write_text(json.dumps(doc));print('SUMMARY',json.dumps(summ),flush=True)
if summ['fail'] or summ['start_tree']['start_fail']:raise SystemExit('native START FAIL; no emission/adoption')
b=B.bind(doc,parts=B.ocv_parts(rows));(R/'bind.json').write_text(json.dumps(b));print('BINDPASS',len(b['ports']),len(b['start_ports']),flush=True)
