import hashlib,json,tempfile,unittest
from pathlib import Path
import cluster_pg_phase as C

class Phase(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.s=dict(name='rg6',top='ot_rg6');self.g=dict(sha256='grantdigest')
 def tearDown(self):self.tmp.cleanup()
 def ref(self,name,text):
  p=self.root/name;p.write_text(text);return dict(source=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 def lef(self,name,origin,size,shift=0,swap=False,width=.48):
  x,y=origin;v=[f'MACRO {name}',f' SIZE {size} BY {size} ;']
  for net,n in [('VSS',0),('VDD',1)]:
   off=10+n*4.5455+shift
   v+=[f' PIN {net}',f' USE {"GROUND" if net=="VSS" else "POWER"} ;',' PORT']
   o=10+(1-n if swap else n)*4.5455+shift
   v+=[' LAYER M8 ;',f' RECT {x} {y+o} {x+size} {y+o+width} ;',' LAYER M9 ;',f' RECT {x+o} {y} {x+o+width} {y+size} ;',' END',f' END {net}']
  v+=[f'END {name}'];return '\n'.join(v)+'\n'
 def audit(self,shift=0,swap=False,width=.48,placement=100):
  r=dict(schema='opentallas.cluster-pg-phase.v1',master='rg6',grant_sha256='grantdigest',instance='vm6',
         die_pg_view=self.ref('die.lef',self.lef('die',(100,100),300)),
         cluster_view=self.ref('child.lef',self.lef('ot_rg6',(0,0),40,shift,swap,width)),
         die_def=self.ref('die.def',f'UNITS DISTANCE MICRONS 1000 ;\nCOMPONENTS 1 ;\n- vm6 ot_rg6 + FIXED ( {placement*1000} 100000 ) N ;\nEND COMPONENTS\n'))
  return self.ref('audit.json',json.dumps(r))
 def test_actual_geometry_matches(self):
  result=C.validate(self.root,self.audit(),self.s,self.g)
  self.assertEqual(result['origin_um'],[100,100]);self.assertEqual(result['stripes'],dict(M8=2,M9=2))
 def test_phase_shift_refused(self):
  with self.assertRaises(ValueError):C.validate(self.root,self.audit(shift=.01),self.s,self.g)
 def test_wrong_net_refused(self):
  with self.assertRaises(ValueError):C.validate(self.root,self.audit(swap=True),self.s,self.g)
 def test_wrong_width_refused(self):
  with self.assertRaises(ValueError):C.validate(self.root,self.audit(width=.4),self.s,self.g)
 def test_actual_def_placement_required(self):
  with self.assertRaises(ValueError):C.validate(self.root,self.audit(placement=101),self.s,self.g)
 def test_pass_marker_insufficient(self):
  ref=self.ref('weak.json',json.dumps(dict(verdict='PASS',master='rg6',grant_sha256='grantdigest')))
  with self.assertRaises(ValueError):C.validate(self.root,ref,self.s,self.g)
 def test_changed_physical_source_refused(self):
  ref=self.audit();(self.root/'child.lef').write_text('mutant')
  with self.assertRaises(ValueError):C.validate(self.root,ref,self.s,self.g)
 def test_partial_95_percent_rail_refused(self):
  ref=self.audit()
  child=self.lef('ot_rg6',(0,0),40).replace('RECT 0 10.0 40 10.48','RECT 0 10.0 38 10.48')
  self.assertIn('RECT 0 10.0 38 10.48',child)
  record=json.loads((self.root/'audit.json').read_text())
  record['cluster_view']=self.ref('child.lef',child)
  ref=self.ref('audit.json',json.dumps(record))
  with self.assertRaises(ValueError):C.validate(self.root,ref,self.s,self.g)

if __name__=='__main__':unittest.main()
