"""Independent all-bit/all-corner physical data-reach replay of a candidate."""
import json,pathlib,sys,math,itertools,hashlib
root=pathlib.Path('results/arch/qw_cb16_legal_bays_1020/grid43');name=sys.argv[1];d=json.loads((root/(name+'_bank_inputs.json')).read_text());s=json.loads((root/(name+'_joint_solution.json')).read_text());assert s['status'] in ['OPTIMAL','FEASIBLE'];hard=s['hard'];bays=s['bays'];errors=[]
def corners(r):x,y,w,h=r;return [(x,y),(x+w,y),(x,y+h),(x+w,y+h)]
def far(a,b):return max(abs(x-xx)+abs(y-yy) for x,y in corners(a) for xx,yy in corners(b))
def overlap(a,b,pad=0):x,y,w,h=a;xx,yy,ww,hh=b;return x-pad<xx+ww-1e-6 and xx<x+w+pad-1e-6 and y-pad<yy+hh-1e-6 and yy<y+h+pad-1e-6
def xy(pt):
 if 'fixed' in pt:return pt['fixed']
 x,y,_,_=hard[pt['node']];a,b=pt['offset'];return x+a,y+b
for n,r in hard.items():
 if any(abs(z/43.2-round(z/43.2))>1e-6 for z in r[:2]):errors.append(('offgrid',n,r))
for (a,x),(b,y) in itertools.combinations(hard.items(),2):
 if overlap(x,y,21.6-1e-6):errors.append(('hard_clearance',a,b))
for a,x in bays.items():
 for b,y in hard.items():
  if overlap(x,y,21.6-1e-6):errors.append(('bay_hard_clearance',a,b))
for (a,x),(b,y) in itertools.combinations(bays.items(),2):
 if overlap(x,y,4.32-1e-6):errors.append(('bay_clearance',a,b))
hops=[abs(xy(a)[0]-xy(b)[0])+abs(xy(a)[1]-xy(b)[1]) for a,b in d['hard_hops']]
anchors=[]
for n,b in d['halves'].items():
 for pt in b['anchor_refs']:
  x,y=xy(pt);anchors.append((max(abs(x-xx)+abs(y-yy) for xx,yy in corners(bays[n])),n))
bank=[(far(bays[a],bays[b]),a,b) for a,b in d['bank_edges']];soft=[(far(bays[a],bays[b]),a,b) for a,b in d['soft_edges']]
for kind,rows in [('hard',[(x,) for x in hops]),('anchor',anchors),('bank',bank),('soft',soft)]:
 for row in rows:
  if row[0]>405+1e-6:errors.append((kind,*row))
report={'status':'FAIL' if errors else 'PASS','hard_bit_endpoints':len(hops),'hard_max_um':max(hops,default=0),'soft_hard_point_tests':len(anchors),'soft_hard_max_um':max(anchors,default=(0,))[0],'bank_max_um':max(bank,default=(0,))[0],'soft_max_um':max(soft,default=(0,))[0],'hard_lattice_um':43.2,'hard_bay_clearance_um':21.6,'bay_clearance_um':4.32,'area_mm2':d['outline'][0]*d['outline'][1]/1e6,'errors':errors,'scope':'DATA_GEOMETRY_ONLY; scalar/reset site proof, actual synthesis/native/CTS/route remain owed','solution_sha256':hashlib.sha256((root/(name+'_joint_solution.json')).read_bytes()).hexdigest()}
(root/(name+'_data_replay.json')).write_text(json.dumps(report,indent=2)+'\n');print('DATA_REPLAY',name,report['status'],report['hard_max_um'],report['soft_hard_max_um'],report['bank_max_um'],report['soft_max_um']);assert not errors
