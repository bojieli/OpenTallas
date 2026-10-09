from collections import defaultdict,Counter
import json,sys,re
from collections import Counter
from pathlib import Path
p=Path(sys.argv[1]);j=json.loads(p.read_text());m=j['modules']['ot_hbm_index_lines_sram'];cells=m['cells'];nets=m['netnames'];drivers={}
for name,c in cells.items():
 for port,bits in c['connections'].items():
  if c.get('port_directions',{}).get(port, 'output' if port in {'QN','Y','rd_out'} else 'input')=='output':
   for bit in bits:
    if isinstance(bit,int):drivers[bit]=(name,c)
def root(bit,seen=None):
 if not isinstance(bit,int):return 'constant:'+bit
 seen=set() if seen is None else seen
 if bit in seen:return 'loop'
 seen.add(bit)
 if bit not in drivers:return 'undriven'
 name,c=drivers[bit];typ=c['type']
 if 'DFF' in typ:return name
 if typ.startswith(('INV','BUF')):
  ins=[b for p,bs in c['connections'].items() if c.get('port_directions',{}).get(p, 'output' if p in {'QN','Y','rd_out'} else 'input')=='input' for b in bs]
  if len(ins)==1:return root(ins[0],seen)
 return 'combinational:'+typ

local=defaultdict(set);categories=defaultdict(set);sample=[]
for name,n in m['netnames'].items():
 mat=re.match(r'pcs\[(\d+)\]\.(.*)',name)
 if not mat:continue
 pc=int(mat[1]);tail=mat[2]; roots={root(b) for b in n['bits'] if root(b) in cells and 'DFF' in cells[root(b)]['type']};local[pc]|=roots
 if tail.startswith(('enc.','encoded')):cat='encoder'
 elif '.dec.' in tail:cat='decoder'
 elif '.capture' in tail:cat='capture'
 elif '.check_q' in tail:cat='check_read_register'
 elif '.check' in tail:cat='check_sidecar'
 else:cat='other_local_metadata'
 categories[cat]|=roots
 if pc==0 and not name.startswith('$'):sample.append({'net':name,'width':len(n['bits']),'DFF_roots':len(roots)})
alllocal=set().union(*local.values());allff={n for n,c in cells.items() if 'DFF' in c['type']}
print(json.dumps({'source_commit':'859068da1','DFF_cells_total':len(allff),'DFF_cells_driving_PC_named_nets':len(alllocal),'DFF_cells_not_attributed_to_PC_named_nets':len(allff-alllocal),'per_PC':{str(k):len(v) for k,v in local.items()},'component_DFF_roots':{k:len(v) for k,v in categories.items()},'component_counts_may_overlap':True,'scope':'Mapped FF output roots intersecting retained PC namespace nets, conservative attribution; ABC combinational area lost hierarchy provenance. Central/global and frontend-renamed arrays may be unattributed. Current RTL is central64-decoded-bank gather, not distributed285bit collector.','PC0_net_sample':sample},indent=2))
