"""Upper-metal cluster grants cannot silently relax tile or die obligations."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import ref_tile as RT

class ClusterGrant(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.rootpatch=patch.object(RT,'ROOT',self.root);self.rootpatch.start()
  self.rec=dict(schema='opentallas.cluster-layer-grant.v1',signal_cap='M9',masters=['rg6'],no_die_signal_through_traffic=True,die_pg_layers=['M8','M9'],die_pg=dict(width_um=.48,pitch_um=9.091),requires_phase_aligned_die_pg=True)
  self.s=dict(name='rg6',kind='cluster',signal_max_layer='M9',job=dict(hold_merge='routing pilot'))
 def tearDown(self):self.rootpatch.stop();self.tmp.cleanup()
 def grant(self):
  p=self.root/'grant.json';p.write_text(json.dumps(self.rec));self.s['cluster_layer_grant']=dict(source='grant.json',sha256=hashlib.sha256(p.read_bytes()).hexdigest())
 def test_unauthorized_m9_refused(self):
  with self.assertRaises(RT.SpecError):RT.cluster_signal_cap(self.s)
 def test_magic_string_refused(self):
  self.s['cluster_layer_grant']='die lead says yes'
  with self.assertRaises(RT.SpecError):RT.cluster_signal_cap(self.s)
 def test_authorized_probe_preserves_obligations(self):
  self.grant();cap,g=RT.cluster_signal_cap(self.s)
  self.assertEqual(cap,'M9');self.assertTrue(g['obligations']['requires_phase_aligned_die_pg'])
  self.assertTrue(g['obligations']['no_die_signal_through_traffic'])
 def test_changed_source_refused(self):
  self.grant();(self.root/'grant.json').write_text('{}')
  with self.assertRaises(RT.SpecError):RT.cluster_signal_cap(self.s)
 def test_other_master_refused(self):
  self.grant();self.s['name']='other'
  with self.assertRaises(RT.SpecError):RT.cluster_signal_cap(self.s)
 def test_through_traffic_refused(self):
  self.rec['no_die_signal_through_traffic']=False;self.grant()
  with self.assertRaises(RT.SpecError):RT.cluster_signal_cap(self.s)
 def test_missing_phase_obligation_refused(self):
  self.rec.pop('requires_phase_aligned_die_pg');self.grant()
  with self.assertRaises(RT.SpecError):RT.cluster_signal_cap(self.s)
 def test_production_needs_phase_audit(self):
  self.grant();self.s['job']={}
  with self.assertRaises(RT.SpecError):RT.cluster_signal_cap(self.s)
 def test_default_cluster_unchanged(self):
  self.s.pop('signal_max_layer');self.assertEqual(RT.cluster_signal_cap(self.s),('M7',None))
 def test_tiles_still_refuse_m9(self):
  self.grant();self.s.update(kind='tile',layer_cap='M9')
  with self.assertRaises(RT.SpecError):RT.tile_cap(self.s,None)
 def test_m6_is_stricter_without_moving_cluster_pg_or_strap(self):
  self.s.update(signal_max_layer='M6',children=[],pg_layer='M7')
  lc=RT.layer_contract(self.s,None)
  self.assertEqual(lc['rlayers'],('M2','M6'))
  self.assertEqual(lc['pg_layer'],'M7');self.assertEqual(lc['strap_layer'],'M8')
  self.assertEqual(lc['signal_max_layer'],'M6')
 def test_slot_ceiling_inherited_and_cannot_be_widened(self):
  self.s.pop('signal_max_layer')
  self.assertEqual(RT.cluster_signal_cap(self.s,dict(signal_max_layer='M6')),('M6',None))
  self.s['signal_max_layer']='M7'
  with self.assertRaises(RT.SpecError):RT.cluster_signal_cap(self.s,dict(signal_max_layer='M6'))
 def test_m6_cannot_change_pg_or_allow_lower_unproven_layers(self):
  self.s.update(signal_max_layer='M6',children=[],pg_layer='M6')
  with self.assertRaises(RT.SpecError):RT.layer_contract(self.s,None)
  self.s['signal_max_layer']='M5'
  with self.assertRaises(RT.SpecError):RT.cluster_signal_cap(self.s)
 def test_m6_requires_actual_net_type_audit_in_route_and_export(self):
  s=RT.load_spec(str(Path(__file__).parent/'examples/nhb_pbst_ref.json'))
  s.update(kind='cluster',children=[],pg_layer='M7',signal_max_layer='M6')
  hooks=RT.gen_hooks(s,'kit')
  self.assertIn('ot_ref_audit_signal_layers M6 M7',hooks['post_drt.tcl'])
  self.assertIn('tools/ref_tile/signal_layer_audit.tcl',RT.referenced_paths(s,'kit'))
  kit=self.root/'kit';kit.mkdir()
  (kit/'floorplan.json').write_text(json.dumps(dict(top='actual_cluster',layer_contract=RT.layer_contract(s,None))))
  with patch('subprocess.run') as run:
   run.return_value.returncode=0
   RT.export(str(self.root/'absent_route'),'kit',str(self.root/'out'),[])
   cmd=run.call_args_list[0].args[0]
  self.assertEqual(cmd[cmd.index('--signal-max-layer')+1],'M6')
  self.assertEqual(cmd[cmd.index('--pg-max-layer')+1],'M7')
  self.assertIn('--signal-audit-tcl',cmd)

if __name__=='__main__':unittest.main()
