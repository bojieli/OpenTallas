"""Fresh source-only vL kit; never reuse a physical DB or a LEC receipt."""
from pathlib import Path
import shutil,json,hashlib,sys,datetime
base=Path(sys.argv[1]); dst=Path(sys.argv[2]); src=Path(sys.argv[3])
assert not dst.exists(),dst
assert hashlib.sha256((base/'rtl/qkd_hr_core_prompt.v').read_bytes()).hexdigest()=='3051cee57cc069b1b46f911ba2ea05e459346a021ce19847ff92eebe6fa417d2'
assert hashlib.sha256(src.read_bytes()).hexdigest()=='088e078f15cce944bd4f321f62e5faece692e40599f248fd58bdbe12a711ef2b'
dst.mkdir(parents=True)
inputs={'CHANNEL_REDESIGN.json','hr_ft_regs.json','PIN_CYCLES.json','hr_face_delta.json','hr_dead_inputs_proof.json','freeze.json','lec_hints.json','clock_binding.json','pins.json','core.json','dead_inputs.json','reset_contract.json','boundary_guard_context.json','timed_face.json','pins_added.json'}
for f in base.iterdir():
 if f.is_file() and (f.name in inputs or f.suffix in {'.sh','.tcl','.py','.mk','.sdc'}):shutil.copy2(f,dst/f.name)
for d in ['rtl','macros','reset_contract']:shutil.copytree(base/d,dst/d,symlinks=True)
shutil.copy2(src,dst/'rtl/qkd_hr_core_prompt.v')
with (dst/'config.mk').open('a') as f:f.write('\n# vL genuine DEPTH form: carry-prediction3FF, zeroPINcycle change.\n# Inputs-only hold repair; R2O+macro paths retained, fullFF SDC restored.\noverride export OT_HOLD_REPAIR_SCOPE = nonport\n')
# Use the current successful routed-proof engine; hint candidates remain untrusted and proved.
lec=base.parent.parent/'tools_branch/tools/die_plan/lec.py'
shutil.copy2(lec,dst/'lec.py')
# The original source-freeze contract is preserved as inherited data; the private source override is explicit.
rec={'schema':'opentallas.private_form_source.v1','variant':'vL','source_branch':'codex/kv-prompt-channel-1107','source_commit':'41fd4204028','base_kit':str(base),'base_rtl_sha256':'3051cee57cc069b1b46f911ba2ea05e459346a021ce19847ff92eebe6fa417d2','rtl_sha256':'088e078f15cce944bd4f321f62e5faece692e40599f248fd58bdbe12a711ef2b','class':'DEPTH','lec_tool_sha256':hashlib.sha256(lec.read_bytes()).hexdigest(),'new_flops':3,'new_pin_cycles':0,'no_physical_checkpoint_reused':True,'no_lec_receipt_reused':True,'inherited_freeze':'freeze.json unmodified; source override explicit in this record','created':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(dst/'PRIVATE_FORM_SOURCE.json').write_text(json.dumps(rec,indent=2)+'\n')
print(json.dumps(rec))
