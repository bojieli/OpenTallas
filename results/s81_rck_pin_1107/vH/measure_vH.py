import csv,re,json,statistics
rows=list(csv.DictReader(open('/tmp/s81-rck-6/vH_place.tsv'),delimiter='\t'))
def pos(r):return(float(r['x'])+float(r['w'])/2,float(r['y'])+float(r['h'])/2)
def bit(r):return int(re.findall(r'\[(\d+)\]',r['name'])[-1])
def grp(bucket):return {bit(r):pos(r) for r in rows if r['bucket']==bucket and '[' in r['name']}
def report(a,b):
 d=sorted(abs(a[j][0]-b[j][0])+abs(a[j][1]-b[j][1]) for j in a.keys()&b.keys());return {'bits':len(d),'median_um':statistics.median(d),'p95_um':d[int(.95*(len(d)-1))],'max_um':max(d)}
d0={bit(r):pos(r) for r in rows if re.search(r'u_tx_pin[./]u_enc[./]d0\[',r['name']) and r['bucket']=='encoder_ff'}
res={'pin2_to_encoder_d0':report(grp('pin_data2'),d0),'TXL6_to_PMA':report(grp('txl6'),grp('pma_data_pin'))}
for k in range(3):
 a=grp('bin_ff') if k==0 else grp('pin_data'+str(k-1));res['input_hop'+str(k)]=report(a,grp('pin_data'+str(k)))
for k in range(1,7):res['TXL_hop'+str(k)]=report(grp('txl'+str(k-1)),grp('txl'+str(k)))
ctrl=[]
for r in rows:
 if 'DFF' not in r['master']:continue
 n=r['name']
 if re.search(r'u_core[./](rs_t\[|lk_s\[|uf_s\[|st(?:_q)?\[)',n) or re.search(r'u_core[./]u_rm[./](wp_g[12]|rp|rp_g|f1|f2|fault)(?:\[|\$)',n) or r['bucket']=='pin_control0':ctrl.append({k:r[k] for k in ('name','x','y','clock_net','bucket')})
res['reset_control_registers']=ctrl
open('/tmp/s81-rck-6/vH_reach.json','w').write(json.dumps(res,indent=2)+'\n')
print(json.dumps({k:v for k,v in res.items() if k!='reset_control_registers'},indent=2));print('RESET_REGISTER_COUNT',len(ctrl));print(json.dumps(ctrl,indent=1))
