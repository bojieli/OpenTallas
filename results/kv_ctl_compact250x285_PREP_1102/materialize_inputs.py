"""Materialize an owned geometry successor plan; never alter source inputs or run EDA."""
from pathlib import Path
import json,gzip,sys,hashlib
packet=Path(sys.argv[1]);prod=Path(sys.argv[2]);out=Path(sys.argv[3]);assert not out.exists();out.mkdir(parents=True)
basis=json.load(open(packet/'actual_production_parent_basis.json'));assert hashlib.sha256((prod/'plan.json').read_bytes()).hexdigest()==basis['plan_sha256']
plan=json.load(open(prod/'plan.json'));c=plan['partition_types']['kv3_hub_C']['hard_cores'][1];assert c==basis['core']
delta=json.load(open(packet/'parent_delta_PREP.json'));pins=out/'kvs_ctl_compact250x285_pins.json';pins.write_bytes(gzip.decompress((packet/'candidate_parent_pins_PREP.json.gz').read_bytes()))
c.update(delta['new']);c['pins_file']=str(pins.resolve());c['note']='PREP current6849 native source; compact geometry and parentpin event, not selected or physicalqualified'
(plan_out:=out/'plan.json').write_text(json.dumps(plan,indent=1)+'\n')
receipt=dict(status='PREP_NOT_GEN',production_plan=str(prod/'plan.json'),production_plan_sha256=basis['plan_sha256'],candidate_plan=str(plan_out.resolve()),candidate_pin_file=str(pins.resolve()),source_RTL_changed=False,logical_ABI_delta_from_current_profile=0,cycles_delta_from_current_profile=0,GEN_requires_independent_geometry_review=True,source_core_json=str(prod/'core.json'),source_kit_rtl=str(prod/'kit_rtl'),source_lec_hint_plan=str(prod/'hint_plan.json'))
(out/'prep_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
