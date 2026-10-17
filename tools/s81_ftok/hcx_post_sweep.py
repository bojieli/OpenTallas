#!/usr/bin/env python3
"""ActualnativeHCP-recorded rawmix ->actualHGI op2 native coefficient gate.
Fullresident parameterROM selected by43layerindices; all55contexts retain
independent inputs/expectations. This doesnot qualify live dieallgather/VMports.
"""
import argparse,json,subprocess
from pathlib import Path
from hcx_post_vectors import build
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--vectors',type=Path,required=True);p.add_argument('--raw-native',type=Path,required=True);p.add_argument('--resident',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
results=[]
for src in sorted(list((a.vectors/'vec').glob('L*'))+list((a.vectors/'vecm').glob('M*'))):
 case=src.name;layer=int(case[1:]) if case.startswith('L') else 40+int(case[1]);dest=a.out/case
 build(src,dest,a.raw_native/case)
 r=subprocess.run([str(a.binary.resolve()),f'+DIR={dest.resolve()}',f'+OT_ROM_DIR={a.resident.resolve()}',f'+LAYER={layer}','+COMPILED_CYC=540'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (dest/'run.log').write_text(r.stdout)
 if r.returncode or 'HCX_POST_NATIVE PASS'not in r.stdout:raise RuntimeError(f'{case} layer{layer}: exit{r.returncode},see{dest}/run.log')
 results.append(dict(case=case,layer=layer,jobs=2,exact_native_words=64,public_serial_cycles=541));print(f'HCX_POST_NATIVE {case} layer{layer} exact64words fixedcycles541 actualHCP-input',flush=True)
(a.out/'summary.json').write_text(json.dumps(dict(scope='nativearithmeticchain withrecordedHCP handoff, notlivedieallgather',results=results),indent=2)+'\n');print(f'HCX_POST_NATIVE_SWEEP PASS cases{len(results)} jobs{len(results)*2} exactwords{len(results)*64}',flush=True)
