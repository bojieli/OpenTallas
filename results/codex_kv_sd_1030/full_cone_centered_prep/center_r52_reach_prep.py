import json,gzip,math,re,sys
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-kv-sd-1030');d=json.load(open(r/'sd_r52_minimax_full_xy_inventory.json'));widths={}
for s in (r/'geom_sdpg_after/geom.tsv').read_text().splitlines():
 a=s.split('\t')
 if a[0]=='C' and a[2]=='S':widths[a[3]]=max(widths.get(a[3],0),float(a[6])-float(a[4]))
for z in d:
 n=z['instance'];basis=z['basis'];point=z['xy_um']
 if basis.startswith('split data row candidate:') or basis.startswith('held actual FDI boundary') or basis.startswith('held actual link boundary') or basis.startswith('held same-cycle TXup'):
  z['origin_lower_left_um']=point;z['xy_um']=[round(point[0]+widths[z['master']]/2,6),round(point[1]+.135,6)]
 elif basis=='RX actual scalar boundary/control proposed anchor':
  xy=[1883.52 if '/eq$' in n else 1885.032,675.27];z['origin_lower_left_um']=xy;z['xy_um']=[round(xy[0]+widths[z['master']]/2,6),675.405];z['basis']='RX actual two scalar boundary FF lower-left packed in row gap'
by={z['instance']:z for z in d};pairs=json.load(gzip.open(r/'sd_r52_all_ff_related_pairs.json.gz'));bad=[];max_nonraw=0
for c in pairs['captures']:
 if c['capture'] not in by:continue
 C=by[c['capture']]
 for i in c['source_indices']:
  S=by[pairs['sources'][i]];v=abs(S['xy_um'][0]-C['xy_um'][0])+abs(S['xy_um'][1]-C['xy_um'][1])
  if '.u_rrl_' not in S['instance'] and '.u_srl_' not in S['instance']:max_nonraw=max(max_nonraw,v)
  if v>405+1e-6:bad.append({'source':S['instance'],'capture':C['instance'],'L1_um':v})
rx=[];tx=[]
for x in json.load(open(r/'phy_rx_bit_consumers.json'))['rx_bits']:
 for n in x['sequential_consumers']:
  if n in by:
   X=by[n]['xy_um'];rx.append({'pin':x['pin'],'FF':n,'L1':abs(X[0]-x['xy_um'][0])+abs(X[1]-x['xy_um'][1])})
for x in json.load(open(r/'phy_tx_bit_xy.json'))['tx_bits']:
 b=int(re.search(r'\[(\d+)',x['pin'])[1]);n=next((n for n in by if re.search(r'p_tx_d\\?\['+str(b)+r'\\?\]',n)),None)
 assert n is not None
 X=by[n]['xy_um'];tx.append({'pin':x['pin'],'FF':n,'L1':abs(X[0]-x['xy_um'][0])+abs(X[1]-x['xy_um'][1])})
sys.path.insert(0,str(r/'src/tools/die_plan'));import taps
p=json.load(open(r/'plan_of_record/plan_c_sd_pg_anchor_v2.json'));ts=[(x['name'],*x['xy']) for x in p['partition_types']['kv3_sys_SD']['clock']['taps']];ss=[z['xy_um']+[1] for z in d if z['clock_net']=='clk'];lo,fa,asg=taps.assign(ts,ss,2400,400,max_distance_um=400)
rep={'qualified':False,'coordinates':'DATA/face fixed FF points now actual master bbox CENTRES; current generated reset/run/group/minimax points are anchorcentres, not legal packing','actual_FFcount':len(d),'FFpair_count':99645,'max_nonraw_FFpair_L1_um':max_nonraw,'over405':bad,'macro_RXbit_pairs':len(rx),'macro_RXbit_to_FF_max':max(rx,key=lambda x:x['L1']),'macro_TXbit_pairs':len(tx),'FF_to_macro_TXbit_max':max(tx,key=lambda x:x['L1']),'primaryroots':[{'name':t[0],'load':n,'max_L1_um':f} for t,n,f in zip(ts,lo,fa)],'primary_over220':sum(abs(s[0]-ts[j][1])+abs(s[1]-ts[j][2])>220+1e-6 for s,j in zip(ss,asg)),'raw_edge_note':'Four pre-hook rawtap2→boundaryepoch edges remain FAIL until actual mandatory reset_taps physical rebind is run and measured; not removed from report. No waveform/depth change authorized.'}
(r/'sd_r52_centered_reach_prep.json').write_text(json.dumps(rep,indent=2));(r/'sd_r52_centered_full_xy_inventory.json').write_text(json.dumps(d,indent=1));print(json.dumps(rep,indent=2))
