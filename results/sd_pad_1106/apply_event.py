from pathlib import Path
import sys
import json,copy,re
r=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2];p=r/'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json';sp=p.with_name('eW_sidecar.json')
plan=json.load(open(p));t=json.load(open(sp));old=copy.deepcopy(t);ca=t['count_aligned'];leaves={'sys_SW','sys_SE'}
for region in leaves:
 assert ca['regions'][region]['pad']==0
 assert not any(v.get('parent')==region for v in ca['regions'].values())
 ca['regions'][region]['pad']=2
rows={v['port']:v for v in t['ports']};deltas=[]
for pid,cc in ca['ports'].items():
 if pid not in rows:continue
 row=rows[pid];ds=2 if row['src_region'] in leaves else 0;dd=2 if row['dst_region'] in leaves else 0
 if not(ds or dd):continue
 assert not cc.get('tree'),pid
 before=cc['K'];cc['K']=before+ds-dd
 assert cc['K']+dd-ds==before
 assert cc['depth']==old['count_aligned']['ports'][pid]['depth']
 assert cc['sched_lat']==old['count_aligned']['ports'][pid]['sched_lat']
 deltas.append({'port':pid,'src':row['src'],'dst':row['dst'],'old_K':before,'new_K':cc['K'],'src_origin_shift':ds,'dst_origin_shift':dd,'unchanged_schedule_cycles':cc['sched_lat']})
# Identity of the actual reader count/tag modulo retained count width.
checks=0
for width in (6,7,8):
 n=1<<width
 for k in range(n):
  for reader in range(n):
   for ds,dd in ((0,0),(2,0),(0,2),(2,2)):
    newk=(k+ds-dd)%n;newreader=(reader-dd)%n
    assert ((newreader-newk+ds)%n)==((reader-k)%n)
    checks+=1
assert ((0-2)-(-2+1))%64 != 0 # wrong-K+1 control changes delivered tag
sites={'u_cland_origin/sf':[180.954,20.25],'u_cland_origin/s0':[559.764,19.98],'u_cland_origin/s1':[928.962,19.98],'u_cland_origin/s2':[1298.214,19.98],'u_cland_origin/pd[0]':[1667.412,19.98],'u_cland_origin/pd[1]':[1876.5,180.09],'u_cland_origin/pd[2]':[1876.5,182.52]}
for tn in ('kv3_sys_SD','kv3_sys_SD_v1'):
 typ=plan['partition_types'][tn]
 for key,xy in sites.items():
  assert key not in typ.get('relay_sites',{}),key
 typ.setdefault('relay_sites',{}).update(sites)
 ps=next(x for x in typ['count_straps'] if x['name']=='strap_ca_pad');assert ps['width']==1;ps['width']=2
 typ['note']+=' | CODEX SD-PAD2 11-06: existing origin PAD0->2, two boot counts only, all incident K rebased to preserve absolute data lag and schedule. Source clock/EDGE_FALL/raw reset semantics unchanged. Seven explicit slash-key origin sites after landing placement, max routed hop379.08um including sf. Actual MCMM GRT/signoff still required.'
t['note_dkv2']=str(t.get('note_dkv2',''))+' | CODEX SD-PAD2 11-06: sys_SW/sys_SE leaf PAD0->2; K+=src_shift-dst_shift on incident data crossings, depth/schedule/data latency unchanged; +2 boot counts.'
p.write_text(json.dumps(plan,indent=1)+'\n');sp.write_text(json.dumps(t,indent=1)+'\n')
out=r/'results/sd_pad_1106';out.mkdir(parents=True,exist_ok=True)
(out/'delta.json').write_text(json.dumps({'leaves':sorted(leaves),'boot_counts_added':2,'data_cycles_added':0,'rtl_changes':0,'sites':sites,'crossings':deltas,'tag_identity_checks':checks,'wrong_K_mutant':'caught'},indent=1)+'\n')
(out/'tag_identity.txt').write_text('For every retained counter width: Knew=Kold+ds-dd, Rnew=Rold-dd. Thus Rnew-Knew+ds=Rold-Kold modulo 2^TW. Writer count shifts by -ds, so delivered absolute word identity and lag are unchanged. All 344064 width6/7/8 reader/K/shift cases pass; Knew+1 mutant fails. Regions are leaves; all affected data crossings are non-tree. Ring depth and scheduled data cycles remain identical. Origin RTL PAD2 exact delay proof separately covers START and START_D +2, both edge choices and repeated raw reset.\n')
print('SD_PAD2_EVENT',len(deltas),'crossings',checks,'tagchecks')
