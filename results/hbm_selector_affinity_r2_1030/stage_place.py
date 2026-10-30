#!/usr/bin/env python3
"""Stage lane-private PLACE runner; exact native proof must qualify first."""
import sys,subprocess,importlib.util,json
from pathlib import Path
repo,A,K=map(Path,sys.argv[1:4]);here=Path(__file__).resolve().parent
cmd=[sys.executable,str(here/'qualify_logic_reuse.py'),str(A),str(K)]
if len(sys.argv)>4:cmd.append(sys.argv[4])
subprocess.run(cmd,check=True)
H=repo/'physical/die_plan/hbm_arch_cores';sys.path.insert(0,str(H))
sp=importlib.util.spec_from_file_location('role_gen',H/'gen_core_kit_hbm.py');G=importlib.util.module_from_spec(sp);sp.loader.exec_module(G)
src=(H/'run_kit_hbm.sh').read_text();needle='python3 -I /work/lec.py /work --netlist'
assert src.count(needle)==1,'runner changed: inspect before patching'
runner=here/'run_kit_qualified.sh';runner.write_text(src.replace(needle,'python3 -I /work/qualified_lec.py /work --netlist'));runner.chmod(0o755)
G.stamp_generation_inputs(K,repo)
fz=json.load(open(K/'freeze.json'));fz['logic_reuse']='lec/reuse.json';fz['kit_hash']=G.kit_hash(K);(K/'freeze.json').write_text(json.dumps(fz,indent=1)+'\n')
print('QUALIFIED_PLACE_READY',K)
