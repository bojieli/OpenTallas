import os,json,pathlib
rows=[]; errors=[]
for d in pathlib.Path('/proc').iterdir():
 if not d.name.isdigit(): continue
 r={'pid':int(d.name),'links':[]}
 try:r['cmd']= (d/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
 except FileNotFoundError:continue
 except PermissionError:errors.append(str(d/'cmdline'));continue
 for name in ['cwd','exe','root']:
  try:r['links'].append(os.readlink(d/name))
  except FileNotFoundError:pass
  except PermissionError:errors.append(str(d/name))
 try:
  for f in (d/'fd').iterdir():
   try:r['links'].append(os.readlink(f))
   except FileNotFoundError:pass
   except PermissionError:errors.append(str(f))
  r['maps']=(d/'maps').read_text(errors='replace')
 except FileNotFoundError:pass
 except PermissionError:errors.append(str(d))
 rows.append(r)
print(json.dumps({'rows':rows,'errors':errors}))
