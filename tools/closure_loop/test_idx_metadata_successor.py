"""Small contract/refusal witnesses; no native execution or result publication."""
import tempfile
import unittest
from pathlib import Path
import idx_metadata_successor as S


def binding(h="1" * 64):
    return {"path": "/unmounted/exact/input", "sha256": h}


def fixture():
    c = dict(schema="opentallas.idx_pg_metadata_successor.v1", original_job=S.JOB,
        original_status="CLOSED", original_pg_qualification="PG_HOLD",
        claim="native_pg_metadata_corrected", parent_adoption=False, full_token_qualified=False,
        timing_provenance=S.TIMING, geometry_fingerprint=S.GEOMETRY,
        routed_source_commit="2727e1f68fe35352898f603aa751441ae447096f",
        gate_snapshot_scope="pre-route gate only; not routed source fingerprint",
        snapshot_reconstruction_status="exact routed per-file source/helper/native-LEF/Lib binding required; original archive unavailable",
        unresolved_qualifications=sorted(S.UNRESOLVED), clone_packet_commit="39021a45e",
        native_mterm_proof_commit="a92a4017131b6e7a7582c6011a72b057c6d1227f",
        reviewed_native_collector_sha256="86ecd58dcc68419006b65d773c832ac6feeaf7ecdcf39dbf9f8f442f868bb5c4",
        reviewed_native_audit_sha256="33c83927a7b4102a684e98fa1a829278031dbcd0432bafe57ca022edb27d290a",
        view_provenance="byte-identical predecessor geometry/timing; not regenerated from clone",
        predecessor_publish_status="AUTO-MERGE CONFLICT (4 source files); unpublished", global_index_eligible=False,
        original_odb=binding(S.ORIGINAL), clone_odb=binding(S.CLONE), original_spef=binding(S.SPEF),
        lineage={k:[binding()] for k in S.LINEAGE},
        reviewed_proofs={k:binding(v) for k,v in S.PROOF_HASHES.items()},
        invariants=dict(pg_binds=644, instances=322, native_pg_terms=196864,
            full_def_equals_reviewed_clone=True, all_geometry_signal_protection_unchanged=True),
        result_directory=S.RESULT_ROOT+"/idx256_pgmeta_review_20261019_001",
        successor_view_name="idx256_pgmeta_review_20261019_001",
        actions=["hash_all_inputs", "native_pg_recensus_exact_clone", "copy_complete_predecessor_views_unchanged",
            "hash_all_inputs_again", "write_new_successor_record_exclusive"])
    for name, hashes in S.LINEAGE_HASHES.items():
        c["lineage"][name] = [binding(h) for h in sorted(hashes)]
    for key in ("exporter_source", "native_pg_collector", "native_pg_audit", "pg_receipt_runner", "openroad_binary", "approved_pg_callback"):
        c[key] = binding()
    c["native_pg_collector"]["path"] = "/unmounted/exact/native_pg_binding.tcl"
    c["native_pg_audit"]["path"] = "/unmounted/exact/audit_native_pg.tcl"
    c["expected_domain_rules_sha256"] = "1"*64
    c["exporter_source"] = binding(S.digest(S.__file__))
    c["predecessor_view_root"] = "/unmounted/exact/views"
    c["predecessor_views"] = {n:{"path":c["predecessor_view_root"]+"/"+n,"sha256":"1"*64} for n in ("block.lef", "block_tt.lib")}
    c["complete_predecessor_view_inventory_sha256"] = S.json_digest(c["predecessor_views"])
    return c


