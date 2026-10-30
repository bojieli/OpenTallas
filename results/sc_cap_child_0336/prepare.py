from pathlib import Path
import json,shutil,hashlib,tarfile,gzip,sys
w=Path('/srv/opentallas-scratch2/claude/wt/codex-sc-cap-0336');b=Path('/srv/opentallas-scratch2/claude/codex-sc-cap-0336');o=w/'results/sc_cap_child_0336';s=o/'source';(s/'rtl').mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(w/'tools/die_plan'));import schema
K=Path('/srv/opentallas-scratch2/claude/codex-qc-kits-0336/gen/sle_sc_v2/sle_sc_v2/rtl');sources=['qfd_dv_s5_sc2_leaf.sv','qfd_dv_s5_sc2_k79.sv','qfd_dv_s5_sc2_k79_helpers.sv']
for n in sources:shutil.copy2(K/n,s/'rtl'/n)
(s/'.gitignore').write_text('/rtl/\n')
public={(q['bus'],q['bit']):q for q in json.load(open(b/'input/pins.json'))};interface=json.load(open(b/'input/port_interface.json'));dirs={p['name']:('in' if p['direction']=='input' else 'out') for p in interface['ports']};sizes={p['name']:p['bits'] for p in interface['ports']};origin=[345.6,656.64];W,H=253.2,505.44;pins=[]
def name(n,k):return n if sizes[n]==1 else f'{n}[{k}]'
def add(n,k,bus,bit,face,delta=0,role=None):
 q=public[bus,bit];x,y=q['x'],q['y']
 if face=='N':x=x+delta-origin[0];y=H
 elif face=='S':x-=origin[0];y=0
 elif face=='E':x=W;y=y+delta-origin[1]
 elif face=='W':x=0;y-=origin[1]
 pins.append(dict(name=name(n,k),bus=n,bit=k,dir=dirs[n],face=face,layer=q['layer'],x=round(x,6),y=round(y,6),parent_public=dict(bus=bus,bit=bit,x=q['x'],y=q['y'],layer=q['layer']),role=role or 'existing_source_bit'))
N=[('busy',0),('fault',0)]+[('tok_idx',k) for k in range(24)]+[('tok_own',0)]+[('tok_user',k) for k in range(2)]+[('tok_v',0)]+[('tok_val',k) for k in range(32)]+[('w1_addr',k) for k in range(24)]+[('w1_data',k) for k in range(32)]+[('w1_we',0)]
for bit,(n,k) in enumerate(N):add(n,k,'x_ctl_o',bit,'N',224.64,'N119 exact u_bout_x_ctl_o concatenation bit')
for k in range(48):add('up_o',k,'x_fe_o',k,'E',388.8,'E48 exact up_o, no parent epoch');add('dn_o',k,'x_fw_o',k,'W',0,'W48 exact dn_o, no parent epoch')
for n,start,count in [('am_idx',0,24),('am_u',24,2),('am_v',26,1),('am_val',27,32),('sc_cfg',59,101)]:
 for k in range(count):add(n,k,'x_ctl_i',start+k,'N',276.48,'existing CA read + boundary FF to child, parent placement unresolved')
for k in range(1,48):add('dn_i',k,'x_fe_i',k-1,'E',388.8,'existing x_fe_i_q input FF')
add('dn_i',0,'flt_fe_i',0,'E',457.92,'existing flt_fe_i_q input FF: direct proxy exceeds405, needs actual existing bin placement')
for k in range(48):add('up_i',k,'x_fw_i',k,'W',0,'existing CA read + boundary FF')
for n,start,count in [('red_addr',0,24),('red_data',24,32),('red_we',56,1)]:
 for k in range(count):add(n,k,'x_su_c_i',start+k,'S',0,'existing fixed6 + strap0..1 R8 pad chain unchanged')
for n,start,count in [('vm_win0',0,2),('vm_wdata0',2,32),('vm_we',34,4)]:
 for k in range(count):add(n,k,'x_su_l0_i',start+k,'E',-172.8,'existing pd8 chain unchanged')
for k in range(4,8):add('vm_we',k,'x_su_l1_i',k-4,'S',0,'existing pd6 chain unchanged')
for n,y,ln in [('ck',17.312,'M6'),('rst_n',19.224,'M4')]:pins.append(dict(name=n,bus=n,bit=0,dir='in',face='W',layer=ln,x=0.,y=y,role='existing source clock/reset, no semantic change'))
assert len(pins)==572 and len({p['name'] for p in pins})==572
expected={name(n,k) for n,c in sizes.items() for k in range(c)};assert expected=={p['name'] for p in pins}
tracks={'M4':(.048,.024),'M5':(.048,.024),'M6':(.064,.032),'M7':(.064,.032)};errors=[]
for p in pins:
 c=p['x'] if p['face'] in 'NS' else p['y'];pitch,off=tracks[p['layer']]
 if abs((c-off)/pitch-round((c-off)/pitch))>1e-5:errors.append([p['name'],'track',c])
 if schema.pg_blocked(p['layer'],c):errors.append([p['name'],'PG',c])
 if not(0<=p['x']<=W and 0<=p['y']<=H):errors.append([p['name'],'outline'])
