"""Review-only IDX PG metadata successor contract; never submits or edits a ledger.

The CLI validates and prints a plan. There is deliberately no export command.
An eventual executor must obtain ROOT review of the complete populated contract,
then call pg_receipt.require_native_pg on the active exact clone immediately before
copying any views. A historical PASS receipt is never freshness authority.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

JOB = "hdie_col_idx256_1019-fan32g1-2727e1f68"
ORIGINAL = "851903b3ea016e159ac50862a1c80c5b3f4c6276e13df27789182736ce4e72c6"
CLONE = "22e4a3d00d57b5d0b9c69e92bd26b4ca351b95b179f3fce416c065a34e79821a"
SPEF = "a86653e98ff953e441f905ec66347cec4a7dd5cfb453b33f3903b59a8e2c29a2"
GEOMETRY = "b44057faf45222632b3bb2eb75a32eb13868819d5b17a28754ceae394f891c4d"
TIMING = "inherited unchanged signal geometry/SPEF; not re-extracted"
RESULT_ROOT = "results/physical/hdie_col_idx256_1019_pg_metadata_successor_1019"
UNRESOLVED = {"parent_any_prm", "nf5_die_binding", "neighbor_matching", "production_throughput", "full_su_mu_token", "source_to_netlist_equivalence"}
LINEAGE = {"closure_record", "view_index", "rtl", "sdc", "lef", "liberty", "snapshot_archive", "snapshot_manifest", "helper_manifest", "pg_hold_review", "geometry_review"}
PROOF_HASHES = {'clone_summary.json': '515b3c0fea680378af85f7a599810cfdbe01fd4da250932d8976d1266653368e', 'def_invariants.log': '5eaf19d507c58b3669fc07a36fdf1f4c8b1a4e9f3db2e76eea254cd9a917925f', 'metal_proof.json': '5a080c7f2ebe652469a1f1c87aa1ac073b165570304af5858445adb6187b8174', 'clone_strict_summary.json': '899d342e7174d3ebfddfa787c12f0c625e9a11e520119c7f9c4bbd10caf6258f', 'after.def.gz': '1731b710c24f86b9ab1182277dac10d223e5395f2faad7df4f435a3ee698e1d5', 'after_raw.json.gz': '19180419b99135d2ae9239fe545fa283295d344022546120a5d1a1c61abce676'}
PROOFS = set(PROOF_HASHES)

LINEAGE_HASHES = {
    "closure_record": {"2bf7b05858818dca0aafc061ec77c2a7e7677ad2b244719e0f4a83f3003d3184", "29de08442272b264048c965774478eedcb38d602ef0da8e0e563dd243f31cc9d"},
    "view_index": {"71f91b69d1b2a402ebda96f82973884407ab90f806afc0c0686903ae67c849bc", "d135aacbc3e67a5ace97bb423c37e64156e31735325e0e13c69bc0ea707d81ec", "3728cfc1d89c7f95186ef0eb360ce5bfd58202a23551dec71986eb57886e4c3c"}}


class Refused(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Refused(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def file_binding(binding, *, verify_files):
    require(isinstance(binding, dict) and set(binding) == {"path", "sha256"}, "missing/extra file binding fields")
    require(isinstance(binding["path"], str) and binding["path"], "missing exact file path")
    require(sha(binding["sha256"]), "missing exact file hash")
    if verify_files:
        p = Path(binding["path"])
        require(p.is_file() and not p.is_symlink(), "missing or symbolic input: " + str(p))
        require(digest(p) == binding["sha256"], "stale input: " + str(p))


def validate(c, *, verify_files=True):
    """Validate only; no subprocess, imports of native tools, writes or publication.

    verify_files=False is for schema/refusal tests only and cannot produce an
    executable plan: its returned state is SCHEMA_ONLY, never READY_FOR_REVIEW.
    """
    require(c.get("schema") == "opentallas.idx_pg_metadata_successor.v1", "unknown schema")
    require(c.get("original_job") == JOB, "wrong predecessor job")
    require(c.get("original_status") == "CLOSED" and c.get("original_pg_qualification") == "PG_HOLD", "history relabelled")
    require(c.get("claim") == "native_pg_metadata_corrected", "claim widened")
    require(c.get("parent_adoption") is False and c.get("full_token_qualified") is False, "adoption forbidden")
    require(c.get("timing_provenance") == TIMING, "timing provenance changed")
    require(c.get("geometry_fingerprint") == GEOMETRY, "geometry changed")
    require(set(c.get("unresolved_qualifications", [])) >= UNRESOLVED, "predecessor qualifications dropped")
    require(c.get("routed_source_commit") == "2727e1f68fe35352898f603aa751441ae447096f", "wrong routed source commit")
    require(c.get("gate_snapshot_scope") == "pre-route gate only; not routed source fingerprint", "pre-gate snapshot confused with routed source")
    require(c.get("snapshot_reconstruction_status") == "exact routed per-file source/helper/native-LEF/Lib binding required; original archive unavailable", "routed source reconstruction provenance missing")
    require(c.get("clone_packet_commit") == "39021a45e", "wrong reviewed clone lineage")
    require(c.get("native_mterm_proof_commit") == "a92a4017131b6e7a7582c6011a72b057c6d1227f", "native MTerm proof lineage missing")
    require(c.get("reviewed_native_collector_sha256") == "86ecd58dcc68419006b65d773c832ac6feeaf7ecdcf39dbf9f8f442f868bb5c4", "wrong historical native collector")
    require(c.get("reviewed_native_audit_sha256") == "33c83927a7b4102a684e98fa1a829278031dbcd0432bafe57ca022edb27d290a", "wrong historical native audit")
    require(c.get("view_provenance") == "byte-identical predecessor geometry/timing; not regenerated from clone", "view provenance changed")
    require(c.get("predecessor_publish_status") == "AUTO-MERGE CONFLICT (4 source files); unpublished", "predecessor publication relabelled")
    require(c.get("global_index_eligible") is False, "global index eligibility forbidden")
    for key, expected in (("original_odb", ORIGINAL), ("clone_odb", CLONE), ("original_spef", SPEF)):
        file_binding(c.get(key), verify_files=verify_files)
        require(c[key]["sha256"] == expected, "wrong " + key)
    lineage = c.get("lineage", {})
    require(set(lineage) == LINEAGE, "incomplete exact source/closure/helper/view lineage")
    for bindings in lineage.values():
        require(isinstance(bindings, list) and bool(bindings), "empty lineage binding")
        for binding in bindings:
            file_binding(binding, verify_files=verify_files)
    gate_only = {"1861a67a289a1b7b4d802212b6292f86d466b78d5fbc826eb7fe05907e370cf0", "5f8f01668eca42bd0d46ad03d609f593bf6f6c39fd9bf9aed6492611dbd6b628"}
    require(not any(b["sha256"] in gate_only for k in ("snapshot_archive", "snapshot_manifest") for b in lineage[k]), "pre-gate fingerprints cannot bind routed source")
    for name, hashes in LINEAGE_HASHES.items():
        require({b["sha256"] for b in lineage[name]} >= hashes, "wrong exact predecessor lineage: " + name)
    proofs = c.get("reviewed_proofs", {})
    require(set(proofs) == PROOFS, "reviewed conductor/fanout/DEF proof missing")
    for name, binding in proofs.items():
        file_binding(binding, verify_files=verify_files)
        require(binding["sha256"] == PROOF_HASHES[name], "reviewed proof changed: " + name)
    require(c.get("invariants") == {"pg_binds": 644, "instances": 322, "native_pg_terms": 196864,
        "full_def_equals_reviewed_clone": True, "all_geometry_signal_protection_unchanged": True}, "invariant scope changed")
    for key in ("exporter_source", "native_pg_collector", "native_pg_audit", "pg_receipt_runner", "openroad_binary", "approved_pg_callback"):
        file_binding(c.get(key), verify_files=verify_files)
    require(c["exporter_source"]["sha256"] == digest(__file__), "wrong exporter source")
    require(Path(c["native_pg_collector"]["path"]).resolve() == Path(c["native_pg_audit"]["path"]).resolve().with_name("native_pg_binding.tcl"), "collector must be exact audited sibling source")
    require(sha(c.get("expected_domain_rules_sha256")), "missing source-bound native domain snapshot")
    views = c.get("predecessor_views", {})
    require(isinstance(views, dict) and bool(views), "missing complete predecessor view inventory")
    require(any(p.endswith(".lef") for p in views) and any(p.endswith(".lib") for p in views), "abstract/timing views absent")
    view_root = Path(c.get("predecessor_view_root", ""))
    require(str(view_root) != ".", "missing predecessor view root")
    if verify_files:
        require(view_root.is_dir() and not view_root.is_symlink(), "invalid predecessor view root")
        entries = list(view_root.rglob("*"))
        require(not any(p.is_symlink() for p in entries), "symbolic predecessor view entry")
        require({str(p.relative_to(view_root)) for p in entries if p.is_file()} == set(views), "incomplete predecessor view inventory")
    for name, binding in views.items():
        p = PurePosixPath(name)
        require(not p.is_absolute() and ".." not in p.parts and str(p) == name, "unsafe view path")
        file_binding(binding, verify_files=verify_files)
        require(Path(binding["path"]) == view_root / name, "view binding outside complete inventory root")
    require(sha(c.get("complete_predecessor_view_inventory_sha256")), "missing complete view inventory commitment")
    require(json_digest(views) == c["complete_predecessor_view_inventory_sha256"], "view inventory changed")
    result = PurePosixPath(c.get("result_directory", ""))
    require(result.parent == PurePosixPath(RESULT_ROOT) and len(result.name) >= 12, "result must use unique immutable directory")
    view = c.get("successor_view_name", "")
    require(view.startswith("idx256_pgmeta_") and len(view) > 26 and "/" not in view, "unique successor view name missing")
    require(c.get("actions") == ["hash_all_inputs", "native_pg_recensus_exact_clone", "copy_complete_predecessor_views_unchanged", "hash_all_inputs_again", "write_new_successor_record_exclusive"], "unapproved action")
    return {"state": "READY_FOR_REVIEW" if verify_files else "SCHEMA_ONLY", "contract_sha256": json_digest(c),
        "result_directory": str(result), "successor_view_name": view, "timing_provenance": TIMING,
        "execution_authorized": False, "historical_receipt_is_freshness_authority": False}


def export_after_root_review(c, *, root_approval, repository_root):
    """Dormant prototype. ROOT must review this exact source+contract before calling.

    No caller-supplied native receipt is accepted. Native work belongs on fleet.
    Failures leave the new exclusive directory/audit logs intact; existing output
    is never reused. Copies are inherited views, never a claim of regeneration.
    This function has no CLI switch and no daemon/index/submit integration.
    """
    require(root_approval == {"decision": "ROOT_APPROVED_EXACT_IDX_SUCCESSOR",
        "contract_sha256": json_digest(c), "exporter_sha256": digest(__file__)}, "exact ROOT approval required")
    validate(c)
    import importlib.util
    import shutil
    runner = Path(c["pg_receipt_runner"]["path"])
    spec = importlib.util.spec_from_file_location("idx_successor_pinned_pg_receipt", runner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = Path(repository_root).resolve(strict=True)
    result = root / c["result_directory"]
    # This dedicated results parent may be made only after exact approval.
    ancestor = root
    for part in PurePosixPath(RESULT_ROOT).parts:
        ancestor = ancestor / part
        require(not ancestor.is_symlink(), "symbolic output ancestor")
        require(not ancestor.exists() or ancestor.is_dir(), "output ancestor is not a directory")
    result.parent.mkdir(parents=True, exist_ok=True)
    require(result.parent.resolve() == root / RESULT_ROOT, "symbolic output ancestor")
    result.mkdir()  # exclusive; an existing successful OR failed run refuses
    try:
        receipt = module.require_native_pg(c["clone_odb"]["path"],
            collector=c["native_pg_audit"]["path"], openroad=c["openroad_binary"]["path"],
            receipt_dir=result / "native_pg_audit")
        require(receipt.get("status") == "PASS" and receipt.get("failure_count") == 0,
            "fresh native PG audit did not pass")
        require(receipt.get("odb_sha256") == CLONE and receipt.get("checked") == 196864
            and receipt.get("roles") == {"POWER":98432, "GROUND":98432}, "incomplete native census")
        require(receipt.get("binding_scope") == "native_master_pg_terminal_binding_only", "native scope changed")
        expected_dependencies = {str(Path(c[k]["path"]).resolve()):c[k]["sha256"]
            for k in ("pg_receipt_runner", "native_pg_audit", "native_pg_collector")}
        require(receipt.get("source_dependencies") == expected_dependencies, "executed native sources changed")
        require(receipt.get("openroad_sha256") == c["openroad_binary"]["sha256"], "native executable changed")
        require(receipt.get("domain_rules_sha256") == c["expected_domain_rules_sha256"], "native domain snapshot changed")
        # Callback and reviewed current rules are evidence; recensus above is the
        # freshness authority. Native conductor proofs remain separately pinned.
        receipt_path = Path(receipt["receipt_path"])
        require(receipt_path.resolve().is_relative_to((result / "native_pg_audit").resolve()), "receipt escaped exclusive run")
        copied = {}
        def copy_exact(binding, relative):
            destination = result / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with Path(binding["path"]).open("rb") as src, destination.open("xb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            require(digest(destination) == binding["sha256"], "copy/hash mismatch: " + relative)
            copied[relative] = binding["sha256"]
            destination.chmod(0o444)
        copy_exact(c["clone_odb"], "artifacts/clone.odb")
        copy_exact(c["original_spef"], "timing/original.spef")
        for name, binding in c["predecessor_views"].items():
            copy_exact(binding, "views/" + c["successor_view_name"] + "/" + name)
        for category in ("closure_record", "pg_hold_review", "geometry_review", "view_index"):
            for index, binding in enumerate(c["lineage"][category]):
                copy_exact(binding, "history/" + category + "/" + str(index) + "_" + Path(binding["path"]).name)
        validate(c)  # reject source/input mutation during collector or copying
        record = {"schema":"opentallas.idx_pg_metadata_successor_record.v1", "contract":c,
            "contract_sha256":json_digest(c), "root_approval":root_approval,
            "native_pg_receipt_sha256":digest(receipt_path), "native_pg_receipt":receipt,
            "exported_files":copied, "claim":"native_pg_metadata_corrected",
            "view_provenance":c["view_provenance"], "timing_provenance":TIMING,
            "parent_adoption":False, "full_token_qualified":False, "global_index_eligible":False,
            "unresolved_qualifications":c["unresolved_qualifications"],
            "original_status":"CLOSED", "original_pg_qualification":"PG_HOLD",
            "predecessor_publish_status":c["predecessor_publish_status"]}
        with (result / "successor_record.json").open("x") as f:
            json.dump(record, f, indent=2, sort_keys=True)
            f.write("\n")
        (result / "successor_record.json").chmod(0o444)
        return result
    except Exception as exc:
        with (result / "FAILURE.json").open("x") as f:
            json.dump({"status":"REFUSED", "error":str(exc), "parent_adoption":False}, f)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("contract", type=Path)
    args = p.parse_args()
    try:
        print(json.dumps(validate(json.loads(args.contract.read_text())), indent=2))
    except (Refused, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"state": "REFUSED", "reason": str(exc), "execution_authorized": False}))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
