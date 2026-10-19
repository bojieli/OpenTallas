#!/usr/bin/env python3
"""ROOT erratum refusal witnesses, no valid Liberty or numerical bounds."""
import json,pathlib,tempfile
import role_manifest as R
ident=dict(master=R.MASTER,**{k:'a'*64 for k in R.IDENTITY-{'master'}})
lines=[]
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d)/'manifest.json'
 m={'schema':'opentallas.sc2-timing-roles.prototype.v1','identity':ident,'roles':{r:{} for r in R.ROLES}}
 for name,roles in [('tt_minimum',{'tt_min'}),('ss_minimum',{'ss_min'}),('ff_minimum',{'ff_min'}),('max_only_hidden_min',{'tt_max'}),('all_roles',R.ROLES)]:
  p.write_text(json.dumps(m))
  try:R.read(p,R.digest(p),ident,roles);raise AssertionError('unsafe admission '+name)
  except ValueError as e:
   assert 'MIN unqualified' in str(e);lines.append(name+' '+str(e))
pathlib.Path(__file__).with_name('manifest_witness.log').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
