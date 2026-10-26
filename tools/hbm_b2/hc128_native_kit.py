#!/usr/bin/env python3
"""Stage an exact W128 HC master with the shared current HBM M5 kit generator.

Example: hc128_native_kit.py --masters /.../masters_drst --view MODULE@SHA12 --out KITROOT
All normal kit arguments pass through; this candidate adds zero face cycles.
"""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
ap=argparse.ArgumentParser(add_help=False);ap.add_argument('--masters',type=Path,required=True);ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2]);a,rest=ap.parse_known_args();a.repo=a.repo.resolve();cfg=a.repo/'physical/die_plan/hbm_arch_cores/native128';views=json.loads((cfg/'views.json').read_text());recipes={};overrides={};receipts={}
for view in views['view_list']:
 mod=view['module'];sv=a.masters/(mod+'.sv');receipt=json.loads((a.masters/(mod+'_receipt.json')).read_text());assert hashlib.sha256(sv.read_bytes()).hexdigest()==receipt['verilog_sha256'],mod;receipts[mod]=receipt
 virtual='native_hc128/'+mod+'.sv';overrides[virtual]=str(sv.resolve());rec=dict(top=mod,files=[virtual],params={},defines=[],source_commit=receipt['source_commit'],source='Current exact native W128 cut; complete emitted module closure; zero face-shell cycles',macros=[])
 if 'pair' in mod:
  rec.update(macros=['ot_sram_1r1w_1024x256_m2_r2c2','ot_sram_1r1w_128x256_m1_r2c2'],macro_place_halo_um=4.32,macro_placement=[dict(inst='u_c.u_b.g_w\\[1\\].u_m',macro='ot_sram_1r1w_1024x256_m2_r2c2',xy_um=[21.6,4.32],orient='R180'),dict(inst='u_c.u_b.g_x\\[0\\].u_m',macro='ot_sram_1r1w_128x256_m1_r2c2',xy_um=[21.6,129.6],orient='MY'),dict(inst='u_c.u_b.g_w\\[0\\].u_m',macro='ot_sram_1r1w_1024x256_m2_r2c2',xy_um=[21.6,179.28],orient='MY')])
 recipes[mod]=rec
if '--view' not in rest:raise SystemExit('--view required; see native128/views.json')
selected=next(v for v in views['view_list'] if v['view']==rest[rest.index('--view')+1]);mod=selected['module'];receipt=receipts[mod]
for name,want in [('--face-shell','off'),('--sigmax','M5')]:
 if name in rest and rest[rest.index(name)+1]!=want:raise SystemExit(name+' must be '+want+' for this native HC candidate')
 if name not in rest:rest.extend([name,want])
if '--views' not in rest:rest.extend(['--views',str(cfg/'views.json')])
if '--core-insertion' not in rest:rest.extend(['--core-insertion','none'])
# A single real clock port; dense local clock taps are built by the shared flow.
if '--clock-taps' not in rest:rest.extend(['--clock-taps','density'])
source_file='native_hc128/'+mod+'.sv';profile=dict(source_commit=receipt['source_commit'],family='HC_W128_NATIVE',added_face_cycles=0,qualification='UNROUTED_CANDIDATE',clock_ports=['clk'],reset_ports=['rst_n'],module_closure_receipt=receipt,port_inventory=dict(top=mod,source_file=source_file,source_sha256=receipt['verilog_sha256'],ports=[(n,*v) for n,v in receipt['ports'].items()]))
p=a.repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py';spec=importlib.util.spec_from_file_location('hc128_shared_kit',p);gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen);sys.argv=[str(p),*rest];gen.main(recipe_overrides=recipes,source_overrides=overrides,source_profile=profile)
