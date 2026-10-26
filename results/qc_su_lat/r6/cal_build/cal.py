import json,re,sys,collections,statistics as st
base='/srv/opentallas-scratch2/claude/qc-su-lat-r6'
def native(log):
  t=open(log).read();o={}
  for c in ('TT','FF'):
    o[c]={m[0]:(int(m[1]),float(m[2])) for m in re.findall(r'OT_MSCTS_TAP grt '+c+r' (\S+) n (\d+) mean ([-.\d]+)',t)}
  return o
def dmp(d):
  lo=json.load(open(d+'/leafof.json'));o={}
  for c in ('TT','FF'):
    g=collections.defaultdict(list)
    for l in open(f'{d}/arrivals_{c}.tsv'):
      p,v=l.split('\t');g[lo[p.split('/')[0]]].append(float(v))
    o[c]={k:sum(v)/len(v) for k,v in g.items()}
  return o
def cmp(nat,mod,label):
  r={}
  for c in ('TT','FF'):
    ks=[k for k in nat[c] if k in mod[c]]
    if not ks: r[c]=None;continue
    res=[nat[c][k][1]-mod[c][k] for k in ks];w=[nat[c][k][0] for k in ks]
    off=sum(a*b for a,b in zip(res,w))/sum(w)
    r[c]=dict(leaves=len(ks),offset_meas_minus_model=round(off,2),resid_sd_after_offset=round(st.pstdev(res),2),resid_range=[round(min(res)-off,1),round(max(res)-off,1)])
  print(label,json.dumps(r));return r
plan=json.load(open(sys.argv[1]))
n6=native(base+'/btab_r6/cts_grt.log')
nl={c:{k:v[0] for k,v in plan['pred_leaf'][c]['leaf'].items()} for c in ('TT','FF')}
out={'r6_nldm':cmp(n6,nl,'R6 NLDM'),'r6_dmp':cmp(n6,dmp(base+'/plan_sta/k1'),'R6 DMP')}
try:
  n5=native('/srv/opentallas-scratch2/claude/qc-su-lat-r5/btab_r5/cts_grt.log');out['r5_dmp']=cmp(n5,dmp(base+'/plan_sta/r5star'),'R5 DMP')
except Exception as e: print('r5',e)
json.dump(out,open(base+'/btab_r6/calib_perleaf.json','w'),indent=1)
