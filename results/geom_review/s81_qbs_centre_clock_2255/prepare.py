"""DISABLED physical-only event; emit candidate contracts and a complete plan in scratch.
No canonical file is written. Existing timing views are invalidated, never relabelled.
"""
import argparse,copy,hashlib,json,re,pathlib
ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--plan',required=True);ap.add_argument('--out',required=True);ap.add_argument('--parent-spec',action='append',default=[],help='selected parent spec repo-relative path; emits coherent copy');a=ap.parse_args()
r=pathlib.Path(a.repo);o=pathlib.Path(a.out);o.mkdir(parents=True,exist_ok=True)
mods=['dsfd_node_LLfu','dsfd_node_LLfd','dsfd_node_NNfu']; p=json.load(open(a.plan)); before=copy.deepcopy(p)
eventrel='physical/die_plan/s81/proposals/DISABLED_qbs_centre_clock_2255'
sha=lambda x:hashlib.sha256(x).hexdigest()
records=[];views={}
for mod in mods:
 oldview=f'physical/ref_tile/s81net_node_{mod.split("_")[-1].lower()}/views/{mod}'
 oldpin=f'physical/die_plan/s81/inputs/core_pins/{mod}.json'; oldlef=f'{oldview}/{mod}.lef'
 newview=f'{eventrel}/views/{mod}'; newpin=f'{eventrel}/pins/{mod}.json';newlef=f'{newview}/{mod}.lef'; views[oldview]=newview
 pj=json.load(open(r/oldpin)); bp=copy.deepcopy(pj)
 q=next(x for x in pj['pins'] if x['name']=='clk[0]');q.update(layer='M5',x=21.612,y=38.892)
 pj.update(lef=newlef,source='DISABLED COORD centre-clock event 2026-11-01; original contract retained',status='PROPOSED_NOT_ACTIVE')
 pj.pop('pinhash',None)
 assert [x for x in bp['pins'] if x['name']!='clk[0]']==[x for x in pj['pins'] if x['name']!='clk[0]']
 lf=(r/oldlef).read_text(); pat=r'(?m)^  PIN clk\[0\]\n.*?^  END clk\[0\]$'
 replacement='  PIN clk[0]\n    DIRECTION INPUT ;\n    USE CLOCK ;\n    PORT\n      LAYER M5 ;\n        RECT 21.588 38.652 21.636 39.132 ;\n    END\n  END clk[0]'
 newlf,n=re.subn(pat,replacement,lf,flags=re.S);assert n==1
 for path,data in [(newpin,json.dumps(pj,indent=1)+'\n'),(newlef,newlf)]:
  dst=o/path;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(data)
 sl={'schema':'opentallas.master_plan_slice.v1','die':'s81','kind':'core','type':mod,'module':mod,'instances':[], 'master_plan_sha256':sha(pathlib.Path(a.plan).read_bytes()),'frozen':False,'outline_um':[43.2,77.76],'core_clock_port':'clk','keepouts':[], 'islands':[{'name':'centre_clock_entry','rect_um':[20.532,37.692,22.692,40.032],'centre_um':[21.612,38.892],'clock_pin':{'layer':'M5','xy_um':[21.612,38.892]},'use':'PG-safe centre entry reserved for new normal floorplan/clock stages'}], 'bays':[{'name':'entry_driver','kind':'repeater','rect_um':[20.532,37.692,22.692,40.032],'owner':mod+'.clock','note':'reserved actual driver placement/tree topology must be supplied before CTS; no old-tree reuse'}], 'entry_pins':[],'hard_cores':[],'latency':{'common_clock_latency_ps':{'TT':250,'FF':202.5},'tol_ps':40},'gates':{'actual_floorplan':'NOT RUN','clock_tree':'NOT RUN'},'note':'DISABLED; do not use old extracted timing views after clock move.'}
 dst=o/'slices'/f'{mod}.json';dst.parent.mkdir(exist_ok=True);dst.write_text(json.dumps(sl,indent=1)+'\n')
 records.append({'module':mod,'old_pins':oldpin,'old_lef':oldlef,'new_pins':newpin,'new_lef':newlef,'old_clock':next(x for x in bp['pins'] if x['name']=='clk[0]'),'new_clock':q,'signal_pin_changes':0,'outline_changes':0,'source_rtl_changes':0,'new_cycles':0,'synth_reusable_if_exact_inputs_match':True,'old_pin_sha256':sha((r/oldpin).read_bytes()),'old_lef_sha256':sha(lf.encode()),'new_lef_sha256':sha(newlf.encode())})
# Rewrite every actual plan hard-core occurrence, preserving all placement/data/reset facts.
changes=[]
for typ,t in p['partition_types'].items():
 for h in t.get('hard_cores',[]):
  if h.get('module') not in mods:continue
  mod=h['module'];rec=next(x for x in records if x['module']==mod)
  old=copy.deepcopy(h);h['lef']=rec['new_lef'];h['pins_file']=rec['new_pins'].removeprefix('physical/die_plan/s81/')
  # A changed clock entry invalidates all old clock-relative parent timing views.
  for k in ('lib','lib_ff','lib_tt','core_json'):
   if k in h:h[k]=str(pathlib.PurePosixPath(rec['new_lef']).parent/pathlib.PurePosixPath(h[k]).name)
  h['clock_entry_event']='DISABLED_qbs_centre_clock_2255';changes.append({'type':typ,'inst':h['inst'],'before':old,'after':copy.deepcopy(h)})
p['note']=p.get('note','')+' DISABLED QBS centre-clock candidate; no current timing-view adoption; new libs missing until genuine export.'
(o/'plan_candidate.json').write_text(json.dumps(p,separators=(',',':'))+'\n')
parent_specs=[]
for rel in a.parent_spec:
 data=json.load(open(r/rel));count=0
 for child in data.get('children',[]):
  if child.get('view') in views:
   child['view']=views[child['view']];count+=1
 if not count:raise SystemExit('Parent spec has none of the changed views: '+rel)
 dst=o/'parent_specs'/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text(json.dumps(data,indent=1)+'\n')
 parent_specs.append({'source':rel,'sha256':sha((r/rel).read_bytes()),'changed_children':count,'candidate':str(dst.relative_to(o))})
(o/'event.json').write_text(json.dumps({'status':'DISABLED_PROPOSAL_NO_CAD','base_plan':str(a.plan),'base_plan_sha256':sha(pathlib.Path(a.plan).read_bytes()),'records':records,'parent_plan_occurrences':changes,'parent_child_view_replacements':views,'selected_parent_specs':parent_specs,'required_parent_spec_action':'Replace children[].view by this exact mapping in any selected parent build; never mix old/new child views. Historical spec snapshots remain untouched.','clock':{'entry_um':[21.612,38.892],'shape_um':[.048,.48],'tracks':{'offset':.012,'pitch':.048},'driver_bay_um':[20.532,37.692,22.692,40.032],'PG_M5_pairs_um':[[19.344,19.536],[23.664,23.856]],'minimum_clock_rect_PG_edge_clearance_um':1.968,'maximum_geometric_entry_sink_L1_um':60.504,'actual_driver_tree':'NOTRUN; reserve bay, fix actual driver ownership before CTS'}},indent=1)+'\n')
print(json.dumps({'candidate_out':str(o),'parent_occurrences':len(changes),'types':len(set(x['type'] for x in changes)),'modules':mods}))
