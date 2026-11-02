from pathlib import Path
import hashlib,importlib.util,json,shutil
root=Path('/srv/opentallas-scratch2/claude/codex-kv-ahub-fault-full-2055')
spec=importlib.util.spec_from_file_location('fg',root/'ahub_fault_groups.py');fg=importlib.util.module_from_spec(spec);spec.loader.exec_module(fg)
src=root/'base/rtl/qkd_ahub_static_dw.sv';original=src.read_text();candidate=fg.factor_fault_capture(original,'qkd_ahub_static_core_la_ck7')
# Full-source negative control suppresses one real 16-bit capture group. All
# other production source files, parameter values, clocks and resets are kept.
mutant=candidate.replace('gqv_groups[5+4*fg_a+fg_s] <= (|issue) &&','gqv_groups[5+4*fg_a+fg_s] <= (fg_a==3 && fg_s==3) ? 1\'b0 : (|issue) &&',1)
assert candidate!=mutant
packets={}
for name,text in [('normal',candidate),('mutant',mutant)]:
 target=root/name;shutil.copytree(root/'base',target)
 (target/'rtl/qkd_ahub_static_dw.sv').write_text(text)
 packets[name]={'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'kit_readset':{str(p.relative_to(target/'rtl')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((target/'rtl').glob('*')) if p.is_file()}}
packets['baseline_sha256']=hashlib.sha256(original.encode()).hexdigest();packets['reference_netlist_sha256']=hashlib.sha256((root/'reference.v').read_bytes()).hexdigest();packets['helper_sha256']=hashlib.sha256((root/'ahub_fault_groups.py').read_bytes()).hexdigest()
(root/'prepared.json').write_text(json.dumps(packets,indent=2)+'\n')
