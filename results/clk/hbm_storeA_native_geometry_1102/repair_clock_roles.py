from pathlib import Path
import csv,json,collections
R=Path.cwd();roots={};loads=collections.defaultdict(list);other=collections.defaultdict(list)
for x in csv.DictReader(open(R/'graph.tsv'),delimiter='\t'):
 if x['kind']=='BTERM'and x['io']=='INPUT':roots[x['net']]=x['owner']
 if x['kind']=='ITERM'and x['io']=='INPUT'and x['signal']=='CLOCK':loads[x['net']].append(dict(inst=x['owner'],pin=x['pin'],master=x['master'],mastertype=x['mastertype']))
 if x['kind']=='ITERM'and x['io']=='INPUT'and x['signal']!='CLOCK'and x['net']in roots:other[x['net']].append(dict(inst=x['owner'],pin=x['pin'],sigtype=x['signal']))
result=[]
for net,pins in loads.items():
 assert net in roots,('native clock net without direct actual input root',net)
 ff=[p for p in pins if p['mastertype']=='CORE'and p['master'].startswith('DFF')];macro=[p for p in pins if p['mastertype']=='BLOCK'];assert len(ff)+len(macro)==len(pins)
 result.append(dict(port=roots[net],net=net,FF_CLK=ff,macro_CLK=macro,other_loads=other.get(net,[])))
assert len(result)==1 and result[0]['port']=='store0_clk[0]'and len(result[0]['FF_CLK'])==2914 and len(result[0]['macro_CLK'])==32
old=json.load(open(R/'result.json'))
if not(R/'initial_name_filter_omission.json').exists():(R/'initial_name_filter_omission.json').write_text(json.dumps(dict(diagnosis='Exporter startswith(clk) omitted actual store0_clk[0]. Native graph and source have real rooted clocks; correction uses native CLOCK MTerm net identity, not spelling.',initial_result=old),indent=2)+'\n')
(R/'clock_roots.json').write_text(json.dumps(result,indent=2)+'\n');old['clock_roots']=[dict(port=q['port'],net=q['net'],FF_CLK=len(q['FF_CLK']),macro_CLK=len(q['macro_CLK']),other_loads=len(q['other_loads']))for q in result];old['clock_role_basis']='Actual INPUT BTerm net identity to INPUT/CLOCK MTerms; name independent';old['clock_roles_verified']=True;(R/'result.json').write_text(json.dumps(old,indent=2)+'\n');print(old['clock_roots'])
