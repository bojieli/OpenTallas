import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import check_macro_instance_tracks_strict as C
ROOT=Path(__file__).resolve().parents[1]
TRACKS='results/uarch/dsrom_noECC_production_context_20261002/inputs/make_tracks.tcl'
RF='ot_sram_1r1w_128x256_m1_r2c2';SCRATCH='ot_sram_1r1w_1024x256_m2_r2c2'

def real_manifest():
    return {'schema':C.SCHEMA,'frozen_checker_sha256':C.FROZEN_SHA,'tracks':{'path':TRACKS,'sha256':C.sha(ROOT/TRACKS)},'row_site':{'x_origin_nm':0,'y_origin_nm':0,'site_pitch_nm':54,'row_pitch_nm':270,'site_count':10000,'row_count':10000},'instances':[{'name':'rf_mirror','macro':RF,'lef':{'path':f'physical/asap7_memory_macros/{RF}/{RF}.lef','sha256':C.sha(ROOT/f'physical/asap7_memory_macros/{RF}/{RF}.lef')},'orientation':'MX','x_nm':0,'y_nm':1080},{'name':'scratch_mirror','macro':SCRATCH,'lef':{'path':f'physical/asap7_memory_macros/{SCRATCH}/{SCRATCH}.lef','sha256':C.sha(ROOT/f'physical/asap7_memory_macros/{SCRATCH}/{SCRATCH}.lef')},'orientation':'MX','x_nm':0,'y_nm':1890}]}

SYNTH='''VERSION 5.7 ;
MACRO m
 CLASS BLOCK ;
 SIZE 10 BY 10 ;
 SYMMETRY X Y ;
 PIN a
 USE SIGNAL ;
 PORT
 LAYER M4 ;
 RECT 0.000 0.000 0.024 0.024 ;
 END
 END a
 PIN b
 USE SIGNAL ;
 PORT
 LAYER M6 ;
 RECT 0.000 0.000 0.032 0.028 ;
 END
 END b
END m
END LIBRARY
'''

