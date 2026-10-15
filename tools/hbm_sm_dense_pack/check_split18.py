#!/usr/bin/env python3
"""Read actualcomputeLEF pairs and score proposed splitpack without hidingfailednets."""
import json,pathlib,argparse,itertools,math
P=argparse.ArgumentParser();P.add_argument('--candidate',required=True);P.add_argument('--out',required=True);a=P.parse_args();r=pathlib.Path('/home/ubuntu/wt/hbm-smcompact-1014');M=json.load(open('results/hbm_sm_dense_pack/plan.json'))['source_models'];g=json.load(open(a.candidate));B={b['name']:b for b in g['blocks']};records=[]
def xy(name,pin,orient=None):
 b=B[name];kind='tcl'if'tcl'in name else name.split('_',1)[1];p=M[kind]['pins'][pin];x,y=p['x'],p['y'];o=orient or b['orient']
 if o in('MY','R180'):x=b['w']-x
 if o in('MX','R180'):y=b['h']-y
 return [b['x']+x,b['y']+y]
def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
def landing(lf,o,emit=False):
 bank=B[['beatNlanding','beatSlanding'][lf]];dest=[(xy(f'{lf}_xs',f'bk1[{i}]',o),i)for i in range(2069)];dest.sort()
 # Alllegalbankoutputfacechoices, fixedlogicalpinmappingrecorded.
 opts=[]
 for face in('S','N'):
  sy=bank['y']+(bank['h']if face=='N'else 0);rr=[]
  for j,(d,i)in enumerate(dest):
   q=[bank['x']+8.736+.096*j,sy];rr.append(dict(bit=i,source=q,destination=d,distance_um=dist(q,d)))
  opts.append((max(x['distance_um']for x in rr),face,rr))
 return min(opts,key=lambda x:x[0])
# Exhaust legalcomputeorientations (noR90), retain actualpinindices.
choices={}
for lf in range(2):
 best=None
 for os,ob,ot,oh0,oh1 in itertools.product(['R0','MX','MY','R180'],repeat=5):
  cur=[]
  for half,oh in [(0,oh0),(1,oh1)]:
   for bit in range(256):cur.append((dist(xy(f'{lf}_tcl{half}',f'sum_o[{bit}]',oh),xy(f'{lf}_tct',f'sum_i[{half*256+bit}]',ot)),f'tcl{half}.sum->tct',bit))
  # XREL alreadyexists: twoedges cancover<=1000, necessarynot sufficient.
  for bus in('w','x'):
   for bit in range(788):
    d=xy(f'{lf}_bdc',f'i_{bus}[{bit}]',ob)if bit<532 else xy(f'{lf}_tcl{(bit-532)//128}',f'i_{bus}[{(bit-532)%128}]',[oh0,oh1][(bit-532)//128]);dd=dist(xy(f'{lf}_xs',f'o_i{bus}[{bit}]',os),d);cur.append((dd/2,'xs->existingXREL->column',bit))
  lm,face,lrr=landing(lf,os);mx=max(lm,max(x[0]for x in cur));viol=sum(x[0]>500for x in cur)+sum(x['distance_um']>500for x in lrr)
  score=(viol,mx)
  if best is None or score<best[0]:best=(score,(os,ob,ot,oh0,oh1),cur,face,lrr)
 choices[lf]={'orientations':dict(zip(['xs','bdc','tct','tcl0','tcl1'],best[1])),'over500_endpoints':best[0][0],'maximum_effective_edge_lowerbound_um':best[0][1],'bank_output_face':best[3],'landing_pairs':best[4],'compute_pair_checks':[dict(effective_edge_lowerbound_um=d,kind=k,bit=i)for d,k,i in best[2]],'qualification':'XRELlegsuseoptimisticD/2lowerboundnotlegalrelayplacement; directTCLsumisactualpinreach.'}
rowout=[]
for lf in range(2):
 b=B[f'{lf}_rowE'];rowout.append({'leaf':lf,'best_possible_horizontal_to_Eboundary_um':g['W']-b['x']-b['w'],'minimum_added_edges':max(0,math.ceil((g['W']-b['x']-b['w'])/500)-1)})
verdict='FAIL'if any(v['over500_endpoints']for v in choices.values())or any(v['minimum_added_edges']for v in rowout)else 'NECESSARY_PIN_GATE_PASS_FULL_PARENT_FORK_AND_CLOCKROUTES_UNPROVEN'
out={'verdict':verdict,'candidate':a.candidate,'frame':[g['W'],g['H']],'area':g['area'],'legal_orientation_search_count':2*4**5,'compute_and_landing':choices,'row_output_lowerbounds':rowout,'still_required':['Full2069commonreceiverQ→threechildD actualpinmap','ActualrowWfirst/last/rowEactualLEFpairs','AllTCTBDCG1gather/control/reset/clockpins','Boundary3705distincttrackslots andcuts','ExistingXRELphysicalstationlegmaps notD/2bound','Newbanknativeclock/pins/TTFF/DRC0']};pathlib.Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'verdict':verdict,'area':g['area'],'leaves':{k:{z:v[z]for z in ['orientations','over500_endpoints','maximum_effective_edge_lowerbound_um']}for k,v in choices.items()},'row_output_lowerbounds':rowout},indent=2))
