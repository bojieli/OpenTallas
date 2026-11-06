#!/usr/bin/env python3
"""Stage an exact W128 HC master (default M5; optional reviewed common-pair M6 form).

Example: hc128_native_kit.py --masters /.../masters_drst --view MODULE@SHA12 --out KITROOT
All normal kit arguments pass through; this candidate adds zero face cycles.
"""
import argparse,hashlib,importlib.util,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hc_alpha_names import normalize_names, placement_name
ap=argparse.ArgumentParser(add_help=False);ap.add_argument('--masters',type=Path,required=True);ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2]);ap.add_argument('--diagnostic-plan',action='store_true');ap.add_argument('--b128-safe',action='store_true',help='opt-in common-pair M6, single-root CTS and balanced SRAM channels; parent must reserve M6');ap.add_argument('--write-face',action='store_true',help='opt-in grouped common-pair write pipeline; requires updated master and native projection +1 write guard');ap.add_argument('--pg6',action='store_true',help='opt-in real M6 PG rails/vias; requires M6 reservation and parent M7 landing');a,rest=ap.parse_known_args();a.b128_safe=a.b128_safe or a.write_face or a.pg6;a.repo=a.repo.resolve();cfg=a.repo/'physical/die_plan/hbm_arch_cores/native128';views=json.loads((cfg/'views.json').read_text());recipes={};overrides={};receipts={}
if '--out' not in rest:raise SystemExit('--out required')
alpha_dir=Path(rest[rest.index('--out')+1]).resolve()/'_hc128_alpha';alpha_dir.mkdir(parents=True,exist_ok=True)
for view in views['view_list']:
 mod=view['module'];original=a.masters/(mod+'.sv');receipt=json.loads((a.masters/(mod+'_receipt.json')).read_text());assert hashlib.sha256(original.read_bytes()).hexdigest()==receipt['verilog_sha256'],mod
 raw=original.read_text()
 if a.write_face and mod=='ot_hbm_hc_bank128_pair_core' and 'OT_HC128_WFACE' not in raw:raise SystemExit('write-face requires a current common-pair master with OT_HC128_WFACE')
 text,alpha=normalize_names(raw,mod);sv=alpha_dir/(mod+'.sv');tmp=sv.with_suffix('.'+str(os.getpid())+'.tmp');tmp.write_text(text);os.replace(tmp,sv)
 receipt=dict(receipt,original_verilog_sha256=receipt['verilog_sha256'],verilog_sha256=hashlib.sha256(sv.read_bytes()).hexdigest(),identifier_alpha=alpha);receipts[mod]=receipt
 virtual='native_hc128/'+mod+'.sv';overrides[virtual]=str(sv.resolve());rec=dict(top=mod,files=[virtual],params={},defines=[],source_commit=receipt['source_commit'],source='Current exact native W128 cut; complete emitted module closure; zero face-shell cycles',macros=[])
 if 'pair' in mod:
  # One M5 PDN pitch lower leaves 4.296 um between X/W0 halos; y=129.6 overlaps by 0.024 um.
  rec.update(macros=['ot_sram_1r1w_1024x256_m2_r2c2','ot_sram_1r1w_128x256_m1_r2c2'],macro_place_halo_um=4.32,macro_placement=[dict(inst='u_c.u_b.g_w\\[1\\].u_m',macro='ot_sram_1r1w_1024x256_m2_r2c2',xy_um=[21.6,4.32],orient='R180'),dict(inst='u_c.u_b.g_x\\[0\\].u_m',macro='ot_sram_1r1w_128x256_m1_r2c2',xy_um=[21.6,125.28],orient='MY'),dict(inst='u_c.u_b.g_w\\[0\\].u_m',macro='ot_sram_1r1w_1024x256_m2_r2c2',xy_um=[21.6,179.28],orient='MY')])
 if a.b128_safe and mod=='ot_hbm_hc_bank128_pair_core':
  # Same outline/pins. Reviewed source form; production --core-macros auto
  # must get these sites from the adopted parent plan event.
  rec['macro_placement'][0]['xy_um']=[38.88,4.332]
  rec['macro_placement'][1]['xy_um']=[21.6,96.252]
  rec['macro_placement'][2]['xy_um']=[38.88,158.748]
  if a.write_face:rec['defines'].append('OT_HC128_WFACE')
 for item in rec.get('macro_placement',[]):item['inst']=placement_name(item['inst'],alpha)
 recipes[mod]=rec
if '--view' not in rest:raise SystemExit('--view required; see native128/views.json')
vid=rest[rest.index('--view')+1];selected=next((v for v in views['view_list'] if v['view']==vid),None)
# HBM-CORES-R8 10-27: a composed-plan view (--views of a later plan, e.g. planU6b) keeps the module/master but has its own
# pin table (re-placed pins): select the master by module.  The shared generator still checks those plan pins against the
# exact emitted ports (PORT_MISMATCH otherwise).
if selected is None and '--views' in rest:selected=next((v for v in json.loads(Path(rest[rest.index('--views')+1]).read_text())['view_list'] if v['view']==vid and v['module'] in receipts),None)
if selected is None:raise SystemExit('view '+vid+' is not a native W128 HC view')
mod=selected['module'];receipt=receipts[mod]
if a.b128_safe and mod!='ot_hbm_hc_bank128_pair_core':raise SystemExit('--b128-safe/--write-face applies only to the common pair, never the already-closed first/subtree')
for name,want in [('--face-shell','off'),('--sigmax','M6' if a.b128_safe else 'M5')]:
 if name in rest and rest[rest.index(name)+1]!=want:raise SystemExit(name+' must be '+want+' for this native HC candidate')
 if name not in rest:rest.extend([name,want])
