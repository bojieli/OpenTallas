import pathlib,subprocess
r=pathlib.Path(__file__).resolve().parent;words=[int(s,16) for s in (r/'boot.hex').read_text().split()]
for name in ['min_t0_dense','alternating_rows']:
 p=r/'out'/name;p.mkdir();ws=words.copy()
 for stage in range(36):
  t0=4 if name=='min_t0_dense' or stage%2==0 else 1000
  ws[5*stage:5*stage+5]=[t0,t0+1,t0+2,t0+3,t0+6]
 (p/'boot.hex').write_text(''.join(f'{w:016x}\n' for w in ws))
 q=subprocess.run(['vvp',str(r/'out/m0.sim')],cwd=p,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (p/'run.log').write_text(q.stdout)
 assert q.returncode==0 and 'cases1152 slots4608 sectors9216' in q.stdout,(name,q.returncode,q.stdout[-500:])
 print('PASS boundary timing',name,q.stdout.strip())
