import json,csv
P='/tmp/codex-rck-redesign-1107/';old=json.load(open(P+'rm_405_perbit_budget.json'));stages={k:[]for k in ['source','write_capture','read_core','read_relay1','read_relay2','BOUT']};rows=[];rad=[0,2,18,2,2,0]
for b in old['bits']:
 a=b['actual_face_q_d'];c=b['slice_center'];z=b['actual_bout'];w=[(a[k]+c[k])/2for k in(0,1)];r1=[c[k]+(z[k]-c[k])/3for k in(0,1)];r2=[c[k]+2*(z[k]-c[k])/3for k in(0,1)];r1[0]-=12;r2[0]-=6
 points=[a,w,c,r1,r2,z];bounds=[abs(points[n][0]-points[n+1][0])+abs(points[n][1]-points[n+1][1])+rad[n]+rad[n+1]for n in range(5)]
 for name,pt in zip(stages,points):stages[name].append(pt)
 rows.append({'bit':b['bit'],'points':points,'max_L1_each_leg_any_independent_site_um':bounds})
result={'status':'PLANNING_HOLD_NO_KIT','core_um':[1828,98,1972,242],'stage_order':list(stages),'L1_site_radii_um':rad,'site_halfwidth_um':[0,1,9,1,1,0],'independence':'EVERY bit leg is bounded independently at both endpoint sites; no correlated stage displacement assumed','delta_vs_H':{'publication_w':1,'read_pipeline_r':2,'memorycommit_w':0},'max_each_leg_um':[max(x['max_L1_each_leg_any_independent_site_um'][n]for x in rows)for n in range(5)],'fail_leg_bits':sum(v>405for x in rows for v in x['max_L1_each_leg_any_independent_site_um']),'cohorts':{},'bits':rows}
for n,(name,pts)in enumerate(stages.items()):
 h=result['site_halfwidth_um'][n];box=[min(x[0]for x in pts)-h,min(x[1]for x in pts)-h,max(x[0]for x in pts)+h,max(x[1]for x in pts)+h];result['cohorts'][name]={'rect':box,'center':[(box[0]+box[2])/2,(box[1]+box[3])/2],'perbit_site_halfwidth':h,'note':'envelope is NOT freebit placement box. Each named bit stays in ownsite.'}
json.dump(result,open(P+'rm_independent405.json','w'),indent=2);print({k:v for k,v in result.items()if k not in('bits','cohorts')});print(result['cohorts'])