class StrictInstances(unittest.TestCase):
 def test_real_mirror_residues_and_all_centres(self):
  r=C.preflight(real_manifest(),ROOT);self.assertTrue(r['status'].startswith('PASS'))
  self.assertEqual([x['signal_RECT_centres_checked'] for x in r['instances']],[819,829]);self.assertEqual([x['y_nm']%48 for x in r['instances']],[24,18])
  self.assertFalse(r['DRC_via_PG_SS_FF_qualified'])
 def test_real_origin_zero_mutants(self):
  for index in (0,1):
   m=real_manifest();m['instances'][index]['y_nm']=0
   self.assertEqual(C.preflight(m,ROOT)['status'],'REFUSE_OFFTRACK_INSTANCE')
 def test_wrong_orientation(self):
  m=real_manifest();m['instances'][0]['orientation']='R0';self.assertEqual(C.preflight(m,ROOT)['status'],'REFUSE_OFFTRACK_INSTANCE')
 def test_rotation_rejected(self):
  for o in ('R90','R270','MXR90','MYR90','UNKNOWN'):
   m=real_manifest();m['instances'][0]['orientation']=o
   with self.assertRaises(C.Refuse):C.preflight(m,ROOT)
 def test_wrong_grid(self):
  for key in ('x_nm','y_nm'):
   m=real_manifest();m['instances'][0][key]+=1
   with self.assertRaises(C.Refuse):C.preflight(m,ROOT)
 def test_nonzero_grid_origin_and_finite_extent(self):
  m=real_manifest();m['instances']=m['instances'][:1];m['row_site']['y_origin_nm']=1080;m['row_site']['row_count']=1
  self.assertTrue(C.preflight(m,ROOT)['status'].startswith('PASS'))
  m['instances'][0]['y_nm']+=2160
  with self.assertRaises(C.Refuse):C.preflight(m,ROOT)
 def test_hash_mutant(self):
  for obj in ('tracks','lef'):
   m=real_manifest();v=m['tracks'] if obj=='tracks' else m['instances'][0]['lef'];v['sha256']='0'*64
   with self.assertRaises(C.Refuse):C.preflight(m,ROOT)
 def test_empty_unknown_dynamic_tracks(self):
  for t in ('','# no tracks','make_tracks Alien -x_offset 0 -x_pitch 0.048 -y_offset 0 -y_pitch 0.048','source other.tcl','make_tracks M4 -x_offset 0 -x_pitch 0 -y_offset 0 -y_pitch 0.048'):
   with self.assertRaises(C.Refuse):C.strict_tracks(t)
 def test_unsupported_geometry_and_unknown_layer(self):
  for bad in (SYNTH.replace('RECT 0.000 0.000 0.024 0.024 ;','POLYGON 0 0 1 1 0 1 ;'),SYNTH.replace('LAYER M4','LAYER M99'),SYNTH.replace('RECT 0.000 0.000 0.024 0.024 ;',''),SYNTH.replace('SIZE 10 BY 10 ;','SIZE 10 BY 10 ;\n ORIGIN 0.001 0 ;')):
   with self.assertRaises(C.Refuse):C.strict_lef(bad)
 def test_missing_signal_layer_and_incompatible_alllayer_intersection(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'m.lef';p.write_text(SYNTH);m=real_manifest();m['instances']=[{'name':'mixed','macro':'m','lef':{'path':str(p),'sha256':C.sha(p)},'orientation':'R0','x_nm':0,'y_nm':0}]
   r=C.preflight(m,ROOT);self.assertEqual(r['status'],'REFUSE_OFFTRACK_INSTANCE');self.assertEqual(r['instances'][0]['layers'],{'M4':1,'M6':1})
   t=Path(d)/'tracks.tcl';t.write_text('make_tracks M4 -x_offset 0.009 -x_pitch 0.036 -y_offset 0.012 -y_pitch 0.048\n');m['tracks']={'path':str(t),'sha256':C.sha(t)}
   with self.assertRaises(C.Refuse):C.preflight(m,ROOT)
 def test_unknown_macro_noinstances_no_symmetry(self):
  m=real_manifest();m['instances'][0]['macro']='unknown'
  with self.assertRaises(C.Refuse):C.preflight(m,ROOT)
  m['instances']=[]
  with self.assertRaises(C.Refuse):C.preflight(m,ROOT)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'m.lef';p.write_text(SYNTH.replace('SYMMETRY X Y ;',''));m=real_manifest();m['instances']=[dict(m['instances'][0],macro='m',lef={'path':str(p),'sha256':C.sha(p)})]
   with self.assertRaises(C.Refuse):C.preflight(m,ROOT)
 def test_half_nm_centre_not_rounded(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'m.lef';p.write_text(SYNTH.replace('0.024 0.024','0.024 0.025'));m=real_manifest();m['instances']=[dict(m['instances'][0],macro='m',orientation='R0',y_nm=0,lef={'path':str(p),'sha256':C.sha(p)})]
   self.assertEqual(C.preflight(m,ROOT)['status'],'REFUSE_OFFTRACK_INSTANCE')
 def test_duplicate_attribute_and_precision_refused(self):
  for text in (SYNTH.replace('USE SIGNAL ;','USE SIGNAL ;\n USE POWER ;',1),SYNTH.replace('0.024 0.024','0.024 0.0241'),SYNTH.replace('CLASS BLOCK ;',''),SYNTH.replace('RECT 0.000','RECT MASK 1 0.000',1)):
   with self.assertRaises(C.Refuse):C.strict_lef(text)
 def test_manifest_unknown_fields_and_boolean_grid(self):
  m=real_manifest();m['unchecked_placement']='other'
  with self.assertRaises(C.Refuse):C.preflight(m,ROOT)
  m=real_manifest();m['row_site']['row_pitch_nm']=True
  with self.assertRaises(C.Refuse):C.preflight(m,ROOT)
 def test_multiple_RECT_centres_conjunctive(self):
  text=SYNTH.replace('RECT 0.000 0.000 0.024 0.024 ;','RECT 0.000 0.000 0.024 0.024 ;\n RECT 0.024 0.001 0.048 0.025 ;')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'m.lef';p.write_text(text);m=real_manifest();m['instances']=[dict(m['instances'][0],macro='m',orientation='R0',y_nm=0,lef={'path':str(p),'sha256':C.sha(p)})]
   r=C.preflight(m,ROOT);self.assertEqual(r['instances'][0]['signal_RECT_centres_checked'],3);self.assertEqual(r['status'],'REFUSE_OFFTRACK_INSTANCE')
 def test_cli_failclosed(self):
  with tempfile.TemporaryDirectory() as d:
   m=real_manifest();m['instances'][0]['orientation']='R90';p=Path(d)/'manifest.json';p.write_text(json.dumps(m));o=Path(d)/'out.json'
   r=subprocess.run([sys.executable,str(ROOT/'tools/check_macro_instance_tracks_strict.py'),'--manifest',str(p),'--root',str(ROOT),'--json',str(o)],capture_output=True)
   self.assertEqual(r.returncode,1);self.assertEqual(json.loads(o.read_text())['status'],'REFUSE_INPUT_COVERAGE')
if __name__=='__main__':unittest.main()
