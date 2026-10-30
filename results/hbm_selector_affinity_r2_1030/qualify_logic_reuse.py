#!/usr/bin/env python3
"""Carry only exact-source completed synthesis/EQUIVALENT native proof to fresh GEN."""
import sys,json,hashlib,re,shutil,subprocess
from pathlib import Path
A,B=map(Path,sys.argv[1:3]);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.load(open(A/'lec/lec.json'))['verdict']=='EQUIVALENT','source proof not EQUIVALENT'
inventory=lambda k,d:{str(p.relative_to(k/d)):h(p) for p in (k/d).rglob('*') if p.is_file()}
assert inventory(A,'rtl')==inventory(B,'rtl'),'RTL differs; must synthesize/prove fresh source'
assert inventory(A,'macros')==inventory(B,'macros'),'macro files differ'
def cfg(k,key):return re.search(r'^export '+key+r' = (.*)$',(k/'config.mk').read_text(),re.M).group(1).split()
for key in ['VERILOG_FILES','VERILOG_DEFINES','VERILOG_INCLUDE_DIRS']:assert cfg(A,key)==cfg(B,key),f'{key} differs'
af,bf=[json.load(open(k/'freeze.json')) for k in [A,B]]
assert af['design']==bf['design'] and (af.get('params') or {})==(bf.get('params') or {})
ar=next((A/'run/results').glob('*/*/base'));br=B/'run/results'/ar.relative_to(A/'run/results');br.mkdir(parents=True,exist_ok=True)
assert not list(br.glob('*.odb')),'destination already contains physical result'
copied=[]
for p in ar.iterdir():
 if p.name.startswith('1_') and p.is_file():
  shutil.copy2(p,br/p.name)
  # Content is hash-qualified below. Mark cache outputs newer than the fresh
  # identical RTL to prevent make from needlessly resynthesizing it.
  (br/p.name).touch();copied.append(p.name)
assert all((br/n).is_file() for n in ['1_synth.v','1_2_yosys.v','1_synth.odb'])
assert not (B/'lec').exists(),'destination already has proof'
shutil.copytree(A/'lec',B/'lec')
r=dict(source_kit=str(A),destination_kit=str(B),copied_synthesis_files=copied,rtl_sha256=inventory(A,'rtl'),macro_inventory_sha256=inventory(A,'macros'),source_qualified_proof_sha256=h(A/'lec/lec.json'),formal_gold_script_sha256=h(A/'lec/gold.ys'),formal_gold_aig_sha256=h(A/'lec/gold.aig'),formal_gate_script_sha256=h(A/'lec/gate.ys'),formal_gate_aig_sha256=h(A/'lec/gate.aig'),synth_v_sha256=h(ar/'1_synth.v'),formal_netlist_sha256=h(ar/'1_2_yosys.v'),old_top=af['design'],new_top=bf['design'],old_params=af.get('params') or {},new_params=bf.get('params') or {},old_defines=[d.removeprefix('-D') for d in cfg(A,'VERILOG_DEFINES')],new_defines=[d.removeprefix('-D') for d in cfg(B,'VERILOG_DEFINES')],verilog_files=cfg(B,'VERILOG_FILES'))
(B/'lec/reuse.json').write_text(json.dumps(r,indent=2)+'\n')
shutil.copy2(Path(__file__).with_name('check_logic_reuse.py'),B/'check_logic_reuse.py')
shutil.copy2(Path(__file__).with_name('qualified_lec.py'),B/'qualified_lec.py')
subprocess.run([sys.executable,str(B/'check_logic_reuse.py'),str(B)],check=True)
print('QUALIFIED_LOGIC_REUSE_EQ',B)
