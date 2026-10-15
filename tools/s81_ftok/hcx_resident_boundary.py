#!/usr/bin/env python3
"""Run real fullresident nativeprojection across physicalpage/layer/MTP edges.
The resident ROM directory is built once from all43weightsets. Stage/expected
files come from independent released fullK vectors. Arithmetic usesactualRTL.
"""
import argparse,json,subprocess
from pathlib import Path
from hcx_projection_vectors import build
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--vectors',type=Path,required=True);p.add_argument('--resident',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rows=[]
for layer,case in [(0,'L00'),(24,'L24'),(25,'L25'),(39,'L39'),(40,'M0R0'),(41,'M1R0'),(42,'M2R4')]:
 src=a.vectors/('vec'if layer<40 else'vecm')/case;dest=a.out/case;build(src,dest,0)
 r=subprocess.run([str(a.binary.resolve()),f'+DIR={dest.resolve()}',f'+OT_ROM_DIR={a.resident.resolve()}',f'+LAYER={layer}'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (dest/'run.log').write_text(r.stdout)
 if r.returncode or 'HCX_PROJECTION PASS'not in r.stdout:raise RuntimeError(f'{case} layer{layer}: exit{r.returncode}, see{dest}/run.log')
 rows.append(dict(case=case,layer=layer,outputs=2,cycles=264));print(f'HCX_RESIDENT_BOUNDARY {case} layer{layer} exact2 cycles264',flush=True)
(a.out/'summary.json').write_text(json.dumps(dict(scope='full43set residentROM projection row0 component',results=rows),indent=2)+'\n');print('HCX_RESIDENT_BOUNDARY PASS',flush=True)
