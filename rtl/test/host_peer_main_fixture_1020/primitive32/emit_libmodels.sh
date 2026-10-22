#!/bin/bash
set -eu
mkdir -p models
python3 - <<'LIB'
from pathlib import Path
ls=sorted(Path('real5').glob('asap7sc*'))
assert len(ls)==5
cmd=['read_liberty -ignore_miss_func '+str(p) for p in ls]
cmd+=['write_verilog -noattr models/imported_models.v']
Path('models/emit_models.ys').write_text('\n'.join(cmd)+'\n')
LIB
docker run --rm -v "$PWD:/work" -w /work openroad/orfs:latest yosys -Q -T -s models/emit_models.ys > models/emit_models.log 2>&1
python3 - <<'STRIP'
from pathlib import Path
import re,hashlib,json
p=Path('models/imported_models.v');s=p.read_text();mods=list(re.finditer(r'(?ms)^module (\S+).*?^endmodule\s*',s));assert mods
import importlib.util,sys
sp=importlib.util.spec_from_file_location("native","native_census.py");m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
roles,_=m.liberty_roles(list(Path("real5").glob("asap7sc*")))
out=[];removed=[];unsupported=[]
for m in mods:
 name=m.group(1).split("(")[0]
 if name.startswith('DFF'):removed.append(name)
 elif name not in roles or roles[name]["sequential"] or any(d["direction"]=="output" and d["function"] is None for d in roles[name]["pins"].values()):unsupported.append(name)
 else:out.append(m.group())
Path('models/comb_models.v').write_text('// Generated from exact five SS Liberty functions by Yosys read_liberty.\n'+'\n'.join(out))
rec={'libraries':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('real5').glob('asap7sc*'))},'emitted_combinational_modules':len(out),'removed_sequential_modules':removed,'unmodeled_not_for_use':unsupported,'canonical_ASR_sha256':hashlib.sha256(Path('canonical_ASR_normalized.v').read_bytes()).hexdigest(),'canonical_DFF_sha256':hashlib.sha256(Path('canonical_DFF_normalized.v').read_bytes()).hexdigest(),'note':'Keep canonical licensed FF files separate, append as compile inputs. Actual SRAM model separate; no formal macro abstraction in behavioral sim.'}
Path('models/model_sources.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
STRIP
