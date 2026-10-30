import copy,json,sys,tempfile,shutil
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/codex-ds-math-intake-1030');T=Path('/srv/opentallas-scratch2/claude/wt/codex-ds-native-exec-1029');C=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-event3-1030')
sys.path[:0]=[str(R/'code'),str(C/'code'),str(C/'code/layer_prog'),str(T/'tools/s81_dv'),str(T/'tools/die_plan'),str(T/'tools')]
from layer_prog.norm_math_intake import attach_math
entry=json.loads((C/'L14/entry_inputs.json').read_text());programme=json.loads((C/'L14/norm_control.json').read_text())
source=Path('/srv/opentallas-scratch2/claude/codex-s81-h2-bind-2249/frozen_source')
actual=attach_math(entry,programme,R/'chain',source)
assert actual['actual_BF16_elements']==5120 and actual['actual_rstd32']=='40ca3c85'and actual['native_programme_qualified']is False
controls={}
def reject(name,fn):
 try:fn()
 except ValueError as exc:controls[name]=str(exc)
 else:raise ValueError('current math intake control escaped '+name)
bad=copy.deepcopy(entry);bad['writes'][0]['data128']=f"{int(bad['writes'][0]['data128'],16)^1:032x}"
reject('changed_actual_entry_word',lambda:attach_math(bad,programme,R/'chain',source))
with tempfile.TemporaryDirectory(prefix='norm_intake_',dir=R)as tmp:
 p=Path(tmp);shutil.copytree(R/'chain',p/'chain')
 receipt=p/'chain/xf/receipt.json';r=json.loads(receipt.read_text());del r['source_sha256']['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv'];receipt.write_text(json.dumps(r))
 reject('selectively_missing_VN_dependency',lambda:attach_math(entry,programme,p/'chain',source))
with tempfile.TemporaryDirectory(prefix='norm_top_bridge_',dir=R)as tmp:
 p=Path(tmp);shutil.copytree(R/'chain',p/'chain')
 receipt=p/'chain/producer/native_params.json';r=json.loads(receipt.read_text());row=r['leaves'][0];other=r['leaves'][1]
 for key in('native_file','native_sha256','native_master'):row[key]=other[key]
 receipt.write_text(json.dumps(r))
 reject('self_consistent_wrong_native_part_file',lambda:attach_math(entry,programme,p/'chain',source))
result=dict(status='PASS_ACTUAL_COMPILER_MATH_CHAIN_INTAKE',math_component_contract=actual,controls_caught=controls,
 native_PDSK_GO_global_dates_adopted=False,full_token=False)
(R/'receipt.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],'5120BF16/current116+17,3controls,no nativeadmission')
