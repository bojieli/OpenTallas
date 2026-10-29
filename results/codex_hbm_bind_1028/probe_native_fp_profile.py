"""Actual native KIND0/1 helper hierarchy KEEP/LAT and source-choice census.
Usage: probe_native_fp_profile.py SOURCE_BASE PROFILE_MANIFEST OUT
This is a two-leaf source vehicle, not numerical or physical sign-off.
"""
from pathlib import Path
import copy,json,sys
root,manifest,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(root/'tools/die_plan'))
import bind_elab as E
ab=json.loads(manifest.read_text())
top=out/'probe.sv';top.write_text('module hbm_fp_probe;\n'+''.join(
 'ot_hnx_su_pinreg_noside #(.KIND(%d),.MLAT(4),.ALAT(4),.LEAF(1),.LN(7),.FETCH_EXTRA_EDGES(2)) lane%d();\n'%(k,k)
 for k in (0,1))+'endmodule\n')
ab.update(top='hbm_fp_probe',netlist=[str(top)],
          dissolve=['ot_hnx_su_pinreg_noside','ot_hbm_su_static_lane_pinreg','ot_hbm_su_static_lane',
                    'ot_hdc_v41x_exp','ot_hdc_v41x_rsqrt','ot_hdc_qadd_lat','ot_hdc_qmul_lat'],
          release_full=['ot_hnx_su_pinreg_noside'])
records=[]
for label,disabled in [('add4_candidate',False),('disabled_flag_control',True)]:
 config=copy.deepcopy(ab)
 if disabled:config['defines']=[s for s in config.get('defines',[]) if s!='OT_HBM_NATIVE_F12_ADD4']
 d=out/label;E.elab(config,str(root),d,mem_gb=12)
 f=E.flatten(json.loads((d/'asbuilt.json').read_text()),'hbm_fp_probe',retain_hierarchy_ports=True)
 adds=[dict(path=n,**r['params']) for n,r in f.instances.items() if r['master']=='ot_hdc_qadd_lat']
 muls=[dict(path=n,**r['params']) for n,r in f.instances.items() if r['master']=='ot_hdc_qmul_lat']
 assert adds and muls
 assert all(int(a['KEEP'])==1 and int(a['LAT'])==4 for a in adds),adds
 assert all(int(m['LAT'])==4 for m in muls),muls
 add_leaves=[c.path for c in f.cells if c.module=='ot_hdc_fp32_add_f12_l4']
 legacy_leaves=[c.path for c in f.cells if c.module=='ot_hdc_fp32_add_lat4i']
 mul_leaves=[c.path for c in f.cells if c.module=='ot_hdc_fp32_mul_lat4']
 if disabled:assert not add_leaves and len(legacy_leaves)==len(adds)
 else:assert len(add_leaves)==len(adds) and not legacy_leaves
 assert len(mul_leaves)==len(muls)
 records.append(dict(label=label,actual_qadd_calls=adds,actual_qmul_calls=muls,
                     selected_add4_f12=len(add_leaves),selected_add4_legacy=len(legacy_leaves),
                     selected_mul4=len(mul_leaves),control_caught=disabled))
rec=dict(schema='opentallas.hbm.native_fp_actual_hierarchy.v1',records=records,
         added_data_cycles=0,status='SOURCE_HIERARCHY_ONLY_NUMERICAL_PROFILE_RECEIPT_SEPARATE',
         scope='Actual native KIND0/1 ALAT4 MLAT4 leaves; FULLSIDE remains absent. No KEEP0/LAT4 caller may inherit a four-edge claim.')
(out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
print('native actual hierarchy ADD4KEEP1→f12_l4; MUL4retained; disabled-flag control CAUGHT',flush=True)
