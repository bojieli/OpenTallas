import sys,os,json,copy
from pathlib import Path
sys.path.insert(0,'tools');sys.path.insert(0,'tools/qwen_layerbench')
import dv_lower as D,dv_lower_mat as M
p=Path('results/rtl/qc_mat_native_1116/mat_ages.json');a=M.load_ages(p);r={}
old=os.environ['DV_LOWER_VFLAGS'];os.environ['DV_LOWER_VFLAGS']='-DOT_QC_SRAM_MIF -DOT_S8_CROM_ALIGN'
try:M.load_ages(p)
except M.LowerError as e:r['missing_selected_source_flag']='CAUGHT: '+str(e)
else:raise AssertionError('feature guard missed')
os.environ['DV_LOWER_VFLAGS']=old
bad=copy.deepcopy(a);bad['stn_lead']['down']=23
try:M.lower_matvec('down',1000,bad,M.Chain(D.slice_map()))
except M.LowerError as e:r['legacy20_pin_lead']='CAUGHT: '+str(e)
else:raise AssertionError('late-gap guard missed')
legacy='results/rtl/qlb_c4b_1018/dv_lower_mat/stn_ages.json'
M.load_ages(legacy);r['legacy_untagged_profile']='PASS original26/2 retained'
Path('results/rtl/qc_mat_native_1116/guards.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
