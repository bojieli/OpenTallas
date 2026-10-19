import csv,json,re,collections
from pathlib import Path
p=Path(__file__).parent
D={n:{r['name']:r for r in csv.DictReader((p/f'{n}_census.tsv').open(),delimiter='\t')} for n in ('original','control_baseline','final')}
def kind(r):
 m=r['master']
 return 'hard_macro' if r['block']=='1' else 'FF' if re.match(r'(?:S?DFF|LATCH)',m) else 'BUF_INV_HB' if (m.startswith(('BUF','HB2','HB4')) or 'INV' in m) else 'comb_or_physical'
def summarize(rows):
 a=collections.defaultdict(lambda:{'count':0,'lef_area_um2':0})
 for r in rows:
  x=a[kind(r)];x['count']+=1;x['lef_area_um2']+=float(r['area_um2'])
 return {k:{'count':v['count'],'lef_area_um2':round(v['lef_area_um2'],6)} for k,v in a.items()}
out={'classification':'Actual LEF masters/area; FF master prefix DFF/SDFF, transparent BUF/INV/HB2/HB4. Other includes comb and physical-only cells.','snapshots':{n:summarize(d.values()) for n,d in D.items()},'deltas':{}}
for n in ['original','control_baseline']:
 b=D[n];f=D['final'];add=[f[k] for k in f.keys()-b.keys()];rem=[b[k] for k in b.keys()-f.keys()]
 masters=collections.defaultdict(lambda:{'added_count':0,'added_area_um2':0,'removed_count':0,'removed_area_um2':0})
 for label,rows in [('added',add),('removed',rem)]:
  for r in rows:
   masters[r['master']][label+'_count']+=1;masters[r['master']][label+'_area_um2']+=float(r['area_um2'])
 out['deltas'][n+'_to_final']={'added':summarize(add),'removed':summarize(rem),'same_name_master_changes':[k for k in b.keys()&f.keys() if b[k]['master']!=f[k]['master']],'masters':masters}
(p/'native_final_cell_area.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='deltas'},indent=2))
for n,d in out['deltas'].items(): print(n,json.dumps({k:v for k,v in d.items() if k!='masters'}))
