"""Actual ordinary type input pins→first soft FF DATA cone, no source/phase credit."""
import pathlib,json,gzip,sys,argparse,collections
ap=argparse.ArgumentParser();ap.add_argument('--runtime',required=True);ap.add_argument('--tools-root',required=True);ap.add_argument('--proposal-dir');ap.add_argument('--sites');a=ap.parse_args();r=pathlib.Path(a.runtime);B=pathlib.Path(__file__).resolve().parent;o=pathlib.Path(a.proposal_dir)if a.proposal_dir else B/'geometry_r0_nativepins';sys.path.insert(0,str(pathlib.Path(a.tools_root)/'tools/die_plan'));import schema as S,gen_phys as GP
raw=json.load(gzip.open(o/'DISABLED_PARENT_PLAN_UNRELEASED.json.gz'));P=S.Plan(raw);pins=GP.type_pins(P,'coll_core');pt={(p,b):(x,y)for p,b,l,x,y,f in pins};ins={b['name']for b in raw['partition_types']['coll_core']['buses']if b['dir']=='in'};src=json.load(gzip.open(r/'core_source_graph_v3.json.gz'));ss=json.load(gzip.open(pathlib.Path(a.sites)if a.sites else o/'CURRENT_PIN_ALL_FF_SITES.json.gz'));xy={x['ff']:x['center_um']for x in ss['rows']};extra=collections.defaultdict(dict);missing=[];infra=set();rows=[];failed=[]
for ff,ts in src['relevant_ff_input_sources'].items():
 for ti in ts:
  t=src['terms'][ti]
  if t[0]!='TOP':continue
  port,bit=t[1:]
  if port not in ins:infra.add(port);continue
  if(port,bit)not in pt:missing.append([port,bit]);continue
  q=pt[port,bit];e={'node':'TYPE_INPUT','instance':'coll_core.TYPE_INPUT','port':port,'bit':bit,'xy_um':q,'center_budget_um':149,'endpoint_budget_um':150};extra[ff][port,bit]=e
  d=sum(abs(x-y)for x,y in zip(xy[ff],q));row={'ff':ff,'name':src['ff_nodes'][ff]['name'],'port':port,'bit':bit,'pin_xy_um':q,'FF_center_um':xy[ff],'pin_to_first_FF_center_um':d};rows.append(row)
  if d>149+1e-6:failed.append(row)
summary={'status':'ACTUAL_TYPE_INPUT_FIRST_FF_SOURCE_PROPOSAL_AUDIT','ordinary_input_constraint_rows':len(rows),'first_FFs':len(extra),'missing_typed_pins':sorted(set(tuple(x)for x in missing)),'center_budget_um':149,'actual_FF_pin_halfextent_reserve_um':.837,'failed_at_current_FF_sites':len(failed),'max_pin_to_first_FF_center_um':max(x['pin_to_first_FF_center_um']for x in rows),'unqualified_infrastructure_top_inputs':sorted(infra),'failure_groups':collections.Counter(x['port']for x in failed).most_common()};(o/'TYPE_INPUT_FIRST_FF_AUDIT.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(o/'TYPE_INPUT_FIRST_FF_CONSTRAINTS.json.gz','wt')as f:json.dump({'summary':summary,'FF_input_constraints':{ff:list(e.values())for ff,e in extra.items()},'failures':failed},f,separators=(',',':'))
print(json.dumps(summary))
