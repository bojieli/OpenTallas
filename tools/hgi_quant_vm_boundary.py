#!/usr/bin/env python3
"""Admitted remote elaboration, uncapped; use unchanged currentflow boundary analyser."""
import importlib.util,json,pathlib,subprocess,sys
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
p=pathlib.Path('tools/closure_loop/rtl_boundary.py')
s=importlib.util.spec_from_file_location('rb',p);rb=importlib.util.module_from_spec(s);s.loader.exec_module(rb)
config=pathlib.Path('physical/qwen_die_masters/cfg/hgi_quant_vm_pd50.env').read_text()
vars=rb._cfg_vars(config);sources=vars['SRCS'].strip("'\"").split()
script='read_verilog -sv -DSYNTHESIS '+' '.join(sources)+'; chparam -set ENABLE 1 -set DEPTH 32 ot_hgi_quant_vm_transport; hierarchy -top ot_hgi_quant_vm_transport; proc; flatten; opt_clean; techmap; opt_clean; write_json '+str(out/'netlist.json')
(out/'elaborate.ys').write_text(script+'\n')
with (out/'yosys.log').open('w') as f:
 subprocess.run([rb.YOSYS,'-s',str(out/'elaborate.ys')],stdout=f,stderr=subprocess.STDOUT,check=True)
result=rb._verdict(rb.analyse(json.loads((out/'netlist.json').read_text()),'ot_hgi_quant_vm_transport'),dict(top='ot_hgi_quant_vm_transport'),16,True)
(out/'boundary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if result['verdict']!='PASS':sys.exit(3)
