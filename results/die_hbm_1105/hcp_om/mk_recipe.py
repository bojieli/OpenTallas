import json,subprocess
t=subprocess.check_output(['git','show','origin/main:physical/die_plan/hbm/cores/harden/recipes_split.json'])
v=json.loads(t)['ot_hbm_hc_root_static__hcp_sys1__155.52x172.8']; v=dict(v)
v['files']=['rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_fp32_mul_lat.sv','rtl/hdc/ot_hdc_prefix.sv']+v['files']
f='physical/die_plan/hbm_arch_cores/recipes_b2.json'; d=json.load(open(f)); d['ot_hbm_hc_root_static__hcp_sys1']=v
open(f,'w').write(json.dumps(d,indent=1)+'\n')
print(v.get('top'),len(v['files']))
