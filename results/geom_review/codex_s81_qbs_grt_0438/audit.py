from pathlib import Path
import json,tkinter,importlib.util,collections
p=Path('/home/ubuntu/coord/tmp/codex-qbs-grt-audit-0438');t=tkinter.Tcl();r=[list(t.splitlist(l)) for l in (p/'sites.tsv').read_text().splitlines()];base=Path('/home/ubuntu/coord/tmp/codex-qbs-audit-2353/dsfd_node_LLfu');old=json.load(open(base/'audit.json'));sl=json.load(open('/home/ubuntu/coord/tmp/codex-qbs-sites-2320/dsfd_node_LLfu/legalized_slice.json'));nodes={x[1]:x for x in r if x[0]=='NODE'};bad=[]
for n,q in old['nodes'].items():
 if nodes.get(n)!=q:bad.append([n,q,nodes.get(n)])
spec=importlib.util.spec_from_file_location('G','/home/ubuntu/OpenTallas/tools/autopilot/geom_rules.py');G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G);d=G.Design(p/'geom.tsv');by={c[6]:i for i,c in d.cells.items()};memberbad=[];depths={};unknown=[];clockids=set()
for leaf in sl['core_tree']['leaves']:
 start=by[leaf['node']];stack=[(n,0) for n in d.drives.get(start,[])];seen=set();terms={};clockids.add(start)
 while stack:
  n,dep=stack.pop()
  if n in seen:continue
  seen.add(n)
  for s in d.nets[n][2]:
   if s[0]!='i':continue
   cid=s[1];c=d.cells[cid]
   if c[0]=='S' and s[2]:terms[c[6]+'/CLK']=dep
   elif c[6].startswith('clkload') and c[0] in ['B','K'] and not d.drives.get(cid):clockids.add(cid)
   elif c[0]=='B':clockids.add(cid);stack.extend((a,dep+1) for a in d.drives.get(cid,[]))
   else:unknown.append([leaf['node'],c[6],c[0],s[2]])
 exp=set(leaf['sinks']);act=set(terms)
 if exp!=act:memberbad.append({'leaf':leaf['node'],'missing':sorted(exp-act),'extra':sorted(act-exp)})
 depths[leaf['node']]={'sinks':len(terms),'depth_counts':dict(collections.Counter(terms.values()))}
clockids.update(by[n] for n in nodes)
dummies={i for i in clockids if d.cells[i][6].startswith('clkload')}
functional=clockids-dummies
masterpg=next(x for x in r if x[0]=='MASTER_PG_CENSUS')
full_pg_errors=[x for x in r if x[0]=='MASTER_PG_ERROR']
clockpg=[x for x in r if x[0]=='PGPIN' and x[1] in {d.cells[i][6] for i in clockids}]
newtap={(x[1],tuple(map(float,x[3:7]))) for x in r if x[0]=='FIXED' and x[2]=='TAPCELL_ASAP7_75t_R'};oldr=[list(t.splitlist(l)) for l in (base/'sites.tsv').read_text().splitlines()];oldtap={(x[1],tuple(map(float,x[3:7]))) for x in oldr if x[0]=='FIXED' and x[2]=='TAPCELL_ASAP7_75t_R'};pg={ly:sorted({tuple(x[3:7]) for x in r if x[0] in ['PG','PGVIA'] and x[2]==ly}) for ly in ['M4','M5']};oldpg={ly:sorted({tuple(x[3:7]) for x in oldr if x[0] in ['PG','PGVIA'] and x[2]==ly}) for ly in ['M4','M5']};pins={(x[1],x[2]):x[3] for x in r if x[0]=='NODEPIN'};pg_bad=[(n,pin,pins.get((n,pin))) for n in nodes for pin in ['VDD','VSS'] if pins.get((n,pin))!=pin]
oldgeo=G.Design('/home/ubuntu/coord/tmp/codex-qbs-cts-pg-0117/dsfd_node_LLfu/geom.tsv');oldby={c[6]:c for c in oldgeo.cells.values()};clockpose_bad=[d.cells[i][6] for i in clockids if oldby.get(d.cells[i][6])!=d.cells[i]];ffpose_bad=[c[6] for c in d.cells.values() if c[0]=='S' and oldby.get(c[6])!=c]
result={'source':'Actual gen10 full-PG normal5_1_grt.odb','planned13node_changes_fromPLACE':bad,'planned_clock_PG_pin_errors':pg_bad,'leaf_membership_errors':memberbad,'unexpected_clock_children':unknown,'leaf_CTS_subtrees':depths,'TAP_count':len(newtap),'TAP_exact_identity':newtap==oldtap,'PG_geometry_exact_identity':pg==oldpg,'native_clock':G.clock_metrics(d),'native_geometry':G.r2r_metrics(d),'area':G.area_metrics(d),'all_clock_pose_master_changes_from_CTS':clockpose_bad,'FF_pose_master_changes_from_CTS':ffpose_bad,'functional_clock_cells':len(functional),'dummy_clock_load_cells':len(dummies),'clock_cell_total':len(clockids),'clock_PG_terms':len(clockpg),'clock_PG_errors':[x for x in clockpg if x[-1] not in ['VDD','VSS']],'full_master_PG_terms':int(masterpg[1]),'full_master_PG_errors':full_pg_errors,'source_FF':sum(c[0]=='S' for c in d.cells.values()),'dummy_with_output_nets':[d.cells[i][6] for i in dummies if d.drives.get(i)]};(p/'audit.json').write_text(json.dumps(result,indent=2));(p/'clock_buffer_ids.json').write_text(json.dumps(sorted(clockids)));print(json.dumps(result,indent=1))