if a.pg6:
 if '--pg-top-layer' in rest and rest[rest.index('--pg-top-layer')+1]!='M6':raise SystemExit('--pg6 requires --pg-top-layer M6')
 if '--pg-top-layer' not in rest:rest.extend(['--pg-top-layer','M6'])
if '--views' not in rest:rest.extend(['--views',str(cfg/'views.json')])
if '--core-insertion' not in rest:rest.extend(['--core-insertion','none'])
# A single real clock port; dense local clock taps are built by the shared flow.
if '--clock-taps' not in rest:rest.extend(['--clock-taps','off' if a.b128_safe else 'density'])
if a.b128_safe:
 for name,want in [('--clock-pin-entry','on'),('--single-root-taps','off'),('--util','.45')]:
  if name not in rest:rest.extend([name,want])
source_file='native_hc128/'+mod+'.sv';profile=dict(source_commit=receipt['source_commit'],family='HC_W128_NATIVE',endpoint_contract=dict(kind='INTERNAL_CORE',partition_rule='R2_INTERNAL_TIMED_IN_PARTITION',parent_partition='q_bXXX',source='tools/die_plan/README.md R2'),added_face_cycles=0,qualification='UNROUTED_CANDIDATE',clock_ports=['clk'],reset_ports=['rst_n'],module_closure_receipt=receipt,port_inventory=dict(top=mod,source_file=source_file,source_sha256=receipt['verilog_sha256'],ports=[(n,*v) for n,v in receipt['ports'].items()]))
# A write pipeline is not a uniform face-shell delay: read/go/arithmetic stay
# native, while the projection compiler defers first dependent read/go one edge.
if a.b128_safe:profile['physical_form']='B128_M6_SINGLE_ROOT_BALANCED_CHANNELS'
if a.pg6:profile['pg_access']='REAL_PG6_PARENT_M7_RESERVATION_AND_FINAL_ACCESS_PENDING'
if a.write_face:
 profile['added_write_cycles']=1
 profile['pin_cycle_delta']={p:1 for p in ['write_data','write_addr','weight_we0','weight_we1','x_write']}
 profile['qualification']='EXACT_PROGRAMMING_BOUNDARY_PROVED_PARENT_PENDING'
 profile['write_contract']='physical/die_plan/hbm_arch_cores/bank128_wface/contract.json'
 if '--reg-guide-boxes' not in rest:
  vp=Path(rest[rest.index('--views')+1]);vi=json.loads(vp.read_text());pp=Path(vi['plan']);pp=pp if pp.is_absolute() else vp.resolve().parent/pp
  pin_table=json.loads((pp.resolve().parent/selected['pins_file']).read_text())
  east=next(p for p in pin_table if p['name']=='weight_we0')['x']>selected['outline_um'][0]-1
  # Direct data/address flops are already FIRM at their faces. Guide only
  # the reset-gated enables that the face hook leaves movable.
  control=['wface_we0','wface_we1','wface_xwe']
  boxes=[dict(name='write_enable_east' if east else 'write_enable_north',prefixes=control,box_um=[226.8,43.2,246.24,86.4] if east else [4.32,237.6,246.24,263.52])]
  guide=alpha_dir/'write_face_guide.json';guide.write_text(json.dumps(dict(boxes=boxes),indent=1)+'\n');rest.extend(['--reg-guide-boxes',str(guide)])

# HBM-CORES-R8 10-27: --diagnostic-plan (as q3sync_kits/build_kit.py) admits an external scratch plan (trial kit, not release evidence)
if a.diagnostic_plan:profile['diagnostic_inputs']=True
# DIE-HBM-54 10-31: the shared generator imports its sibling modules (static_id_contracts, face_shell, ...) by name
sys.path.insert(0,str(a.repo/'physical/die_plan/hbm_arch_cores'))
p=a.repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py';spec=importlib.util.spec_from_file_location('hc128_shared_kit',p);gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)
# DIE-HBM-54 10-31: --core-macros auto (autopilot default) takes the plan core_macros.json rects; their names are the
# emitted flat SRAM cell names, which the alpha step renamed -> translate them with the same report (rects unchanged).
_cmp=gen.core_macros_placement
def _cmp_alpha(cm_path,module,macros):
 r=_cmp(cm_path,module,macros)
 if r and module in receipts:
  for row in r[0]:row['inst']=placement_name(row['inst'],receipts[module]['identifier_alpha'])
 return r
gen.core_macros_placement=_cmp_alpha
sys.argv=[str(p),*rest];gen.main(recipe_overrides=recipes,source_overrides=overrides,source_profile=profile)
