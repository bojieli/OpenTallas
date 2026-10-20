from pathlib import Path
import re,json,hashlib,gzip
B=Path(__file__).resolve().parent/'inputs'
T=['ot_sram_1r1w_32x546_m1_p192_mir','ot_sram_1r1w2c_32x546_m1_p192_mir']
P={};H={};W=177.768
for t in T:
 f=B/(t+'.lef.gz');raw=gzip.decompress(f.read_bytes());s=raw.decode();H[t]=hashlib.sha256(raw).hexdigest();P[t]={}
 for m in re.finditer(r'^  PIN ([^\n]+)\n(.*?)^  END \1$',s,re.M|re.S):
  r=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',m[2])
  if r:
   a=list(map(float,r.groups()));P[t][m[1]]=[(a[0]+a[2])/2,(a[1]+a[3])/2]
def pin(t,n,pos):
 x,y=P[t][n];ox,oy,o=pos
 return [ox+(W-x if o=='MY' else x),oy+y]
def md(a,b):return sum(abs(x-y) for x,y in zip(a,b))
plans={
 'original1e':{'rx_ib':[43.2,43.2,'R0'],'rx_af':[259.2,43.2,'MY'],'tx_ib':[259.2,432,'MY'],'tx_af':[43.2,432,'R0']},
 'same_domain_columns':{'rx_ib':[43.2,43.2,'R0'],'rx_af':[43.2,432,'R0'],'tx_ib':[259.2,432,'MY'],'tx_af':[259.2,43.2,'MY']}}
out={'schema':'opentallas.hostpc.reach_planning.v1','qualification':'MODEL_ONLY_NOT_PLACED','source':'exact1e memory bit correspondence rd_out[i] -> wq_data[i] -> wd_in[i]; mux/bypass/control/reset/crossclock/fullgraph NOT_PROVEN','lef_sha256':H,'band_y_um':[216,419.04],'plans':{}}
for name,plan in plans.items():
 rows=[]
 for d in ['rx','tx']:
  for i in range(546):
   a=pin(T[0],f'rd_out[{i}]',plan[d+'_ib']);b=pin(T[1],f'wd_in[{i}]',plan[d+'_af'])
   q=[(a[0]+b[0])/2,max(216,min(419.04,(a[1]+b[1])/2))]
   rows.append({'domain':d,'bit':i,'ib_rd':a,'af_wd':b,'planned_wq':q,'ib_to_wq_um':md(a,q),'wq_to_af_um':md(q,b)})
 out['plans'][name]={'macros':plan,'register_count':len(rows),'planned_bit_hop_max_um':max(max(r['ib_to_wq_um'],r['wq_to_af_um']) for r in rows),'planned_bit_hops_gt405':sum(max(r['ib_to_wq_um'],r['wq_to_af_um'])>405 for r in rows),'register_points':rows}
p=Path(__file__).with_name('model.json.gz');p.write_bytes(gzip.compress((json.dumps(out,indent=2)+'\n').encode(),mtime=0))
for n,p in out['plans'].items():print(n,p['planned_bit_hop_max_um'],p['planned_bit_hops_gt405'])
