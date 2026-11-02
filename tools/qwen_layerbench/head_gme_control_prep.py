#!/usr/bin/env python3
"""Emit the component-only native GME ROM and actual cmd380 field oracle.

Four genuine <=8-round descriptors are unchanged. Cycles are deliberately
TEST_ONLY controls, never emitted as production execution relocations.
"""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_isa as ISA
p=argparse.ArgumentParser(description=__doc__)
for k in ('programme','gme','out'):p.add_argument('--'+k,type=Path,required=True)
p.add_argument('--rank',type=int,choices=range(8),default=0);a=p.parse_args();P=a.out;P.mkdir(exist_ok=True,parents=True);(P/'input').mkdir(exist_ok=True)
obj=json.loads(a.programme.read_text());g=json.loads(a.gme.read_text())['ranks'][a.rank]
assert obj['programme']['meta_rows']==33 and [x['rounds']for x in g['programme_words'][:4]]==[8,8,8,1]
pw=[0]*1024
for r in obj['programme']['instructions']:
 v=int(r['word_hex'],16)
 for j in range(16):pw[r['pc']*16+j]=(v>>(64*j))&((1<<64)-1)
# BASE END fixture calendar is sealed but never started. HEAD cycles TEST_ONLY.
pw[976]=(1<<46)|50
for i,r in enumerate(g['programme_words']):pw[984+i]=((i==4)<<46)|(r['unit']<<44)|((28+i)<<32)|(1024*(i+1))
pw[992]=(0x43414c47<<32)|5120;pw[993]=(0x43414c42<<32)|(5<<24)|28
pw[1016]=(0x43414c31<<32)|50;pw[1017]=(0x43414c53<<32)|(33<<18)|(37<<12)|1;pw[1018]=(0x43414c32<<32)|60
pw[1022]=(0x58504654<<32)|5200;pw[1023]=(0x58504631<<32)|(37<<6)|6
(P/'input/program.memh').write_text(''.join(f'{x:016x}\n'for x in pw))
nochase=list(pw)
for pc in range(28,32):
 word=sum(nochase[pc*16+j]<<(64*j)for j in range(16));ff=ISA.decode(word);ff['chase']=0;ff['chase_n']=0;word=ISA.encode(**ff)
 for j in range(16):nochase[pc*16+j]=(word>>(64*j))&((1<<64)-1)
(P/'input/program_nochase.memh').write_text(''.join(f'{x:016x}\n'for x in nochase))

oldpw=list(pw);oldword=sum(oldpw[28*16+j]<<(64*j)for j in range(16));oldfields=ISA.decode(oldword);oldfields['me_tiles']=6;oldword=ISA.encode(**oldfields)
for j in range(16):oldpw[28*16+j]=(oldword>>(64*j))&((1<<64)-1)
(P/'input/program_old6.memh').write_text(''.join(f'{x:016x}\n'for x in oldpw))


fields=[('nout',18),('tiles',18),('k',18),('wsrc',1),('wbase',24),('ts',24),('ks',24),('js',24),('xbase',24),('xks',24),('xjs',24),('xcs',24),('jsh',3),('split',4),('wcs',24),('round',1),('obase',24),('ots',24),('ojs',24),('mmode',1),('oen',1),('amax',1),('rmax',1),('mbase',24)]
expected=[]
for rr in g['programme_words'][:4]:
 f=ISA.decode(int(rr['word_hex'],16));v=1;off=1
 for k,b in fields:
  x=f['me_'+k]+(18432 if k=='wbase' else 29376 if k=='wcs' else 0)
  if x>=1<<b:raise ValueError('native command field overflow')
  v|=x<<off;off+=b
 assert off==380
 expected.append(v)
(P/'input/cmd.memh').write_text(''.join(f'{v:095x}\n'for v in expected))
(P/'fixture.json').write_text(json.dumps(dict(status='TEST_ONLY_CONTROL_FIXTURE',rank=a.rank,clock_ps=833,GME_cycles=[1024,2048,3072,4096,5120],stop=5120,real_matrix_execution=False,numerical_results=False,head_production_dates=False,programme_sha256=hashlib.sha256(a.programme.read_bytes()).hexdigest(),GME_sha256=hashlib.sha256(a.gme.read_bytes()).hexdigest()),indent=2)+'\n')
