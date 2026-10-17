from pathlib import Path
import gzip,json,collections,math,hashlib
r=Path(__file__).parent;j=json.load(gzip.open('/home/ubuntu/artifacts/s81-connected-0305/first_pass_plan_17b.json.gz','rt'));base={i['name']:i for i in j['insts']};c=json.load(gzip.open(r/'C_east_horiz_final_preserve_upstream.json.gz','rt'));d={n:dict(a) for n,a in base.items()};d.update(c['homes']);slots=[];names=set();by=collections.defaultdict(list)
for bus in j["buses"]:
 for n,p0 in bus[3]:by[n].append(bus)
for n in d:
 if n.startswith('f_cx') and n in c['homes'] and n.rsplit('_',1)[-1] in ['1','2']:
  # Only the literal per-column cx source stations, never global edge stations.
  import re
  m=re.fullmatch(r'f_cx(\d+)(_x2)?_([12])',n)
  if not m:continue
  w=538 if m[2] else 566;a=d[n];a['w']=17.28;a['h']=32.4;a['orient']='R0';a['master']=f'dsfd_cfifo_fwd{w}_ew_fn';names.add(n)
  bs=by[n]
  slots.append(dict(instance=n,column=int(m[1]),lane=1 if m[2] else 0,stage=int(m[3]),master=a['master'],candidate_origin_um=[a['x'],a['y']],outline_um=[17.28,32.4],orientation='R0',old_master=base[n]['master'],old_orientation=base[n]['orient'],incident_buses=bs,grant_status='NOT_GRANTED_FINAL_SOURCE_PIN_SLOT_PG',clock_relation='same2station chain; fo0 inverted,fn0 noninverted; noaddedstage,physicalphaseUNPROVEN'))
grid=collections.defaultdict(set)
for n,a in d.items():
 for x in range(math.floor(a['x']/200),math.floor((a['x']+a['w'])/200)+1):
  for y in range(math.floor(a['y']/200),math.floor((a['y']+a['h'])/200)+1):grid[x,y].add(n)
def ov(a,b):return min(a['x']+a['w'],b['x']+b['w'])>max(a['x'],b['x'])+.001 and min(a['y']+a['h'],b['y']+b['h'])>max(a['y'],b['y'])+.001
pairs=set()
for n in names:
 a=d[n];near=set()
 for x in range(math.floor(a['x']/200),math.floor((a['x']+a['w'])/200)+1):
  for y in range(math.floor(a['y']/200),math.floor((a['y']+a['h'])/200)+1):near.update(grid[x,y])
 for z in near:
  if z!=n and ov(a,d[z]):pairs.add(tuple(sorted([n,z])))
x=dict(scope='C_DIAGNOSTIC_R0_STATION_SLOT_REQUEST_NOT_A_GRANT',source=j['source_commit'],plan_sha256=hashlib.sha256(Path('/home/ubuntu/artifacts/s81-connected-0305/first_pass_plan_17b.json.gz').read_bytes()).hexdigest(),parent_source_unchanged='9a1b4fc3cc12628bf4864566326473416a18a6cc',slots=sorted(slots,key=lambda a:(a['column'],a['lane'],a['stage'])),master_replicas=dict(collections.Counter(a['master'] for a in slots)),source_capture_edges_added=0,global_clock_phase_qualified=False,snapped_final_origins=False,outline_note='Use actual17.28x32.4 body, not shaved17.256x32.376 abstract',actual_body_overlap_pairs=[list(a) for a in sorted(pairs)],actual_pin_reach_qualified=False,actual_cut_qualified=False,wholeframe_min108um_street_fit=False,interface=dict(data_inputs={'di0':'Wbits includingmarker0/valid1'},data_outputs={'do0':'Wbits'},clock_inputs={'fi0':'one'},clock_outputs={'fo0':'invertedfi0','fn0':'double-invertedfi0'},reset_ports=[],R0_faces={'E':['di0','fi0'],'W':['do0','fo0','fn0']}),open=['Netfill literalfn0 R0source/phase/reset/epoch bench','Die-owned actualallincidentpins/cuts/clocks/PG/slot grant','4KVlinks beyond430.56um lowerbound','Wholeframe108umstreet cannot inherit159.84parentfit'])
(r/'C_R0_slot_request.json').write_text(json.dumps(x,indent=1)+'\n');print('slots',len(slots),'replicas',x['master_replicas'],'overlap_pairs',len(pairs))
