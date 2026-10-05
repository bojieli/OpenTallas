import sys,json,gzip,hashlib,math,re
from pathlib import Path
import numpy as np
R=Path('/home/ubuntu/OpenTallas-hbrom-cluster-20261005');sys.path.insert(0,str(R/'tools'))
import hbrom_global_screen as S
ip=R/'results/uarch/hbrom/g0_inputs.json.gz';pp=R/'results/rtl/w19_hbm_tp96_program_oreduce.json'
I=json.load(gzip.open(ip,'rt'));P=json.load(open(pp));M,D=S.compile_matrices(I,P)
private=json.load(open('/tmp/hbrom-global-rank-floorplan.json'))['uniform_element']['private_compute_mm2']
cases=[]
for tp in [64,96,128]:
 for sm in [16,32]:
  cur=np.zeros((tp,sm),dtype=np.int64); families={}
  for t,o in M:
   if tp==96: counts=np.array([b-a for a,b in o['rows']],dtype=np.int64)
   elif o['fn']=='wo_a_part':counts=np.array([1024 if r<64 else 0 for r in range(tp)])
   elif '.wq_b.weight' in t['name']:counts=np.array([512 if r<64 else 0 for r in range(tp)])
   else:counts=np.array([(r+1)*o['n']//tp-r*o['n']//tp for r in range(tp)])
   tile=counts[:,None]//sm+(np.arange(sm)[None,:]<counts[:,None]%sm)
   key=re.sub(r'\.w[123]\.weight$','',t['name']);shift=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%sm;tile=np.roll(tile,shift,axis=1)
   L={'fp4':8,'fp8':4,'bf16':64}[o['fmt']];U=1 if o['fmt']=='bf16' else 32
   C=o['k']//(8*U);G=(C+L-1)//L;valid=[min(L,C-g*L) for g in range(G)]
   assert all(L%a==0 and 8%(L//a)==0 for a in valid)
   rpr=sum(8//(L//a) for a in valid);cur+=tile*rpr
   family=re.sub(r'layers\.\d+','layers.*',t['name']);family=re.sub(r'experts\.\d+','experts.*',family)
   v=dict(format=o['fmt'],K=o['k'],native_groups=G,max_rows_per_rank=int(counts.max()),max_rows_per_engine=int(tile.max()),native_items_per_engine=int(tile.max())*G,native_waves_per_engine=math.ceil(int(tile.max())*G/8),issue_slot_cycles_lower_bound=math.ceil(int(tile.max())*G/8)*64,compact_records_per_row=rpr)
   if family not in families or v['issue_slot_cycles_lower_bound']>families[family]['issue_slot_cycles_lower_bound']:families[family]=v
  pairs=(cur+8191)//8192*4;maxp=int(pairs.max()); area=pairs.sum(axis=1)*2*I['macro']['area_mm2']
  cases.append(dict(ranks=tp,engines_per_rank=sm,rotation=True,mapped_matrix_count=len(M),compact_records=int(cur.sum()),max_pairs_per_pool=maxp,total_allocated_pairs=int(pairs.sum()),pool_padding_records=int((pairs//4*8192-cur).sum()),max_rank_raw_ROM_mm2=float(area.max()),uniform_pool_raw_ROM_mm2_per_rank=maxp*sm*2*I['macro']['area_mm2'],families=families,qualified=False,TPOT_us=None))
# Reuse exact published pool geometry equations with the newly enumerated pool sizes.
source=Path('/tmp/hbrom_global_pool_geometry.py').read_text(); source=source[:source.index("out={'schema'")]
source=re.sub(r'for N in \[[^\]]+\]:','for N in '+repr(sorted({c['max_pairs_per_pool'] for c in cases}))+':',source)
ns={'__file__':'/tmp/hbrom_global_pool_geometry.py'};exec(compile(source,'pool_geometry_equations','exec'),ns);geom={r['pairs_per_pool']:r for r in ns['rows']}
for c in cases:
 g=geom[c['max_pairs_per_pool']]; sm=c['engines_per_rank'];c['pool_geometry']=g
 c['private_compute_mm2_per_rank']=sm*private
 c['ROM_channels_network_compute_mm2_per_rank_lower']=sm*(g['pool_plus_network_mm2_lower']+private)
 c['ROM_channels_network_compute_mm2_per_rank_upper']=sm*(g['pool_plus_network_mm2_conservative_upper']+private)
 c['with_additional20pct_global_spacing_mm2']=c['ROM_channels_network_compute_mm2_per_rank_upper']/.8
 c['service_budget_under814p08_mm2']=814.08-c['with_additional20pct_global_spacing_mm2']
 c['array_total_silicon_mm2_without_services']=c['ranks']*c['with_additional20pct_global_spacing_mm2']
pins=[ip,pp,Path('/tmp/hbrom-global-firstuse-layout.json'),Path('/tmp/hbrom-global-pool-geometry.json'),Path('/tmp/hbrom_global_pool_geometry.py'),Path('/tmp/hbrom-global-rank-floorplan.json'),R/'tools/hbrom_global_screen.py',Path(__file__)]
out=dict(schema='opentallas.hbrom.firstprinciples_rank_frontier.v1',architecture_only=True,qualified=False,source_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in pins},mapping='TP96 retains program row owners; TP64/128 balanced complete rows except64 attention-head owners wq_b and64 wo_a partial owners with8x8 exact reduction retained. This is not a TP96 transport schedule transplanted to other rank counts.',cases=cases,deferred_source_and_dedicated_bytes=sum(t['bytes'] for t in D),deferred_replicated_bytes_per_rank=sum(t['bytes'] for t in D if t.get('replicated')),auxiliary_storage_bytes=I['auxiliary_storage_bytes'],scope='Mapped executable matrix pools only. Dedicated/sourcearchive Engram MTP vision scales originalwo_a and aux retain separate storage and service obligations.',interpretation=['Native issue wave lowerbounds exclude pipeline refill context service arbitration and dependency tails.','Compact firstuse layout can retain identical native compute operand sequence; finite scheduling still required.','New rank mappings require analytical matching of exact collective trees and transports; no performanceclaim.','Service budget is area-only; mutable SRAM may replace HBM but must include capacity protection banking ports links and routing.','All borrowed pool geometry numbers are analytical footprints, not placement or SS/FF closure.','Additional global20percent spacing deliberately retained atop local channels.','Whole vocabulary head rows balanced across ranks;64 fixed owners here refers to64 attention heads.'],TPOT_claim=None)
Path('/tmp/hbrom-firstprinciples-rank-frontier.json').write_text(json.dumps(out,indent=2)+'\n')
for c in cases: print(c['ranks'],c['engines_per_rank'],c['max_pairs_per_pool'],round(c['uniform_pool_raw_ROM_mm2_per_rank'],1),round(c['with_additional20pct_global_spacing_mm2'],1),round(c['service_budget_under814p08_mm2'],1))