class ContractTests(unittest.TestCase):
    def test_schema_only_never_authorizes_execution(self):
        r = S.validate(fixture(), verify_files=False)
        self.assertEqual(r["state"], "SCHEMA_ONLY")
        self.assertFalse(r["execution_authorized"])
        self.assertFalse(r["historical_receipt_is_freshness_authority"])

    def test_export_cannot_start_without_exact_root_approval(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(S.Refused, "exact ROOT approval"):
                S.export_after_root_review(fixture(), root_approval={}, repository_root=td)
            self.assertEqual(list(Path(td).iterdir()), [])

    def test_actual_files_missing_refuse(self):
        with self.assertRaisesRegex(S.Refused, "missing or symbolic"):
            S.validate(fixture())

    def test_all_policy_widening_and_unapproved_action_refuse(self):
        cases = {"original_status":"PASS", "original_pg_qualification":"PASS", "parent_adoption":True,
            "full_token_qualified":True, "timing_provenance":"re-extracted", "geometry_fingerprint":"0"*64,
            "global_index_eligible":True, "predecessor_publish_status":"published", "unresolved_qualifications":[],
            "claim":"closed", "clone_packet_commit":"other", "view_provenance":"generated from clone",
            "native_mterm_proof_commit":"a92", "actions":["submit_exact"]}
        for key, value in cases.items():
            with self.subTest(key=key), self.assertRaises(S.Refused):
                c=fixture(); c[key]=value; S.validate(c, verify_files=False)

    def test_exact_artifact_and_source_hashes_refuse(self):
        for key in ("original_odb", "clone_odb", "original_spef", "exporter_source"):
            with self.subTest(key=key), self.assertRaises(S.Refused):
                c=fixture(); c[key]=binding("0"*64); S.validate(c, verify_files=False)
        for key in S.PROOFS:
            with self.subTest(proof=key), self.assertRaises(S.Refused):
                c=fixture(); c["reviewed_proofs"][key]=binding("0"*64); S.validate(c, verify_files=False)

    def test_missing_any_lineage_refuses(self):
        for key in S.LINEAGE:
            with self.subTest(key=key), self.assertRaises(S.Refused):
                c=fixture(); del c["lineage"][key]; S.validate(c, verify_files=False)

    def test_pre_gate_snapshot_cannot_be_relabelled_routed_source(self):
        c=fixture(); c["lineage"]["snapshot_archive"]=[binding("1861a67a289a1b7b4d802212b6292f86d466b78d5fbc826eb7fe05907e370cf0")]
        with self.assertRaisesRegex(S.Refused, "pre-gate fingerprints"):
            S.validate(c, verify_files=False)

    def test_view_inventory_and_traversal_refuse(self):
        for name in ("../old/block.lef", "/absolute.lef", "a/../block.lef"):
            with self.subTest(name=name), self.assertRaises(S.Refused):
                c=fixture(); c["predecessor_views"][name]=binding()
                c["complete_predecessor_view_inventory_sha256"]=S.json_digest(c["predecessor_views"])
                S.validate(c, verify_files=False)
        c=fixture(); c["predecessor_views"]["block.lef"]["sha256"]="2"*64
        with self.assertRaisesRegex(S.Refused, "view inventory changed"):
            S.validate(c, verify_files=False)

    def test_result_cannot_reuse_original_or_shared_view_directory(self):
        for value in ("physical/ref_tile/old/views", S.RESULT_ROOT, S.RESULT_ROOT+"/../old"):
            with self.subTest(value=value), self.assertRaises(S.Refused):
                c=fixture(); c["result_directory"]=value; S.validate(c, verify_files=False)

    def test_stale_or_symbolic_file_binding_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"input"; p.write_text("before")
            b={"path":str(p), "sha256":S.digest(p)}
            S.file_binding(b, verify_files=True)
            p.write_text("after")
            with self.assertRaisesRegex(S.Refused, "stale"):
                S.file_binding(b, verify_files=True)
            link=Path(td)/"alias"; link.symlink_to(p)
            with self.assertRaisesRegex(S.Refused, "symbolic"):
                S.file_binding({"path":str(link), "sha256":S.digest(p)}, verify_files=True)


if __name__ == "__main__":
    unittest.main()
