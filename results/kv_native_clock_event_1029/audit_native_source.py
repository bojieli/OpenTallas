import odb,json,collections
D=odb.dbDatabase.create();odb.read_db(D,'native_source/clock_native.odb');b=D.getChip().getBlock();u=b.getDbUnitsPerMicron();t=json.load(open('body_pack02/tree_native.json'));actual={};bad=[]
for i in b.getInsts():
 q=i.getBBox();r=(q.xMin(),q.yMin(),q.xMax(),q.yMax());n=i.getName();actual[n]=r
 expected=tuple(round(z*u) for z in t['sites'][n]);
 if r[:2]!=expected or r[2]-r[0]!=1620 or r[3]-r[1]!=270 or str(i.getOrient())!='R0' or str(i.getPlacementStatus())!='FIRM' or r[0]%54 or r[1]%540:bad.append([n,r,expected,str(i.getOrient()),str(i.getPlacementStatus())])
active=[];over=[]
for n,r in sorted(actual.items(),key=lambda p:p[1][0]):
 active=[(k,s) for k,s in active if s[2]>r[0]]
 for k,s in active:
  if s[1]<r[3] and s[3]>r[1]:over.append([n,k])
 active.append((n,r))
assert set(actual)==set(t['sites'])
out=dict(cells=len(actual),native_mismatch=len(bad),body_overlap_pairs=len(over),sample_bad=bad[:10],sample_overlap=over[:10],verdict='PASS' if not bad and not over else 'FAIL',scope='clock-only native source; provider and PG not integrated')
json.dump(out,open('native_source/audit.json','w'),indent=1);print(json.dumps(out));assert out['verdict']=='PASS'
