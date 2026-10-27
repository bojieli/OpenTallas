"""Exact closed-view reach evidence admits a new route; it never qualifies it."""
import copy
import hashlib
import json
import unittest
import test_closed_stands as B
import closed_stands as C

class NativeReach(unittest.TestCase):
 def setUp(self):
  self.repo=B.Repo().put('aaaaaaaaa',pv='M7').put('bbbbbbbbb',pv='M7')
  self.repo.c['a'*36]=copy.deepcopy(self.repo.c['aaaaaaaaa'])
  self.old=B.hist();self.sp=B.spec(reroute_reason=dict(kind='native_reach',source='results/proof.json',fix='move same-face pins; zero added edges'))
  self.audit=dict(schema='opentallas.native_all_driver_endpoint_audit.v5',odb_sha256='a'*64,
   drivers=10,native_cells=20,missing_or_unknown=[],unknown_std_masters=[],
   max_L1_pin_centers_um=450,max_L1_pin_bbox_upper_um=451,
   reach_over405=[dict(driver='u0/Q',worst_sink='u1/D',endpoints=['u1/D'],max_L1_pin_centers_um=450)])
  self.proof=dict(schema='opentallas.native_reach_reroute.v1',closed_job=self.old['name'],
   closed_source_commit='a'*40,block='ot_t',native_receipt='results/native.json',odb_sha256='a'*64)
  self.oldplan=dict(top='ot_t',outline={'w':17.28,'h':64.8},pins={'W':['d']},pin_ranges={'d':[1,5]})
  self.newplan=copy.deepcopy(self.oldplan);self.newplan['pin_ranges']['d']=[2,6]
  self.sync()
 def sync(self):
  raw=json.dumps(self.audit);self.proof['native_receipt_sha256']=hashlib.sha256(raw.encode()).hexdigest()
  self.repo.c['bbbbbbbbb'].update({'results/native.json':raw,'results/proof.json':json.dumps(self.proof),
    'physical/ref_tile/t/spec.json':json.dumps(self.newplan)})
  self.repo.c['a'*36]['physical/ref_tile/t/spec.json']=json.dumps(self.oldplan)
 def check(self):
  return C.check(self.sp,self.sp['name'],[self.old],self.repo.show,self.repo.blob)
 def refused(self):
  self.assertEqual(self.check()['verdict'],'REFUSE',self.check())
 def test_exact_native_fail_and_changed_coordinates_admit_only(self):
  r=self.check();self.assertEqual(r['verdict'],'PASS',r)
  self.assertIn('admission only',r['message']);self.assertIn('fresh gate/native qualification required',r['message'])
 def test_wrong_job_source_block_or_schema_refuse(self):
  for key,value in [('closed_job','another'),('closed_source_commit','b'*40),('closed_source_commit','a'*9),('block','other'),('schema','witness')]:
   with self.subTest(key=key):
    saved=copy.deepcopy(self.proof);self.proof[key]=value;self.sync();self.refused();self.proof=saved
 def test_uncommitted_absolute_traversal_missing_sources_refuse(self):
  for path in ('/tmp/proof.json','../proof.json','results/../proof.json','results/absent.json'):
   with self.subTest(path=path):
    self.sp['reroute_reason']['source']=path;self.refused()
 def test_raw_path_and_digest_or_odb_mismatch_refuse(self):
  for key,value in [('native_receipt','/tmp/raw.json'),('native_receipt','../raw.json'),('odb_sha256','b'*64)]:
   with self.subTest(key=key):
    saved=copy.deepcopy(self.proof);self.proof[key]=value;self.sync();self.refused();self.proof=saved
  self.sync();self.repo.c['bbbbbbbbb']['results/native.json']+=' ';self.refused()
 def test_no_violation_unknown_or_partial_native_census_refuses(self):
  for key,value in [('reach_over405',[]),('missing_or_unknown',['pin']),('unknown_std_masters',['m']),('drivers',0),('native_cells',True),('max_L1_pin_centers_um',None),('schema','unsupported-witness')]:
   with self.subTest(key=key):
    saved=copy.deepcopy(self.audit);self.audit[key]=value;self.sync();self.refused();self.audit=saved
 def test_bad_or_nonfinite_path_measurement_refuses(self):
  for key,value in [('driver',''),('worst_sink','unlisted'),('endpoints',[]),('max_L1_pin_centers_um',405),('max_L1_pin_centers_um',float('inf')),('max_L1_pin_centers_um',float('nan'))]:
   with self.subTest(key=key):
    saved=copy.deepcopy(self.audit);self.audit['reach_over405'][0][key]=value;self.sync();self.refused();self.audit=saved
 def test_same_geometry_metadata_only_or_malformed_ranges_refuse(self):
  for plan in (self.oldplan,dict(self.oldplan,why='move it'),dict(self.newplan,pin_ranges={'d':[float('nan'),6]}),dict(self.newplan,pin_ranges={'d':[7,6]})):
   self.newplan=copy.deepcopy(plan);self.sync();self.refused()
 def test_changed_outline_faces_rtl_parameters_or_layer_refuse(self):
  for mutate in ('outline','faces','rtl','params','layer'):
   with self.subTest(mutate=mutate):
    self.setUp()
    if mutate=='outline':self.newplan['outline']['w']=99
    if mutate=='faces':self.newplan['pins']={'E':['d']}
    if mutate=='rtl':self.repo.c['bbbbbbbbb']['rtl/t/ot_t.sv']='module changed;endmodule'
    if mutate=='params':self.repo.c['bbbbbbbbb']['physical/ref_tile/t/kit.env']=self.repo.c['bbbbbbbbb']['physical/ref_tile/t/kit.env'].replace('--param W=512','--param W=1024')
    if mutate=='layer':self.repo.c['bbbbbbbbb']['physical/ref_tile/t/kit.env']=self.repo.c['bbbbbbbbb']['physical/ref_tile/t/kit.env'].replace("PIN_V='M7'","PIN_V='M5'")
    self.sync()
    if mutate=='params':
     # Different known parameters identify a new block under the existing gate.
     self.assertEqual(self.check()['verdict'],'NA')
    else:self.refused()
 def test_new_reason_does_not_waive_clock_source_binding(self):
  import source_binding as SB
  self.assertEqual(self.check()['verdict'],'PASS')
  ok,_=SB.relaxed_rule_requirement(['clock_pin_spread'],{'tt_pin_spread_ps':81,'ff_pin_spread_ps':50,'tt_pair_skew_ps':81,'ff_pair_skew_ps':50},gate={'spec':self.sp})
  self.assertFalse(ok)

 def test_every_reported_offending_path_is_checked(self):
  self.audit['reach_over405'].append(dict(driver='u2/Q',worst_sink='u3/D',endpoints=['u3/D'],max_L1_pin_centers_um=float('nan')))
  self.sync();self.refused()
 def test_missing_geometry_source_cannot_be_replaced_by_metadata(self):
  self.repo.c['bbbbbbbbb'].pop('physical/ref_tile/t/spec.json')
  self.sp['reroute_reason']['geometry']={'pin_ranges':{'d':[2,6]}}
  self.refused()
 def test_changed_route_faces_cannot_hide_in_unchanged_spec_json(self):
  self.repo.c['bbbbbbbbb']['physical/ref_tile/t/kit.env']=self.repo.c['bbbbbbbbb']['physical/ref_tile/t/kit.env'].replace('=left','=right')
  self.refused()
