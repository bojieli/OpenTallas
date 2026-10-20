from pathlib import Path
import re
for cohort in ('closure_loop','ref_tile','fleet','landed_parent'):
 ids={}
 for side in ('base','cand'):
  p=Path(f'{side}_{cohort}.log');t=p.read_text();ids[side]={re.sub(r' - .*','',x) for x in t.splitlines() if x.startswith(('FAILED ','ERROR '))};print(side,cohort,Path(f'{side}_{cohort}.rc').read_text().strip(),t.splitlines()[-1]);Path(f'{side}_{cohort}.fail').write_text('\n'.join(sorted(ids[side]))+'\n')
 print('NEW',cohort,sorted(ids['cand']-ids['base']))
 print('FIXED',cohort,sorted(ids['base']-ids['cand']))
