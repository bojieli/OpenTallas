from pathlib import Path
import json
R=Path('/srv/opentallas-scratch2/claude/codex-hbm-1030');p=R/'hh_seams2/die_plan.json';r=json.load(open(p));assert not any(x['name'].startswith('SOUTHERN_VMS_') for x in r.get('latency_groups',[]))
ps={x['id']:x for x in r['ports']};new={}
for l in r['lanes']:
 if l['id'] in ('L700','L701'):new[(ps[l['ports'][0]]['src']['part'],ps[l['ports'][-1]]['dst']['part'])]=l['id']
for pair,ctl in [(('NE_hub','NW_hub'),'L96m'),(('NW_hub','NE_hub'),'L96')]:
 r.setdefault('latency_groups',[]).append({'name':'SOUTHERN_VMS_'+pair[0],'kind':'bus','lanes':[new[pair],ctl],'source':'nativeSouthernVMS_and_hcollb','note':'Actualnativebinding allocates fullSouthernVMS2224 onnewdetour; hcollb packet remaining22bits onL96. Bothactualbusgroups receiveequalplanaddeddepth; padonly22bitcontrol lane. NorthernVMS/prHCOLold11cycleL4unchanged.'})
r['note']='HH seam-aware: first/laststage<=30um fromdeclaredpins andvia-seamhop<=364.5; actualnew18/21cycles, explicit22bitR8pads | '+r.get('note','');json.dump(r,open(p,'w'),indent=1)
