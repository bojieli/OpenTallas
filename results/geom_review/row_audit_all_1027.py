import os,odb,json,bisect,collections,re
D=odb.dbDatabase.create();odb.read_db(D,os.environ['ODB']);B=D.getChip().getBlock();U=B.getDbUnitsPerMicron();rows={}
for r in B.getRows():
 bb=r.getBBox();rows.setdefault(bb.yMin(),[]).append((bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax(),r.getOrient(),r.getName()))
ys=sorted(rows);bad=[];checked=0;orients=collections.Counter();filt=os.environ.get('INST_REGEX','')
def rail(o):return 0 if o in ('R0','MY') else 1 if o in ('MX','R180') else o
for i in B.getInsts():
 n=i.getName()
 if 'DFF' not in i.getMaster().getName() or (filt and not re.search(filt,n)):continue
 bb=i.getBBox();x=(bb.xMin()+bb.xMax())/2;y=(bb.yMin()+bb.yMax())/2;j=bisect.bisect_right(ys,y)-1;cand=[] if j<0 else[r for r in rows[ys[j]] if r[0]<=x<r[2] and r[1]<=y<r[3]]
 checked+=1;orients[i.getOrient()]+=1
 if not any(rail(r[4])==rail(i.getOrient()) for r in cand):bad.append(dict(inst=n,orient=i.getOrient(),xy_um=[bb.xMin()/U,bb.yMin()/U],expected_orient=sorted(set(r[4] for r in cand))))
print('ROW_AUDIT '+json.dumps(dict(checked=checked,bad=len(bad),orientations=dict(orients),first_bad=bad[:30],scope='all placed DFFs by default; R0/MY and MX/R180 rail equivalence; no placement edits')))
