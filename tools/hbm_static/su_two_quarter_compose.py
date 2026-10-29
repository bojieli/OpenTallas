#!/usr/bin/env python3
"""One resident NW/NE programme for two/three real exp-sum rows.

Each row uses source VM rows128*r..128*r+127 and writes tensor results
in place after its source reads. Scalars use rows499-r; result sums use
rows496-r. Local SU store addresses remain the real finite128+128 rows.
All input and scalar data must be published before START by a real client.
No source VM publication or native arithmetic execution is inferred here.
"""
import argparse,contextlib,io,json,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent/'toksim_su/suvop'))
import prod_compile as C

def compose(out,rows,mlat=4,alat=4,wcopy=0,mutant='none'):
 if rows not in (2,3):raise ValueError('two/three rows only: fourth row overlaps scalar source under this finite VM layout')
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 C.MLAT,C.ALAT,C.WCOPY=mlat,alat,wcopy
 rng=np.random.default_rng(0x32515048);shared=(rng.integers(1,1000,(512,512)).astype(C.F)/C.F(1024)).astype(C.F)
 read_last={};write_first={}
 streams={k:[] for k in ('prog.mem','native_prog.mem','tree.mem','explw.mem','expw.mem','exps.mem')}
 phases=[];read_checks=0;errors=0
 for phase in range(rows):
  source=128*phase;scalar=499-phase;sumrow=496-phase
  local=shared.copy();local[:128]=shared[source:source+128];local[499]=shared[scalar]
  d=out/f'row{phase}';a=SimpleNamespace(out=str(d),rec='qw_softmax_exp_sum_r1',quarters=2,pin_reg=1,full_side=True,rr=25,wr=22,fill_slack=1,drain_slack=2,side_ii=0,rfd_slack=1,pretree=True,qpr=2,seed_override=local)
  with contextlib.redirect_stdout(io.StringIO()):C.compile_rec(a)
  man=json.loads((d/'programme.json').read_text());assert man['issues']==128
  offset=len(streams['prog.mem']);trees=(d/'tree.mem').read_text().splitlines()
  for edge,raw in enumerate((d/'prog.mem').read_text().splitlines()):
   word=int(raw,16);result=0;native=0
   for q in range(2):
    qw=(word>>(q*C.QW))&((1<<C.QW)-1)
    for port in range(8):
     shift=440+30*port;r=(qw>>shift)&((1<<30)-1)
     if r>>29:
      sec=(r>>13)&65535;row=(sec>>4)&511
      newrow=scalar if row==499 else row+source
      if mutant=='source_alias' and phase and row!=499:newrow=row
      if mutant=='scalar_stale' and phase and row==499:newrow=499
      assert 0<=newrow<512
      for k in range(8):
       col=(sec>>13)*128+((sec&15)*8)+k
       errors+=int(shared[newrow,col]!=local[row,col]);read_checks+=1
      sec=(sec&~(511<<4))|(newrow<<4);read_last[sec]=offset+edge+25
      r=(r&~(65535<<13))|(sec<<13)
      qw=(qw&~(((1<<30)-1)<<shift))|(r<<shift)
     shift=128+39*port;w=(qw>>shift)&((1<<39)-1)
     if w>>38:
      sec=(w>>8)&65535;row=(sec>>4)&511
      newrow=sumrow if row==498 else source+row-128
      assert (row==498 or 128<=row<256) and 0<=newrow<512
      sec=(sec&~(511<<4))|(newrow<<4);write_first.setdefault(sec,offset+edge+4)
      w=(w&~(65535<<8))|(sec<<8)
      qw=(qw&~(((1<<39)-1)<<shift))|(w<<shift)
    result|=qw<<(q*C.QW)
    tree=(int(trees[edge],16)>>(48*q))&((1<<48)-1)
    native|=(qw|(tree<<C.QW))<<(q*(C.QW+48))
   streams['prog.mem'].append(f'{result:0{2*C.QW//4}x}')
   streams['native_prog.mem'].append(f'{native:01235x}')
  for name in ('tree.mem','explw.mem'):streams[name]+=(d/name).read_text().splitlines()
  for name in ('expw.mem','exps.mem'):
   for raw in (d/name).read_text().splitlines():
    if name=='expw.mem':
     sec=int(raw[10:14],16);row=(sec>>4)&511
     newrow=sumrow if row==498 else source+row-128
     sec=(sec&~(511<<4))|(newrow<<4);raw=raw[:10]+f'{sec:04x}'+raw[14:]
    streams[name].append(f'{int(raw[:8],16)+offset:08x}'+raw[8:])
  phases.append(dict(row=phase,offset=offset,edges=man['edges'],source_vm_rows=[source,source+127],scalar_vm_row=scalar,sum_vm_row=sumrow,released_golden=man['reduction']['model_check'],finals=man['reduction']['finals']))
  # Each component already retains WR-complete retirement and an eight-edge
  # tail. Sequential full images therefore never overlap local-store phases.
 for name,lines in streams.items():(out/name).write_text('\n'.join(lines)+'\n')
 (out/'arith').mkdir(exist_ok=True);(out/'arith/seed.mem').write_text('\n'.join(f'{x:08x}' for x in shared.view(np.uint32).ravel())+'\n')
 overlaps=[dict(sector=s,last_read_return=read_last[s],first_write_capture=t) for s,t in write_first.items() if s in read_last and t<=read_last[s]]
 if mutant=='none':assert not overlaps,overlaps
 verdict='PASS' if not errors else 'CAUGHT'
 assert (mutant=='none')==(errors==0),(mutant,errors)
 m=dict(schema='native_su_two_quarter_contiguous_rows.v1',rows=rows,actual_qids=[2,3],native_bits=4940,clock_ps=833,edges=len(streams['prog.mem']),phases=phases,programme_reloads_between_rows=0,extra_barrier_edges=0,source_memory_word_checks=read_checks,source_memory_mismatches=errors,mutant=mutant,source_mapping_verdict=verdict,inplace_write_before_last_read=overlaps,installable=False,remaining=['actual role-local VM publication before START','actual native arithmetic execution and interquarter transport binding','candidate producer SRAM capacity and source/profile selection'])
 (out/'programme.json').write_text(json.dumps(m,indent=2)+'\n');return m

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('out');p.add_argument('--rows',type=int,required=True);p.add_argument('--mlat',type=int,default=4);p.add_argument('--alat',type=int,default=4);p.add_argument('--wcopy',type=int,default=0);p.add_argument('--mutant',choices=['none','source_alias','scalar_stale'],default='none')
 a=p.parse_args();m=compose(a.out,a.rows,a.mlat,a.alat,a.wcopy,a.mutant);print(json.dumps({k:m[k] for k in ('rows','edges','programme_reloads_between_rows','source_memory_word_checks','source_memory_mismatches','source_mapping_verdict','installable')}))
if __name__=='__main__':main()
