#!/usr/bin/env python3
"""Prepare an isolated exact owner-source S81 parent with NP28 H2 MC24 children.
No source-tree parent/BE/FE files are modified. All clocks tied for numerical proof only.
"""
import argparse,hashlib,json,pathlib,re,subprocess,tarfile,io
p=argparse.ArgumentParser(); p.add_argument('--owner',default='55740b883'); p.add_argument('--out',required=True); p.add_argument('--hop',type=int,choices=[1,2],default=2); p.add_argument('--pin-copy',type=int,choices=[0,1],default=0); p.add_argument('--reset-split',type=int,choices=[0,1],default=0); a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[3]; out=pathlib.Path(a.out).resolve(); src=out/'src'; src.mkdir(parents=True,exist_ok=True)
owner=subprocess.check_output(['git','rev-parse',a.owner],cwd=root).decode().strip()
archive=subprocess.check_output(['git','archive',owner,'rtl/dsrom_sys','rtl/lib','rtl/common','tools/s81_vm','physical/asap7_memory_macros_v2'],cwd=root)
with tarfile.open(fileobj=io.BytesIO(archive)) as t: t.extractall(src,filter='data')
files=['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgl.sv','rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq28h_mc24.sv']
for f in files: (src/f).write_bytes((root/f).read_bytes())
parent=src/'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv'; original=parent.read_bytes(); text=original.decode()
pattern=r'dsfd_vm_bgr #\(\.NP\(NP\), \.NPR\(NPR\), \.NB\(32\), \.NBL\(8\), \.QD\(QD\), \.RQ\(8\), \.MACRO\(MACRO\), \.DW\(128\), \.NSTG\(4\), \.EP\(EP\)\) u_bg \(\s*\.ck\(ck\), \.rs\(rst\),'
clocks=', '.join(f'.ck_{domain}_l{k}(ck)' for domain in ['bank','req','ret'] for k in range(8))
text,n=re.subn(pattern,f'dsfd_vm_bgq28h_mc24 #(.FORWARD_HOP({a.hop}), .PIN_OUTPUT_COPY({a.pin_copy}), .RESET_FANOUT_SPLIT({a.reset_split})) u_bg (\n                '+clocks+', .rs(rst),',text)
assert n==1, f'expected exactlyone selectedNP28 template, found{n}'
assert 'localparam integer NP = 28, NPR = 10, NT = 4' in text
assert 'localparam integer EP = 2;' in text
parent.write_text(text)
manifest={'status':'FUNCTIONAL_PROBE_PHYSICAL_CLOCK_DELIVERY_OPEN','owner_commit':owner,'successor_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),'owner_parent_sha256':hashlib.sha256(original).hexdigest(),'probe_parent_sha256':hashlib.sha256(parent.read_bytes()).hexdigest(),'only_parent_change':f'NP28 BGR child replacement with MC24 (=24 roots, not NP24), H{a.hop}, PIN_OUTPUT_COPY={a.pin_copy}; all roots tied numerically','NP':28,'NPR':10,'children':16,'forward_hop_per_tile':8*a.hop,'PIN_OUTPUT_COPY':a.pin_copy,'RESET_FANOUT_SPLIT':a.reset_split,'bank_EP':2,'bank_ED':3,'BE_definition':'unchanged owner source, dynamic MD','physical_clock_delivery':'OPEN','files':{f:hashlib.sha256((src/f).read_bytes()).hexdigest() for f in files}}
(out/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
runner=src/'run_native_h2.py'; runner.write_text('''import importlib.util,json,pathlib,sys\nroot=pathlib.Path(__file__).parent\nspec=importlib.util.spec_from_file_location('gate',root/'tools/s81_vm/s81_vm_gate.py'); g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)\ng.SRCS += ['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgl.sv','rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq28h_mc24.sv']\ncase=sys.argv[1]; out=root.parent/'bench'/case; r=g.one(case,out); (out/'result.json').write_text(json.dumps(r,indent=2)+'\\n'); sys.exit(0 if r['ok'] else1)\n'''.replace('else1','else 1'))
print(json.dumps(manifest,indent=2))
