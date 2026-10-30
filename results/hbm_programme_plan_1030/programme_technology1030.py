import json,pathlib,re,odb
K=pathlib.Path('/kit');db=odb.dbDatabase.create();odb.read_db(db,str(next(K.glob('run/results/asap7/*/base/3_2_place_iop.odb'))));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();R=lambda q:[q.xMin(),q.yMin(),q.xMax(),q.yMax()]
t=dict(dbu=u,core=R(b.getCoreArea()),rows=[],masters={},obstacles=[])
for row in b.getRows():t['rows'].append(dict(rect=R(row.getBBox()),site=row.getSite().getWidth(),orient=str(row.getOrient())))
for line in(K/'master_core_infra.tcl').read_text().splitlines():
 m=re.match(r'ot_ci_cell \{([^}]+)\} (\S+) ',line)
 if m:
  master=db.findMaster(m[2]);t['masters'][m[2]]=[master.getWidth(),master.getHeight()]
for i in b.getInsts():
 status=str(i.getPlacementStatus());master=i.getMaster()
 if master.isBlock()or status in('FIRM','LOCKED','COVER'):t['obstacles'].append(dict(name=i.getName(),kind='macro'if master.isBlock()else'fixed',rect=R(i.getBBox()),master=master.getName(),status=status))
pathlib.Path('/out/technology.json').write_text(json.dumps(t,indent=1)+'\n');print('ACTUAL_POSTTAP',len(t['rows']),'rows',len(t['obstacles']),'fixed/macro obstacles')