assert not errors,errors[:8]
report={'scope':'CONDITIONAL CHILD source/pins only; no GEN/P&R/STA or parent activation','parent_body_um':[345.6,656.64,598.8,1162.08],'child_outline_um':[W,H],'pins':572,'inputs':357,'outputs':215,'track_and_PG_errors':errors,'source_bits_unchanged':True,'parent_epoch_bits_omitted':True,'output_map':{'N119':'w1_we/data/addr + tok_val/v/user/own/idx + fault/busy, exact concatenation bits0..118','E48':'up_o[47:0]→x_fe_o[47:0]','W48':'dn_o[47:0]→x_fw_o[47:0]'},'output_exact_per_bit_L1_um':{},'input_direct_public_proxies_not_delivery_clearance':{}}
for face,key in [('N','x_ctl_o'),('E','x_fe_o'),('W','x_fw_o')]:
 pp=[p for p in pins if p['dir']=='out' and p['face']==face];report['output_exact_per_bit_L1_um'][key]=max(abs(p['x']+origin[0]-p['parent_public']['x'])+abs(p['y']+origin[1]-p['parent_public']['y']) for p in pp)
for n in dirs:
 pp=[p for p in pins if p['bus']==n and p['dir']=='in' and 'parent_public' in p]
 if pp:report['input_direct_public_proxies_not_delivery_clearance'][n]=max(abs(p['x']+origin[0]-p['parent_public']['x'])+abs(p['y']+origin[1]-p['parent_public']['y']) for p in pp)
(o/'pins.json').write_text(json.dumps(dict(schema='opentallas.core_pins.v1',module='qfd_dv_s5_sc2_leaf',outline_um=[W,H],pins=pins),indent=2)+'\n');(o/'pin_model.json').write_text(json.dumps(report,indent=2)+'\n')
spec=dict(name='sc_cap_child_0336',top='qfd_dv_s5_sc2_leaf',kind='core',sources=['results/sc_cap_child_0336/source/rtl/'+n for n in sources],params={},defines=['SYNTHESIS'],clock_port='ck',reset_ports=['rst_n'],outline=dict(w=W,h=H),layer_cap='M7',route={'pd':.5},children=[],macros=[],note='Exact existing production source LA7/LM9, no reset/RTL/state/data-cycle patch; internal629 async-reset0 helper flops retained. Conditional child plan only.')
(s/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
plan=dict(schema='opentallas.die_plan.v1',die=dict(name='sc_cap_child_conditional',period_ps=833),clock=dict(insertion_ps=250,insertion_ff_ps=202.5,insertion_tol_ps=40),partition_types={'sc_cap_child_holder':dict(module='sc_cap_child_holder',outline_um=[W,H],hard_cores=[dict(inst='u_core',module='qfd_dv_s5_sc2_leaf',origin_um=[0,0],outline_um=[W,H],pins_file='pins.json')])},note='Standalone child generation input only; NOT parent source activation; nominal IO frames are not measured child timing')
(o/'child_plan.json').write_text(json.dumps(plan,indent=2)+'\n');(o/'recipes.json').write_text(json.dumps({'qfd_dv_s5_sc2_leaf':dict(ref_tile='results/sc_cap_child_0336/source',plan_type='sc_cap_child_holder',plan_pins_contract=True,suffix='sc_cap0336',util=.5,orfs_vars={'MAX_ROUTING_LAYER':'M7'},note='Conditional source/pin prep only; root/GEOM review before native physical launch; no RTL patches')},indent=2)+'\n')
with (o/'source_bundle.tar.gz').open('wb') as raw:
 with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
  with tarfile.open(fileobj=gz,mode='w') as tar:
   for n in sources:
    p=s/'rtl'/n;ti=tarfile.TarInfo('results/sc_cap_child_0336/source/rtl/'+n);ti.size=p.stat().st_size;ti.mode=0o644;ti.mtime=0
    with p.open('rb') as f:tar.addfile(ti,f)
(o/'source_manifest.json').write_text(json.dumps(dict(files={n:hashlib.sha256((s/'rtl'/n).read_bytes()).hexdigest() for n in sources},source_bundle_sha256=hashlib.sha256((o/'source_bundle.tar.gz').read_bytes()).hexdigest(),all_source_bytes_identical_to_original_native_SC=True,added_state_or_data_cycles=0),indent=2)+'\n')
print(json.dumps(report,indent=2))
