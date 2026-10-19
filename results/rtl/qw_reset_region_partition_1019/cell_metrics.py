import odb,json,pathlib
P=pathlib.Path('/work');out={}
for name in ['qfd_rst_rep','qfd_rst_rep_p8']:
 d=odb.dbDatabase.create();odb.read_db(d,str(P/(name+'.odb')));b=d.getChip().getBlock();u=b.getDbUnitsPerMicron()
 out[name]={i.getMaster().getName():dict(width_um=i.getMaster().getWidth()/u,height_um=i.getMaster().getHeight()/u,area_um2=i.getMaster().getWidth()*i.getMaster().getHeight()/u**2) for i in b.getInsts()}
(P/'cell_metrics.json').write_text(json.dumps(out,indent=1))
print('METRICS_DONE',flush=True)
