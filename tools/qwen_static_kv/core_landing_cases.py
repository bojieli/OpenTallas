from pathlib import Path
import sys
O=Path(sys.argv[1]);O.mkdir(exist_ok=True)
for T in (1,77,2048,4097,4300,4500,6000,8192):
 for s,g in ((0,0),(1,3),(3,7)):
  ts=[t for t in range(T) if (t>>7)&3==s and t&7==g]
  sec=lambda t: ((t>>6)&1)*128+((t>>9)&15)*8+((t>>3)&7)
  if sum((t>>7)&3==s for t in range(T))>1024:ts.sort(key=sec)
  ks=[sec(t) for t in ts]
  vs=[512+((t>>6)&1)*128+((t>>9)&15)*8+((t>>1)&7) for t in range(T) if (t>>7)&3==s and ((((t>>4)&3)<<1)|(t&1))==g]
  # Production fixed laws, independent row enumeration and edge arithmetic.
  ko=[i+(i//8)*3 for i in range(len(ks))];vo=[i+(i//8)*6 for i in range(len(vs))]
  (O/f'c{T}_{s}_{g}.txt').write_text(f'{s} {g} {T} 0 626 228 3 4 40 1000 {len(ks)} {len(vs)} 8 3 8 6\n'+'\n'.join(' '.join(map(str,x+[0])) for x in (ks,ko,vs,vo))+'\n')
