from pathlib import Path
import json,re,hashlib,csv,math
R=Path(__file__).resolve().parent
ROOT=R.parents[1]
ORIG=Path('/srv/opentallas-scratch/claude/wt/codex-ft-obstacle-union-2149/results/hbm_storeA_sourceproof_intake_0030')
TCL=Path('/srv/opentallas-scratch/claude/wt/codex-clock-union-2208/results/clk/hbm_storeA_native_geometry_1102/gutter_macro_placement_capture_gutters.tcl')
MOD='ot_hnx_sfu_store_a_regional4_captured';W,H=760.32,483.84
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,value):(R/name).write_text(json.dumps(value,indent=1)+'\n')
header=(R/(MOD+'.sv')).read_text().split(');',1)[0]
ports=[dict(name=n,direction=d,width=int(w)+1)for d,w,n in re.findall(r'^    (input|output) wire \[(\d+):0\] (\w+)[,\n]',header,re.M)]
assert sum(p['width']for p in ports)==5986
pins=[];edge_idx=[0,0];raw_idx=0
for p in ports:
 for b in range(p['width']):
  n=f"{p['name']}[{b}]"
  if p['name'] in ['store0_clk','store0_rst_n','capture_ctl_reset_n','capture_meta_reset_n']:
   k=['store0_clk','store0_rst_n','capture_ctl_reset_n','capture_meta_reset_n'].index(p['name']);x,y,layer=375.864+.24*k,324.12,'M5'
  elif p['name'] in ['capture_payload_D','capture_meta87_D']:
   # Full M4 metal fits the actual central8.64um intercolumn channel.
   x=374.184+.24*(raw_idx%14);y=216.648+.048*(raw_idx//14);layer='M4';raw_idx+=1
  else:
   side=len(pins)%2;idx=edge_idx[side];edge_idx[side]+=1
   x=(.096 if side==0 else W-.096);y=.024+.192*idx;layer='M4'
  assert 0<=x<=W and 0<=y<=H
  pins.append(dict(name=n,layer=layer,x=round(x,6),y=round(y,6)))
assert len(pins)==5986 and raw_idx==2200
assert len({(p['layer'],p['x'],p['y'])for p in pins})==len(pins)
dump('native_pins.json',pins)
# Macro source paths are expectations, not actual newmapped native names.
mac=[]
for line in TCL.read_text().splitlines():
 m=re.search(r'\{(m[01]\.g_bank.*?)\}\s+(ot_sram\S+)\s+([\d.]+)\s+([\d.]+)\s+(R0)',line)
 if m:
  name,master,x,y,orient=m.groups();name=name.replace('\\','');x=float(x);y=float(y)
  mac.append(dict(name='u_store.'+name,master=master,rect_um=[x,y,x+172.824,y+41.064],orient=orient))
assert len(mac)==32
dump('core_macros.json',dict(schema='opentallas.core_macros.v1',cores={MOD:dict(status='KNOWN',basis='EXPLICIT_SOURCE_ONLY_REFERENCE_FROM_ACTUAL_PRIOR_GUTTER_RECTS_NOT_NEWMAPPED_NAMES_OR_PLACEMENT',macros=mac)}))
plan=json.loads((ORIG/'GEN_plan.json').read_text());dump('GEN_plan.json',plan)
view=MOD+'@'+sha(R/'native_pins.json')[:12]
dump('views.json',dict(schema='opentallas.hbm_arch.views.v1',plan='GEN_plan.json',plan_sha256=sha(R/'GEN_plan.json'),view_list=[dict(view=view,module=MOD,outline_um=[W,H],pins_file='native_pins.json',pins_sha256=sha(R/'native_pins.json'),pins=5986,recipe_keys=[MOD],family='SOURCE13_REGIONAL_STOREA_PROPOSAL',canonical_type=None,instances=['UNADOPTED_B113_SOURCE_EVENT'],placed=0)]))
files=['ot_hnx_sfu_store_a_regional4_captured.sv','ot_hnx_sfu_store_a_regional4.sv','ot_hgi_sfu_store_a_regional_capture.sv','ot_hgi_su_lgroup2_regional_write.sv','ot_hgi_su_lbank.sv','ot_sram_1r1w_256x256_m2_r2c2_bb.v']
# Paths relative to repository, committed into the candidate source readset.
base='results/'+R.name
dump('native_readset.json',dict(top=MOD,files=[dict(file=base+'/'+f,sha256=sha(R/f))for f in files],pins_sha256=sha(R/'native_pins.json'),plan_sha256=sha(R/'GEN_plan.json'),core_macros_sha256=sha(R/'core_macros.json'),ABI=5986,native_SRAMs=32,source_only=True,component_reset_cycles=4,physical_release=False))
# Simultaneous prototype row capacity for the NEW copy cells only. Not mapping.
rows=[];w,h=1.404,.27
for region in range(4):
 x0=118.8 if region%2==0 else 481.68;y0=112.59 if region//2==0 else 319.95
 for i in range(2200):
  x=x0+2.16*(i%72);y=y0+.27*(i//72)
  assert all(x+w<=m['rect_um'][0]-4.32 or x>=m['rect_um'][2]+4.32 or y+h<=m['rect_um'][1]-4.32 or y>=m['rect_um'][3]+4.32 for m in mac)
  rows.append(dict(region=region,logical_index=i,x_um=round(x,6),y_um=round(y,6),width_um=w,height_um=h))
with(R/'capture_capacity_rows.csv').open('w')as f:
 c=csv.DictWriter(f,fieldnames=list(rows[0]));c.writeheader();c.writerows(rows)
dump('native_intake_model.json',dict(status='SOURCE_ONLY_GEN_PREP_NOT_DISPATCHED',macro_count=32,ABI=5986,outline_um=[W,H],new_capture_declared_FF=8800,old_native_mapped_FF_context=2914,new_expected_clock_FF_context=11714,all_clockloads_unmeasured=True,physical_reset_inputs=['store0_rst_n','capture_ctl_reset_n','capture_meta_reset_n'],raw_M4_pin_array='actual shapes clear centralmacro bodies; halo/access/upstream source join NOTqualified',capture_capacity=dict(model_cell=[w,h],cells=len(rows),simultaneous_overlap=0,macro_halo4_32_hits=0,native_mapped_cells=False,original_logic_readcapture_unplaced=True),logical_input_bits_per_cycle=2048,max_noncolliding_StoreA_write_bytes_per_cycle=128,throughput_qualification='unchanged selected write topology, no new runtime/production pass or gain',resource_proposal=dict(memory_GB=16,threads=2,disk_GB=5,basis='originalStoreA actual12GB sourceproof class +8800sameedgeFF; normal admission, no arbitrary timeout'),clock_reference_ps=dict(TT=250,FF=202.5),uncertainty_ps=dict(setup=0,hold=25),physical_release=False))
