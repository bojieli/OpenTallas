#!/usr/bin/env python3
"""Own bank128 write-face safe-form kit; no changes to running kits."""
import sys,json,hashlib,importlib.util,os,argparse,subprocess
from pathlib import Path
repo=Path(__file__).resolve().parents[4]
a=argparse.ArgumentParser();a.add_argument('--context',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--write-face',choices=['on','off'],default='on');a=a.parse_args();ctx=a.context;out=a.out
commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
module='ot_hbm_hc_bank128_pair_core'
base=json.loads((ctx/'base_freeze.json').read_text()); src=repo/'rtl/hbm_accel/cores_split/ot_hbm_hc_native128'/f'{module}.sv'
sys.path.insert(0,str(repo/'tools/hbm_b2'));from hc_alpha_names import normalize_names,placement_name
text,alpha=normalize_names(src.read_text(),module); ap=ctx/(module+'.sv');ap.write_text(text)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
view={k:base[k] for k in ('view','module','outline_um','pins_file','pins_sha256','pins')};view['recipe_keys']=[module];view['instances']=['diagnostic native pair'];view['placed']=112
(ctx/'views.json').write_text(json.dumps(dict(schema='opentallas.hbm_arch.core_views.v1',plan=str(ctx/'die_plan.json'),view_list=[view]),indent=1)+'\n')
virtual='native_hc128/'+module+'.sv'
rec=dict(top=module,files=[virtual],params={},defines=['OT_HC128_WFACE'] if a.write_face=='on' else [],source_commit=commit,source='Bank128 opt-in525bit write face +1edge; exact SRAM-boundary proof',util=.40,macros=['ot_sram_1r1w_1024x256_m2_r2c2','ot_sram_1r1w_128x256_m1_r2c2'],macro_place_halo_um=4.32,macro_placement=[dict(inst='u_c.u_b.g_w\\[1\\].u_m',macro='ot_sram_1r1w_1024x256_m2_r2c2',xy_um=[38.88,4.332],orient='R180'),dict(inst='u_c.u_b.g_x\\[0\\].u_m',macro='ot_sram_1r1w_128x256_m1_r2c2',xy_um=[21.6,96.252 if a.write_face=='on' else 108.012],orient='MY'),dict(inst='u_c.u_b.g_w\\[0\\].u_m',macro='ot_sram_1r1w_1024x256_m2_r2c2',xy_um=[38.88,158.748],orient='MY')])
for row in rec['macro_placement']:row['inst']=placement_name(row['inst'],alpha)
profile=dict(base['source_profile']);profile.update(source_commit=commit,family='HC_W128_NATIVE_WFACE',added_face_cycles=int(a.write_face=='on'),qualification='EXACT_WRITE_CUT_UNROUTED',diagnostic_inputs=True)
profile['module_closure_receipt']=dict(profile['module_closure_receipt'],source_commit=commit,verilog_sha256=sha(ap),added_cycles=int(a.write_face=='on'),qualification='WRITE_FACE_BOUNDARY_PROVED_UNROUTED')
profile['port_inventory']=dict(top=module,source_file=virtual,source_sha256=sha(ap),ports=[(n,*v) for n,v in base['source_profile']['module_closure_receipt']['ports'].items()])
profile['write_face']=dict(define='OT_HC128_WFACE',cycles=1,cohort=['write_data','write_addr','weight_we0','weight_we1','x_write'],arithmetic_cycles=0,precondition='no programming during reset; firstdependentread/go shifted1edge')
sys.path.insert(0,str(repo/'physical/die_plan/hbm_arch_cores'))
p=repo/'physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py';spec=importlib.util.spec_from_file_location('b128_gen',p);gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)
sys.argv=[str(p),'--views',str(ctx/'views.json'),'--view',view['view'],'--out',str(out),'--tag','_wface_vB' if a.write_face=='on' else '_shallow_vA','--util','.40','--sigmax','M6','--face-shell','off','--clock-pin-entry','on','--clock-taps','off','--single-root-taps','off','--core-insertion','none','--core-macros','off']
if a.write_face=='on':
 guide=ctx/'write_face_guide.json';guide.write_text(json.dumps(dict(boxes=[dict(name='write_ingress_north',prefixes=['wface_data','wface_addr','wface_we0','wface_we1','wface_xwe'],box_um=[4.32,237.6,246.24,263.52])]),indent=1)+'\n');sys.argv.extend(['--reg-guide-boxes',str(guide)])
gen.main(recipe_overrides={module:rec},source_overrides={virtual:str(ap)},source_profile=profile)
