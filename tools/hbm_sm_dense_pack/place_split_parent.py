exec(open('tools/hbm_sm_dense_pack/check_split_rows.py').read().split('for lf in range(2):')[0])
import numpy as np,hashlib
def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
for lf in range(2):
 for k,o in gate['compute_and_landing'][str(lf)]['orientations'].items():B[f'{lf}_{k}']['orient']=o
 B[f'{lf}_rowW']['orient']=['R180','MX'][lf];B[f'{lf}_rowE']['orient']='MX'
# Free parent points at least1um fromactualhardframes; nofictionalregisterareaovermacro.
free=[]
for y in np.arange(2,g['H']-2,2):
 for x in np.arange(2,g['W']-2,2):
  if not any(b['x']-1<x<b['x']+b['w']+1 and b['y']-1<y<b['y']+b['h']+1 for b in B.values()):free.append([x,y])
A=np.array(free);use=np.zeros(len(A));rels=[]
for lf in range(2):
 for bus in['w','x']:
  for bit in range(788):
   s=xy(f'{lf}_xs',f'o_i{bus}[{bit}]',B[f'{lf}_xs']['orient'],'xs');n=f'{lf}_bdc'if bit<532 else f'{lf}_tcl{(bit-532)//128}';k='bdc'if bit<532 else'tcl';pin=f'i_{bus}[{bit if bit<532 else(bit-532)%128}]';d=xy(n,pin,B[n]['orient'],k);cost=np.maximum(np.abs(A-s).sum(axis=1),np.abs(A-d).sum(axis=1));ok=np.where((cost<=500)&(use<8))[0]
   if not len(ok):raise Exception(('noexistingXRELstation',lf,bus,bit,float(cost.min())))
   j=ok[np.argmin(cost[ok]+use[ok]*.4)];use[j]+=1;q=list(map(float,A[j]));rels.append(dict(row=lf,bus=bus,bit=bit,source=s,existing_XREL=q,destination=d,first_um=sum(abs(s[i]-q[i])for i in range(2)),second_um=sum(abs(d[i]-q[i])for i in range(2))))
# NewbankD shares sourcebitindex with its assignedoutputQ; qfirst/outputstages notremoved.
bankD=[]
for lf in range(2):
 bank=B[['beatNlanding','beatSlanding'][lf]];rr=gate['compute_and_landing'][str(lf)]['landing_pairs'];face=gate['compute_and_landing'][str(lf)]['bank_output_face'];bankD.append({x['bit']:[x['source'][0],bank['y']+(0 if face=='N'else 43.2)]for x in rr})
forks=[]
for bit in range(2069):
 q=[224+1.6*(bit%128),232+.9*(bit//128)];p=xy('beatWtransit',f'd[{bit}]','R0','beat_e');sinks=[p,bankD[0][bit],bankD[1][bit]];distances=[dist(q,s)for s in sinks];assert max(distances)<=500,(bit,distances)
 forks.append(dict(bit=bit,existing_receiver_Q=q,sinks=sinks,max_um=max(distances)))
# ActualWtransit2edgeanalogue last->actualE2edge input. samesourcebit.
trans=[]
for bit in range(2069):
 s=xy('beatWtransit',f'last[{bit}]','R0','beat_e');d=xy('beatE',f'd[{bit}]','R0','beat_e');trans.append(dict(bit=bit,source=s,destination=d,um=dist(s,d)))
assert max(t['um']for t in trans)<500
out={'status':'PARTIAL_FULL18_ACTUAL_PIN_GATE_NEW_BANKS_UNHARDENED','frame':[g['W'],g['H']],'area_um2':g['area'],'children':list(B.values()),'compute_gate_source':'split18_east_gate.json','existing_XREL_3152_pairs':rels,'fork2069_pairs':forks,'transit2069_pairs':trans,'maximum_XREL_leg_um':max(max(r['first_um'],r['second_um'])for r in rels),'maximum_fork_um':max(t['max_um']for t in forks),'maximum_transit_um':max(t['um']for t in trans),'parent_station_grid':{'pitch_um':2,'maximum_bits_per_gridpoint':8,'note':'Each2x2umparentpatch<=8FF isanalyticalplacementdensity, notphysicalCTSroute.'},'parent_source_ownership':{'receiverQ':'ExistingOT_SMH_PINREGbin_l/u_pinb2069FF, threeforkloadsperQ,noaddededge','XREL':'ExistingOT_SMH_XREL3152operandFF+xvcontrol, samegoldenedges','qualification':'Parentpointplacementonly, notactualhardmacrooutlines. Existingclockrootsmustbesplitphysicallywithoutmask. Fixedhold/CTSareaandactualFFplacementunmeasured.'},'open':['Distinct3705W/Eboundarypintracks/receiverpairs andallrowactualpinsjointly','Allclock/reset/control/G1/gatherportnets','M6M8cutsoveractualOBS+PG','Newlanding1edgefullshapephysicalnativegate','RetainedactualWBsplitreferenceexactproof']}
json.dump(out,open('/home/ubuntu/wt/sm-dense-pack-1015/results/hbm_sm_dense_pack/split18_full_pin_progress.json','w'),indent=2);print({k:out[k]for k in ['maximum_XREL_leg_um','maximum_fork_um','maximum_transit_um']})
# Canonicaldistinct boundaryslots; analytic parentregistered pointsonly.
row_receiver=[];outdrivers=[]
for lf in range(2):
 b=B[f'{lf}_rowW'];o=b['orient']
 for bit in range(818):
  d=xy(f'{lf}_rowW',f'd[{bit}]',o,'row_w');q=[d[0]+(8 if lf==0 else-8),d[1]];row_receiver.append(dict(bus='rin',row=lf,bit=bit,Q=q,D=d))
  s=xy(f'{lf}_rowE',f'last[{bit}]','MX','row_e');outdrivers.append(dict(bus='rout',row=lf,bit=bit,source=s))
for bit in range(2069):outdrivers.append(dict(bus='bout',bit=bit,source=xy('beatE',f'last[{bit}]','R0','beat_e')))
slots=[(20+.128*i,'M6')for i in range(int((g['H']-40)/.128))]+[(20+.16*i,'M8')for i in range(int((g['H']-40)/.16))]
def assign(points,key,face):
 available=set(range(len(slots)));result=[]
 for x in sorted(points,key=lambda t:t[key][1]):
  q=x[key];j=min(available,key=lambda j:abs(slots[j][0]-q[1]));available.remove(j);y,layer=slots[j];b=[0 if face=='W'else g['W'],y];result.append(dict(**x,boundary=b,layer=layer,distance_um=dist(q,b)))
 return result
inp=[dict(bus='bin',bit=f['bit'],Q=f['existing_receiver_Q'])for f in forks]+row_receiver
out['boundary_inputs']=assign(inp,'Q','W');out['boundary_outputs']=assign(outdrivers,'source','E');out['boundary_input_max_um']=max(x['distance_um']for x in out['boundary_inputs']);out['boundary_output_max_um']=max(x['distance_um']for x in out['boundary_outputs']);assert out['boundary_input_max_um']<500 and out['boundary_output_max_um']<500
out['open'].append('BoundaryM6PORT/M8slots needPG-obstruction/viaescape check; atX0/W tileedgegrosscapacityonly, notfullroutecutcertificate.')
json.dump(out,open('/home/ubuntu/wt/sm-dense-pack-1015/results/hbm_sm_dense_pack/split18_full_pin_progress.json','w'),indent=2);print('boundary',out['boundary_input_max_um'],out['boundary_output_max_um'])
