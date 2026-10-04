import importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("split",ROOT/"tools/dsrom_split_domain_parent_model.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ModelTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.x=m.build();cls.edges={e["name"]:e for e in cls.x["prospective_edges"]}
 def test_actual_wide_ports(self):
  p=self.x["current_named_core_ports"]
  self.assertEqual(p["xs_rd_q"]["bits"],32768);self.assertEqual(p["rom_fr"]["bits"],8832)
 def test_profiles_not_transferred(self):
  self.assertEqual(self.x["current_runtime_profile"]["ROM_PHW"],6)
  self.assertEqual(self.x["prospective_selected_profile"]["ROM_PHW"],10)
  self.assertEqual(self.edges["field_visible_row_write"]["source_bits"],4032)
 def test_root_bound(self):
  c=self.x["phase_source_census"];self.assertEqual(c["phases"],46509)
  self.assertTrue(all(w["max_rows_per_root"]==64 and w["max_total_rows"]==4096 for w in c["worst"]))
 def test_journal_no_return_credit(self):
  a=self.x["area"];self.assertEqual(a["AR_fullphase_journal_bits"],64*64*69)
  self.assertEqual(a["full_return_storage_retained_bits"],138469120);self.assertEqual(a["full_return_storage_credit_bits"],0)
 def test_adapter_ports(self):
  self.assertEqual(self.edges["collective_write4"]["source_bits"],4+4*15+4*512)
  self.assertEqual(self.edges["CKV_service_id_read_reply"]["source_bits"],512)
  self.assertEqual(self.edges["rope_cache_snapshot_lease_reply"]["source_bits"],2072)
 def test_command_not_stub(self):
  e=self.edges["QE_command"]
  self.assertEqual(e["source_bits"],3+sum(v["bits"] for v in e["members"]))
  self.assertEqual(next(v["bits"] for v in e["members"] if v["name"]=="qe_xbase"),30)
  self.assertIn("resolved",e["source_basis"])
 def test_finite_credits_and_rate(self):
  for e in self.edges.values():
   self.assertEqual(e["outstanding_credit_seats"],8)
   self.assertEqual(e["packet_bits"],e["source_bits"]+48)
   self.assertEqual(e["rate_words_per_hyperperiod"],3)
 def test_no_free_tracks(self):
  self.assertEqual(self.x["routing"]["sum_independent_crossing_signal_tracks"],sum(e["packet_bits"] for e in self.edges.values()))
  self.assertEqual(self.x["routing"]["assumed_multiplexing_credit"],0)
 def test_peer_failure_not_promoted(self):
  c=self.x["CKV_peer_binding"]
  self.assertEqual(c["successor_owner"],"Epicurus");self.assertEqual(c["installed_binary_binding"],"UNPROVEN")
  self.assertNotIn("ag_rx_ready",c["remote_RX_ports"])
  self.assertTrue(c["retained_service_hash_matches_peer"])
  self.assertIn("STILL writes",c["source_equations"]["RX_fault"])
 def test_no_hardware_admission(self):
  self.assertFalse(self.x["admission"]["engine_RTL_admitted"])
  self.assertFalse(self.x["admission"]["physical_build_admitted"])
  self.assertFalse(self.x["new_engine_RTL"])
 def test_archive_hashes(self):
  for r in m.load(m.BASE/"inputs/origins.json"):
   self.assertEqual(m.sha(m.BASE/"inputs"/r["copy"]),r["sha256"])
 def test_parser_rejects_unknown(self):
  with self.assertRaises(ValueError):m.ports("module x #(parameter P=1) (interface bus);",{})
 def test_mixed_xu_not_blind_clock_transfer(self):
  self.assertEqual(self.x['current_runtime_profile']['X_EG'],0)
  self.assertIn('OP_SINK=1',self.edges['XU_block_read_request']['mode_condition'])
 def test_reverse_visible_lane_receipts(self):
  e=self.edges['field_visible_row_write_reverse_receipt']
  self.assertEqual(e['source_bits'],4+1+1+1+64)
  self.assertIn('every enabled lane',e['source_basis'])
 def test_unique_edge_names(self):self.assertEqual(len(self.edges),len(self.x["prospective_edges"]))
if __name__=="__main__":unittest.main()
