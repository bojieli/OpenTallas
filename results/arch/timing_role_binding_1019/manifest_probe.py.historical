#!/usr/bin/env python3
"""Structural admission witnesses only; fixtures are never timing libraries."""
import copy,hashlib,json,pathlib,tempfile
import role_manifest as R
ident=dict(master=R.MASTER,**{k:'a'*64 for k in R.IDENTITY-{'master'}})
with tempfile.TemporaryDirectory() as d:
 p=pathlib.Path(d);m={'schema':'opentallas.sc2-timing-roles.prototype.v1','identity':ident,'roles':{}}
 for role in sorted(R.ROLES):
  lib=R.MASTER+'_'+role;f=p/(role+'.lib');f.write_text('library ('+lib+') { cell ('+R.MASTER+') {} }\n')
  m['roles'][role]=dict(file=f.name,sha256=R.digest(f),library=lib,corner=role[:2],analysis=role[3:],domain={'slew_ps':[5,320],'load_ff':[0.72,46.08]},constraint_policy='upper_requirements',added_access_minimum_delay_ps=0)
 cases={'positive':m,'missing':copy.deepcopy(m),'swapped':copy.deepcopy(m),'stale_source':copy.deepcopy(m),'positive_access_min':copy.deepcopy(m)}
 del cases['missing']['roles']['ff_min']
 cases['swapped']['roles']['ff_min'],cases['swapped']['roles']['ff_max']=cases['swapped']['roles']['ff_max'],cases['swapped']['roles']['ff_min']
 cases['stale_source']['identity']=dict(ident,source_sha256='b'*64)
 cases['positive_access_min']['roles']['ff_min']['added_access_minimum_delay_ps']=1
 lines=[]
 for case,obj in cases.items():
  f=p/'manifest.json';f.write_text(json.dumps(obj));h=R.digest(f)
  try:R.read(f,h,ident,R.ROLES);assert case=='positive';lines.append(case+' PASS structural schema only')
  except ValueError as e:assert case!='positive';lines.append(case+' '+str(e))
 f=p/'manifest.json';f.write_text(json.dumps(m))
 for case,expected,roles in [('tt_minimum',R.digest(f),{'tt_min'}),('ss_minimum',R.digest(f),{'ss_min'}),('unreviewed_digest','b'*64,R.ROLES)]:
  try:R.read(f,expected,ident,roles);raise AssertionError(case)
  except ValueError as e:lines.append(case+' '+str(e))
 pathlib.Path(__file__).with_name('manifest_witness.log').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
