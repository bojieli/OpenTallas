"""Explicit NE mechanism transformation of the existing real bundle990 fixture."""
import argparse,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
subprocess.run([sys.executable,str(HERE/'gen_fixture.py'),'--out',str(a.out)],check=True)
f=a.out/'fixture_desc.mem';rows=[]
for line in f.read_text().splitlines():
 d=int(line,16);old=d>>5&((1<<40)-1);new=old^0x800
 pc=lambda b:((b>>7)^(b>>12)^(b>>17))&31
 if pc(old)^pc(new)!=16 or old>>12!=new>>12:raise ValueError('NE half transform must change only physicalPC4')
 d=(d&~(((1<<40)-1)<<5))|(new<<5);rows.append(f'{d:057x}')
f.write_text('\n'.join(rows)+'\n');p=a.out/'fixture.json';m=json.loads(p.read_text());m.update(source_quad=3,source_half_transform='Each original source byte XOR0x800: flipsPC4 only, preservesrow/col/slot/leaf/group/byteoffset; mechanismfixture, no productionrebase authority',original_fixture_source_quad=2,STORE_BACK_local_word=8192,STORE_ordinary_global_VMword=204800);p.write_text(json.dumps(m,indent=1)+'\n')
