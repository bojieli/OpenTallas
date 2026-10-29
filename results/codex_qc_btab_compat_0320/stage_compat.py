"""Canonical admission compatibility only; preserve the completed GRT physical design."""
import sys,json,hashlib,pathlib
K=pathlib.Path(sys.argv[1]);T=pathlib.Path(sys.argv[2]);out=pathlib.Path(sys.argv[3]);sys.path.insert(0,str(T));import core_infra
H=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(p.relative_to(K)):H(p) for p in K.rglob('*') if p.is_file()}
a=json.load(open(K/'core_infra_plan.json'));b=core_infra.compile_slice(json.load(open(K/'master_slice.json')),K)
c=json.loads(json.dumps(b));assert c['core_tree'].pop('under_gate')=={};assert c==a,'active compiled design changed'
sl=json.load(open(K/'master_slice.json'))
assert core_infra.emit_tcl(sl,K)==(K/'master_core_infra.tcl').read_text()
assert core_infra.emit_cts_tcl(b)==(K/'core_infra_cts.tcl').read_text()
old=(K/'core_infra_impl.tcl').read_text();new=(T/'core_infra.tcl').read_text();begin=new.index('# FORM C (CORES-EARLY-5):');end=new.index('proc ot_ci_lec_netlist',begin);assert new[:begin]+new[end:]==old,'active implementation changed'
(K/'core_infra_plan.json').write_text(json.dumps(b,indent=2)+'\n');(K/'core_infra_impl.tcl').write_text(new)
after={str(p.relative_to(K)):H(p) for p in K.rglob('*') if p.is_file()}
changed=sorted(k for k in before if before[k]!=after[k]);assert changed==['core_infra_impl.tcl','core_infra_plan.json'],changed
x=dict(scope='admission compatibility; no physical build',canonical_compiler_source='309dfdf952d14c1ae4838a513f4eefe1ee200b35',native_GRT_source='f28e60fc9464',changed_files=changed,compile_difference='core_tree.under_gate absent -> empty dictionary',implementation_difference='unused ot_ci_tree_gate_planned procedure only',all_other_file_hashes_unchanged=True,files_compared=len(before),frozen_physical={k:v for k,v in before.items() if k.endswith(('5_1_grt.odb','5_1_grt.sdc','3_place.odb','master_slice.json','constraint.sdc','core_infra_cts.tcl','master_core_infra.tcl','pins.json'))},compiler_sha256=H(T/'core_infra.py'),implementation_sha256=H(T/'core_infra.tcl'))
out.write_text(json.dumps(x,indent=1)+'\n');print(json.dumps(x,indent=1))
