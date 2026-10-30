from pathlib import Path
import sys,json,copy
w=Path('/srv/opentallas-scratch2/claude/wt/codex-collft-0336');b=Path('/srv/opentallas-scratch2/claude/codex-collft-0336');sys.path.insert(0,str(w/'tools/die_plan'))
import clock_landings as C
p=json.load(open(b/'plan/plan_collft_boot_candidate.json'));t=json.load(open(b/'plan/sidecar_qc33.json'));tn='coll_ft__cla4a25d77';old=copy.deepcopy(p);old['partition_types'][tn]['clock'].pop('landing_origin_boot_branch')
a=C.Landings(old,t,require_geometry=False);z=C.Landings(p,t,require_geometry=False)
assert a.region==z.region
ar={q['port']:q for q in a.manifest()['ports']};zr={q['port']:q for q in z.manifest()['ports']}
changed=[dict(port=k,old=ar[k]['ring_k'],new=v['ring_k']) for k,v in zr.items() if ar[k]['ring_k']!=v['ring_k']]
assert len(changed)==8 and all(q['old']==14 and q['new']==15 for q in changed)
oldties=a.strap['instances'];newties=z.strap['instances'];changed_ties=[]
for inst,r in newties.items():
 for pin,v in r['values'].items():
  if oldties[inst]['values'][pin]!=v:changed_ties.append(dict(instance=inst,pin=pin,old=oldties[inst]['values'][pin],new=v))
assert len(changed_ties)==8 and all(q['old']==14 and q['new']==15 for q in changed_ties)
raws={n:'cland_reset_'+n for n in ['crec_rx_s1_i','crec_rx_s2_i','crec_tx_s1_i','crec_tx_s2_i','fltk_i','fltv_i']}
z.reset_placements[tn]={'crec_rx_s1_i':dict(net=raws['crec_rx_s1_i'],copied_raw_parent='rst_rl_9')}
lines,raw=z._origin_strap_rtl(tn,z.ca_type[tn]['role'],raws,[],lambda _:raws['crec_rx_s1_i']);s='\n'.join(lines)
assert '.BOOT_BRANCH_EXPORT(1)' in s and '.raw_parent(rst_rl_9)' in s and s.count('u_cland_boot_north')==1
pbad=copy.deepcopy(p);pbad['partition_types'][tn]['clock']['landing_origin_boot_branch']['raw_parent']='rst_rl_10';bad=C.Landings(pbad,t,require_geometry=False);bad.reset_placements[tn]=copy.deepcopy(z.reset_placements[tn])
try:bad._origin_strap_rtl(tn,bad.ca_type[tn]['role'],raws,[],lambda _:raws['crec_rx_s1_i'])
except C.LandingError:wrongraw='REJECTED'
else:raise AssertionError('wrong raw accepted')
out=dict(default_off_existing_rows_unchanged=True,region_mapping_unchanged=True,generated_K_changes=changed,parent_tie_changes=changed_ties,wrong_raw_parent=wrongraw,scope='actual full plan/table rows and typed origin hook; full native wrapper bind/physical integration NOT RUN')
(b/'boot_generator_report.json').write_text(json.dumps(out,indent=2)+'\n');(b/'boot_generator_origin.sv.txt').write_text(s+'\n');print(json.dumps(out,indent=2))
