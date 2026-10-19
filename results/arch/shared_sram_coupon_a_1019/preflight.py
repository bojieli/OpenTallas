import odb, openroad, inspect
print('ENCODER', [x for x in dir(odb.dbWireEncoder) if not x.startswith('_')])
for x in ['newPath','addPoint','addRect','addTechVia','begin','end']:
 print('DOC',x,getattr(odb.dbWireEncoder,x).__doc__)
print('LAYERMETHODS',[x for x in dir(odb.dbTechLayer) if any(k in x.lower() for k in ['rect','width','spacing','grid','corner','eol'])])
print('TECHMETHODS',[x for x in dir(odb.dbTech) if 'Layer' in x or 'Grid' in x])
