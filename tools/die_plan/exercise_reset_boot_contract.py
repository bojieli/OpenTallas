"""Small static witness on actual published before/after wavefront and plan."""
import argparse,copy,hashlib,json
from pathlib import Path
from reset_boot_contract import compile_contract,check_binding,adopt_contract


def main():
 p=argparse.ArgumentParser()
 for n in ('plan','before','after','delta','contract','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();load=lambda path:json.loads(path.read_text())
 plan,before,after,delta=[load(getattr(a,n))for n in ('plan','before','after','delta')]
 contract=compile_contract(plan,before,after,delta);assert contract==load(a.contract)
 ref=dict(file=str(a.contract.resolve()),sha256=hashlib.sha256(a.contract.read_bytes()).hexdigest())
 plan,manifest=adopt_contract(plan,{},ref);plan['asbuilt']=manifest
 assert check_binding(plan,a.contract.parent)==contract
 caught=[]
 def negative(name,fn):
  try:fn()
  except ValueError:caught.append(name)
  else:raise AssertionError(name+' escaped')
 stale=copy.deepcopy(delta);stale['changed_parts']={}
 negative('unchanged_global_max_cannot_hide_local_BOOT_delta',lambda:compile_contract(plan,before,after,stale))
 old=copy.deepcopy(plan);old['partitions'][0]['origin_um'][0]+=.054
 negative('stale_selected_physical_plan',lambda:check_binding(old,a.contract.parent))
 missing=copy.deepcopy(plan);missing['asbuilt']={}
 negative('plan_only_without_current_manifest_adoption',lambda:check_binding(missing,a.contract.parent))
 corrupt=copy.deepcopy(plan);corrupt['reset_boot_contract']['sha256']='0'*64;corrupt['asbuilt']=dict(reset_boot_contract=corrupt['reset_boot_contract'])
 negative('changed_contract_payload',lambda:check_binding(corrupt,a.contract.parent))
 result=dict(status='PASS',parts=len(contract['parts']),changed_parts=contract['changed_parts'],negative_controls_caught=caught,
     baseline_max_release=contract['baseline_max_release'],final_max_release=contract['final_max_release'],start_mode=contract['start_mode'],
     added_production_cycles=contract['added_production_cycles'],note='compiler authority remains incomplete; actual reset-only plan has no START propagation')
 a.out.write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
