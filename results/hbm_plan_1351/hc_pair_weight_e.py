"""Physical end-pair interface: one native input copy at the actual E-side weight partner."""
import json,pathlib,math,sys,collections
B=pathlib.Path(__file__).parent;I=B/"xq_pin6_center_trial";O=B/"pin6_bundle";O.mkdir(exist_ok=True);(O/"cores").mkdir(exist_ok=True)
for f in I.iterdir():
 if f.is_file() and f.name!="die_plan.json" and not(O/f.name).exists():(O/f.name).symlink_to(f)
for f in (I/"cores").iterdir():
 if not(O/"cores"/f.name).exists():(O/"cores"/f.name).symlink_to(f)
P=json.load(open(I/"die_plan.json"));fn="ot_hbm_hc_bank128_pair_core__250.56x267.84__canon.json";a=json.load(open(I/"cores"/fn));names={"weight_we0","weight_we1","write_addr","x_write"};qs=sorted([q for q in a if q["name"].split("[")[0]in names],key=lambda q:q["x"])
used={q["y"] for q in a if q["x"]>248.56};ys=[]
for k in range(math.ceil((64.8-.024)/.048),math.floor((70-.024)/.048)):
 y=round(.024+k*.048,3)
 if y not in used and (not ys or y-ys[-1]>=.1439):ys.append(y)
 if len(ys)==len(qs):break
assert len(ys)==len(qs)==13
delta=[]
for q,y in zip(qs,ys):
 delta.append({"name":q["name"],"old_xy_layer":[q["x"],q["y"],q["layer"]],"xy_layer":[250.541,y,"M4"]});q.update(x=250.541,y=y,layer="M4")
new="ot_hbm_hc_bank128_pair_core__250.56x267.84__weight_E.json";(O/"cores"/new).write_text(json.dumps(a,indent=1)+"\n")
changed=[]
for tn in ["q_b002","q_b011"]:
 for c in P["partition_types"][tn]["hard_cores"]:
  if c["inst"].endswith("pair3"):
   assert c["pins_file"].endswith(fn);c["pins_file"]="cores/"+new;changed.append([tn,c["inst"]])
(O/"die_plan.json").write_text(json.dumps(P,indent=2)+"\n")
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan");import check,schema
checks={}
for tag,path in [("before",I),("after",O)]:
 raw=json.load(open(path/"die_plan.json"));p=schema.Plan(raw,path/"die_plan.json");p.types={k:v for k,v in p.types.items()if k in ["q_b002","q_b011"]};r=check.Report(True);summary=check.check_core_faces(p,r,path);checks[tag]={"summary":summary,"errors":r.errors()};print(tag,summary,len(r.errors()))
W,H=250.56,267.84;peaks={}
for face in "WESN":
 vals=[]
 for q in a:
  d=[q["x"],W-q["x"],q["y"],H-q["y"]]
  if min(d)<=2 and "WESN"[d.index(min(d))]==face:vals.append(q["y"] if face in "WE" else q["x"])
 vals.sort();i=0;mx=0
 for j,x in enumerate(vals):
  while x-vals[i]>10+1e-7:i+=1
  mx=max(mx,j-i+1)
 peaks[face]=mx/10
rep={"basis":"C15 errors identify exact E-side partner L42_i/L43_i, window1126.848..1270.464, last pair origin1131.84; sourcepincentres64.8..70locally alongside that window","changed_instances":changed,"native_port_names_unchanged":True,"input_copies_added":0,"port_bits_moved":13,"face_delta":"N→E for end-pair actual weight input partner; all other instances keep canonical view","cycles_added":0,"pin6_peaks":peaks,"core_faces_checks":checks,"delta":delta,"qualification":"PHYSICAL INTERFACE CANDIDATE; freshselectedkit/LEF/Lib/station-ends/nativegraph requiredbeforeadoption"};(O/"hc_pair_weight_E_report.json").write_text(json.dumps(rep,indent=2)+"\n");print("peaks",peaks)
