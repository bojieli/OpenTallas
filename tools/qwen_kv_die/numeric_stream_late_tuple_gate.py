#!/usr/bin/env python3
"""A real extra coherent metadata edge must not relabel the unchanged word."""
import pathlib,json,hashlib,subprocess,os,shutil
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());src=out/'src_late_tuple_mutant';shutil.copytree(out/'src',src,dirs_exist_ok=True)
f=src/'rtl/physical/ot_qwen_tile_numeric_output_metadata.sv';s=f.read_text();before='assign numeric_tuple={has_query,payload};';after='reg [88:0] late_numeric; always @(posedge core_clk) late_numeric<={has_query,payload}; assign numeric_tuple=late_numeric;'
if s.count(before)!=1:raise RuntimeError('nonunique late tuple mutation')
f.write_text(s.replace(before,after));receipt={'mutated_source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'before':before,'after':after,'arithmetic_sources_unchanged':True}
obj=out/'obj_late_tuple_mutant';vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator');cmd=[vlt,'--binary','--timing','-j','2','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_numeric_stream_lifetime','--Mdir',str(obj),'-GMUT=4','-GALL_SPLITS=0','-GFULL_STALLS=0','-DXCACHE_TP8']+list(m['sources']);receipt['compiled_command']=cmd
with(out/'late_tuple_mutant_build.log').open('w')as log:subprocess.run(cmd,cwd=src,stdout=log,stderr=subprocess.STDOUT,check=True)
binary=obj/'Vtb_qwen_numeric_stream_lifetime';r=subprocess.run([str(binary)],cwd=src,capture_output=True,text=True);text=r.stdout+r.stderr;(out/'late_tuple_mutant.log').write_text(text);receipt.update(exit=r.returncode,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest());(out/'late_tuple_mutant_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
expected=['actual every-math numeric context mismatch','actual streaming mask/query sequence mismatch']
if not r.returncode or not any(x in text for x in expected):raise RuntimeError('late tuple escaped '+text)
print('PASS source-bound extra metadata edge refused: '+text,flush=True)
