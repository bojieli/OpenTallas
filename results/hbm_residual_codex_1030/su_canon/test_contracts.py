import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[3]
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
P=module('tools/die_plan/parent_id_straps.py','parent_ids');S=module('physical/die_plan/hbm_arch_cores/static_id_contracts.py','static_ids')
class Contracts(unittest.TestCase):
 def descriptor(self,m,w,v):return dict(module=m,physical_id_alias={'strap_lane_lane_id':'lane_lane_id'},straps=[dict(port='strap_lane_lane_id',width=w,value=v)])
 def test_exact_rows(self):
  for m,w in S.SU_ID_WIDTHS.items():
   for v in (0,1,(1<<w)-1):
    d=self.descriptor(m,w,v);self.assertEqual(P.validate_parent_id_straps(d,{'strap_lane_lane_id':w},actual_module=m),{'strap_lane_lane_id':dict(width=w,value=v)})
    self.assertEqual(P.logical_id_straps(d),{'lane_lane_id':dict(width=w,value=v)})
    self.assertEqual(S.static_inputs(m,{'strap_lane_lane_id':w},{'strap_lane_lane_id':'input'}),['strap_lane_lane_id'])
 def test_schema_width_and_literal_pairs(self):
  import jsonschema
  schema=module('tools/die_plan/schema.py','schema')
  for w in (9,11):
   jsonschema.validate([dict(port='strap_lane_lane_id',width=w,value=format(1,'0'+str(w)+'b').join([str(w)+"'b",'']))],schema._core_id_straps)
   with self.assertRaises(jsonschema.ValidationError):jsonschema.validate([dict(port='strap_lane_lane_id',width=w,value=1<<w)],schema._core_id_straps)
  with self.assertRaises(jsonschema.ValidationError):jsonschema.validate([dict(port='strap_lane_lane_id',width=9,value="11'b00000000001")],schema._core_id_straps)
 def test_counterexamples(self):
  for m,w in S.SU_ID_WIDTHS.items():
   for change in ('wrongmodule','wrongwidth','nativephysical','wrongnative','nomap','outofrange','actualwrong'):
    d=self.descriptor(m,w,1);inp={'strap_lane_lane_id':w};actual=m
    if change=='wrongmodule':d['module']=m+'_other';actual=d['module']
    if change=='wrongwidth':d['straps'][0]['width']=9 if w==11 else 11
    if change=='nativephysical':d['parent_id_straps']={'lane_lane_id':dict(width=w,value=1)}
    if change=='wrongnative':d['physical_id_alias']['strap_lane_lane_id']='fault'
    if change=='nomap':del d['physical_id_alias']
    if change=='outofrange':d['straps'][0]['value']=1<<w
    if change=='actualwrong':actual=m+'_other'
    with self.assertRaises(ValueError,msg=(m,change)):P.validate_parent_id_straps(d,inp,actual_module=actual)
   with self.assertRaises(ValueError):S.static_inputs(m,{'lane_lane_id':w},{'lane_lane_id':'input'})
if __name__=='__main__':unittest.main()
