"""Require a source-bound routed phase audit before capture parent adoption."""
import hashlib
import json
import math
import shlex
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(view, state_root, db_hash=None):
    """Validate the CLOSED producer, exported views, actual DB and phase proof.

    The audit writer records actual hashes before any scratch cleanup. During
    adoption the DB is rehashed locally or on its known closure-loop host.
    db_hash is an injection point for isolated validation tests only.
    """
    receipt = json.loads((view / "routed_phase_audit.json").read_text())
    if receipt.get("schema") != "opentallas.capture.routed_phase_audit.v1":
        raise ValueError("capture phase audit: unsupported or missing receipt")
    job_name = receipt["job"]
    if Path(job_name).name != job_name:
        raise ValueError("capture phase audit: unsafe job name")
    job = json.loads((state_root / "jobs" / (job_name + ".json")).read_text())
    if job["status"] != "CLOSED":
        raise ValueError("capture phase audit: producer is not CLOSED")
    source = job["commit_full"]
    if receipt["source_commit"] != source:
        raise ValueError("capture phase audit: producer source mismatch")
    binding = receipt["source_binding"]
    import source_binding
    if binding.get("schema") != source_binding.SCHEMA or not binding.get("files"):
        raise ValueError("capture phase audit: missing immutable source binding")
    if source_binding.canonical_digest(binding["files"]) != binding["manifest_sha256"]:
        raise ValueError("capture phase audit: corrupt source manifest")
    tree = source_binding.git_files(Path(__file__).resolve().parents[2], source)
    gate = subprocess.run(["git", "-C", str(Path(__file__).resolve().parents[2]), "show",
                           source + ":physical/ref_tile/dsfd_capt_x8_dual/gate_result.json"],
                          check=True, capture_output=True, text=True)
    if json.loads(gate.stdout)["source_binding"]["manifest_sha256"] != binding["manifest_sha256"]:
        raise ValueError("capture phase audit: receipt differs from producer gate snapshot")
    if any(e["source"] == "working_tree" and tree.get(e["path"]) != e["git_blob"] for e in binding["files"]):
        raise ValueError("capture phase audit: snapshot differs from routed source")
    required = {"insertion.json", "abstract.json", view.name + ".lef"}
    required.update(view.name + "_" + c + ".lib" for c in ("tt", "ff", "ss"))
    if not required.issubset(receipt["view_sha256"]):
        raise ValueError("capture phase audit: incomplete view binding")
    for name, expected in receipt["view_sha256"].items():
        if Path(name).name != name or sha(view / name) != expected:
            raise ValueError("capture phase audit: exported view changed: " + name)
    ins = json.loads((view / "insertion.json").read_text())
    if ins["parasitics"] != "spef" or ins["db"] != "6_final.odb":
        raise ValueError("capture phase audit: insertion must use final routed SPEF")
    db = str(Path(ins["base"]) / ins["db"])
    if receipt["routed_db"]["path"] != db or not db.startswith(job["run"] + "/routes/"):
        raise ValueError("capture phase audit: DB is not the CLOSED producer's DB")
    if db_hash is None:
        local_db = Path(db)
        if local_db.is_file():
            actual = sha(local_db)
        else:
            result = subprocess.run(["ssh", job["host"], "sha256sum -- " + shlex.quote(db)],
                                    check=True, capture_output=True, text=True)
            actual = result.stdout.split()[0]
    else:
        actual = db_hash(db)
    if actual != receipt["routed_db"]["sha256"]:
        raise ValueError("capture phase audit: routed DB changed")
    if receipt["phase"] != "pin_source_latency_minus_boundary_R" or receipt["parasitics"] != "spef":
        raise ValueError("capture phase audit: expected routed compensated clock phase")
    if receipt["period_ps"] != {"core": 833.333, "serial": 1111.110667}:
        raise ValueError("capture phase audit: nominal related periods required")
    if receipt["setup_uncertainty_ps"] != 60 or receipt["hold_uncertainty_ps"] != 25:
        raise ValueError("capture phase audit: uncertainty changed")
    if receipt["cross_domain_exceptions"]:
        raise ValueError("capture phase audit: crossing exceptions forbidden")
    for corner in ("tt", "ff"):
        for port in ("ck", "ckv"):
            measured = ins["clock_measurements"].get(port) or ins["clock_measurements"].get(port + "[0]")
            r = measured[corner]["boundary"]["mean"]
            if not math.isfinite(r) or receipt["clock_R_ps"][corner][port] != r:
                raise ValueError("capture phase audit: actual per-clock R mismatch")
    seen = set()
    for p in receipt["paths"]:
        key = (p["corner"], p["launch"], p["capture"], p["sense"])
        if key in seen or not p["startpoint"] or not p["endpoint"]:
            raise ValueError("capture phase audit: duplicate or missing actual path")
        seen.add(key)
        if not math.isfinite(p["slack_ps"]) or p["slack_ps"] < 0:
            raise ValueError("capture phase audit: compensated timing fails: " + str(key))
    expected = {(c, a, b, s) for c in ("tt", "ff") for a, b in (("core", "serial"), ("serial", "core")) for s in ("max", "min")}
    if seen != expected:
        raise ValueError("capture phase audit: both directions and max/min TT/FF required")
    for name in ("audit.tcl", "audit.log"):
        if sha(view / name) != receipt["audit_sha256"][name]:
            raise ValueError("capture phase audit: audit evidence changed")
    logged = [json.loads(line.removeprefix("OT_CAPTURE_PHASE "))
              for line in (view / "audit.log").read_text().splitlines()
              if line.startswith("OT_CAPTURE_PHASE ")]
    if logged != receipt["paths"]:
        raise ValueError("capture phase audit: receipt paths differ from actual audit log")
    return receipt
