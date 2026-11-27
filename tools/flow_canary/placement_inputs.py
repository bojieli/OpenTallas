"""Capture the inputs consumed through placement of a generated type canary."""
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "opentallas.flow_canary.placement_inputs.v1"
STAGES = ("synth", "floorplan", "place")
DEFAULT_IMAGE = "openroad/orfs:asap7lock"
FIELDS = {"schema", "die", "item", "top", "threads", "mem_gb", "image", "image_id", "runner_env",
          "classifier", "capture_model", "stages"}
SHA = re.compile(r"[0-9a-f]{64}\Z")
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
HOST_REFERENCE = re.compile(rb"(?<![\w./])/(?:srv|home|mnt|media)/")
CONTROL_EXTENSIONS = {".mk", ".sh", ".tcl", ".py", ".ys", ".sdc", ".v", ".sv", ".svh", ".vh"}
RUNNER_ENV = re.compile(r"\$\{?(OT_[A-Z0-9_]+)\b")
# These exact stock helpers inspect scratch shape or unused host diagnostics.
# Their bytes still participate in the stock stage fingerprint.
HOST_INSPECTION = {
    "gp_noconverge.py": "e16c723d34c5d6aec02d71c39f73287178473afe3888cd6df7f0558fd811965c",
    "seal_gate.py": "ee1cfe63a83007fedcf9af46cb3668af2c9b905a7475e20cee2a0ca2b4bc2f5a",
}


def load_stage_model(kit):
    path = kit / "kit_resume.py"
    spec = importlib.util.spec_from_file_location("_canary_stage_model", path)
    if spec is None or spec.loader is None:
        raise ValueError("stock stage input model is unavailable")
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    return model


def host_reference(path):
    with path.open("rb") as stream:
        return any(HOST_REFERENCE.search(line) for line in stream
                   if not line.lstrip().startswith((b"#", b"//")))


def freeze_identity(kit, manifest, source):
    """Canonicalize the recorded reset-contract path only after proving its bytes."""
    filename = "freeze.json"
    if filename not in manifest["files"]:
        return None
    freeze = json.loads((kit / filename).read_text())
    reset = freeze.get("reset_contract")
    if not isinstance(reset, dict) or "contract" not in reset:
        return None
    if freeze.get("schema") != "opentallas.partition_freeze.v1" or not source:
        raise ValueError("unknown reset contract provenance")
    parent = Path(source).resolve()
    contract = Path(reset["contract"])
    if not contract.is_absolute() or not contract.resolve().is_relative_to(parent) or contract.is_symlink():
        raise ValueError("reset contract is outside the pinned source")
    copied = manifest["files"].get("reset_contract.json", {}).get("sha256")
    receipt = manifest["files"].get("reset_contract/receipt.txt", {}).get("sha256")
    if (not copied or copied != reset.get("contract_sha256") or not receipt or receipt != reset.get("receipt_sha256")
            or hashlib.sha256(contract.read_bytes()).hexdigest() != copied):
        raise ValueError("pinned and generated reset contract evidence differ")
    reset["contract"] = contract.resolve().relative_to(parent).as_posix()
    return digest(freeze)


def capture(kit, spec, image, model=None, source=None):
    """Return a comparable certificate for a fresh GEN, or refuse reuse on unknown inputs."""
    kit = Path(kit).resolve()
    runner = kit.parent / "run_kit.sh"
    if spec.get("flow") != "type" or (kit / "run/results").exists():
        raise ValueError("placement inputs require a fresh generated type kit")
    if (spec.get("vars") or {}).get("inputs"):
        raise ValueError("canary declares an external input snapshot")
    if any(path.is_symlink() for path in kit.rglob("*")):
        raise ValueError("generated kit contains a symbolic link")
    model = model or load_stage_model(kit)
    manifest = model.manifest(str(kit), runner=str(runner), image=image, with_checkpoint=False)
    if manifest.get("error") or not manifest.get("runner", {}).get("sha256"):
        raise ValueError("stock generated kit manifest is incomplete")
    image_id = manifest["image"].get("id")
    if not image_id or not IMAGE_ID.fullmatch(image_id):
        raise ValueError("worker image identity is absent")

    for rel, item in manifest["files"].items():
        path = kit / rel
        if not item["sha256"] or not path.resolve().is_relative_to(kit):
            raise ValueError(f"unverified generated input {rel}")
        if ((item["stage"] in STAGES or rel == "config.mk") and path.suffix in CONTROL_EXTENSIONS
                and item["sha256"] != HOST_INSPECTION.get(rel) and host_reference(path)):
            raise ValueError(f"generated placement input names a host path: {rel}")

    freeze = freeze_identity(kit, manifest, source)
    if freeze is not None:
        manifest["files"]["freeze.json"]["sha256"] = freeze
        manifest["fingerprints"] = model.fingerprints(manifest)

    # The generated runner is hashed by the stock synth key. Capture any worker
    # overrides it can read, without depending on the rest of the process env.
    runner_env = {name: os.environ[name] for name in set(RUNNER_ENV.findall(runner.read_text()))
                  if name in os.environ}
    if runner_env.get("OT_ORFS_IMAGE", DEFAULT_IMAGE) != image:
        raise ValueError("physical runner image and reviewed image differ")
    if runner_env.get("OT_DOCKER", "docker") != "docker":
        raise ValueError("runner uses a different container client")
    return {
        "schema": SCHEMA,
        "die": spec["die"],
        "item": spec["item"],
        "top": spec["top"],
        "threads": spec.get("threads", 8),
        "mem_gb": spec["mem_gb"],
        "image": image,
        "image_id": image_id,
        "runner_env": digest(runner_env),
        "classifier": hashlib.sha256((kit / "kit_resume.py").read_bytes()).hexdigest(),
        "capture_model": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "stages": {stage: manifest["fingerprints"][stage] for stage in STAGES},
    }


def valid(certificate):
    if not isinstance(certificate, dict) or set(certificate) != FIELDS or certificate["schema"] != SCHEMA:
        return False
    stages = certificate["stages"]
    return (isinstance(stages, dict) and set(stages) == set(STAGES)
            and all(isinstance(value, str) and SHA.fullmatch(value)
                    for value in (*stages.values(), certificate["classifier"], certificate["capture_model"],
                                  certificate["runner_env"]))
            and isinstance(certificate["image_id"], str) and IMAGE_ID.fullmatch(certificate["image_id"]) is not None)


def same_placement_inputs(current, previous):
    """Unknown or differently constructed certificates require native placement."""
    return valid(current) and valid(previous) and current == previous


def digest(certificate):
    return hashlib.sha256(json.dumps(certificate, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

CERTIFICATE = Path("harness/placement-inputs.json")
PRIOR = Path("harness/placement-prior.json")
PROPOSAL = Path("harness/placement-reuse-proposal.json")
PREFLIGHT = Path("harness/placement-reuse-preflight.json")
ACCEPTED = Path("placement_reuse.json")
REUSE_SCHEMA = "opentallas.flow_canary.placement_reuse.v1"


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=1) + "\n")
    temporary.replace(path)


def certified_previous(run, spec, review):
    """Read the cached baseline and its exact placement receipt without rescanning the kit."""
    metadata = read_json(run / "canary_meta.json")
    old_spec = metadata["spec"]
    if not metadata.get("review_before_route") or any(old_spec.get(k) != spec.get(k) for k in ("die", "item", "top")):
        return None
    lease = run / ".keep"
    if lease.is_symlink() or lease.read_text() != review.keep_text(run):
        return None
    receipt = review.receipt_path(run)
    placed = review.read_receipt(run)
    kit = Path(metadata["kit"])
    certificate = read_json(run / CERTIFICATE)
    if (not valid(certificate) or review.digest(run / CERTIFICATE) != placed.get("placement_inputs_file_sha256")
            or any(certificate[k] != spec[k] for k in ("die", "item", "top"))
            or placed["kit"] != str(kit) or placed["src_commit"] != metadata["src_commit"]
            or not kit.resolve().is_relative_to((run / "gen").resolve()) or not Path(placed["odb"]).is_file()
            or (run / "harness/route_approval.json").exists()):
        return None
    return {"run": run.name, "certificate": certificate, "receipt_sha256": review.digest(receipt),
            "odb_sha256": placed["odb_sha256"], "submitted_at": metadata.get("submitted_at", 0)}


def prepare_prior(run, spec, review):
    latest = None
    for older in run.parent.glob(f"{spec['die']}_*"):
        if older == run or older.is_symlink() or not (older / CERTIFICATE).is_file():
            continue
        try:
            prior = certified_previous(older, spec, review)
        except (KeyError, OSError, TypeError, ValueError):
            continue
        if prior is not None and (latest is None or prior["submitted_at"] > latest["submitted_at"]):
            latest = prior
    if latest is not None:
        write_json(run / PRIOR, latest)


def reuse_candidate(run):
    metadata = read_json(run / "canary_meta.json")
    prior = read_json(run / PRIOR)
    current = read_json(run / CERTIFICATE)
    lint = read_json(run / "lint.json")
    if lint.get("verdict") != "PASS" or not same_placement_inputs(current, prior["certificate"]):
        return None
    older = prior["run"]
    if older == run.name or Path(older).name != older or older in (".", ".."):
        raise ValueError("invalid previous canary scope")
    return {"schema": REUSE_SCHEMA, "src_commit": metadata["src_commit"], "prior_run": older,
            "placement_inputs_sha256": digest(current), "prior_receipt_sha256": prior["receipt_sha256"],
            "odb_sha256": prior["odb_sha256"]}


def proposed_reuse(run):
    candidate = reuse_candidate(run)
    if candidate is None:
        return None
    preflight = run / PREFLIGHT
    document = read_json(preflight)
    if document.get("verdict") != "PASS" or document.get("kit") != read_json(run / "canary_meta.json")["kit"]:
        return None
    return dict(candidate, preflight_sha256=hashlib.sha256(preflight.read_bytes()).hexdigest())


def has_physical_attempt(run):
    meta = read_json(run / "canary_meta.json")
    return (run / "gen/placement_review/placed.json").exists() or (Path(meta["kit"]) / "run/results").exists()


def accept_reuse(run, review):
    proposed = read_json(run / PROPOSAL)
    if not isinstance(proposed, dict) or proposed != proposed_reuse(run):
        raise ValueError("new generated inputs do not match the previous placement")
    meta = read_json(run / "canary_meta.json")
    if has_physical_attempt(run):
        raise ValueError("reuse response contains a new physical attempt")
    previous = run.parent / proposed["prior_run"]
    expected = read_json(run / PRIOR)
    if previous.is_symlink() or certified_previous(previous, meta["spec"], review) != expected:
        raise ValueError("previous placement receipt changed during generation")
    receipt = review.receipt_path(previous)
    placed = review.read_receipt(previous)
    review.validate_placement(Path(placed["kit"]), receipt, placed)
    write_json(run / ACCEPTED, proposed)
    return proposed


def accepted_reuse(run):
    """Read the coordinator's accepted result; a worker proposal alone is never terminal."""
    try:
        accepted = read_json(run / ACCEPTED)
        if accepted.get("schema") == REUSE_SCHEMA and accepted == proposed_reuse(run) and not has_physical_attempt(run):
            return accepted
        return None
    except (KeyError, OSError, TypeError, ValueError):
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "propose"))
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    if args.action == "propose" and not (args.run / PRIOR).is_file():
        return 1
    try:
        if args.action == "capture":
            metadata = read_json(args.run / "canary_meta.json")
            certificate = capture(metadata["kit"], metadata["spec"], metadata.get("image", DEFAULT_IMAGE),
                                  source=metadata["src"])
            write_json(args.run / CERTIFICATE, certificate)
        else:
            if reuse_candidate(args.run) is None:
                return 1
            kit = Path(read_json(args.run / "canary_meta.json")["kit"])
            result = subprocess.run([sys.executable, "-I", str(kit / "kit_preflight.py"), str(kit),
                                     "--out", str(args.run / PREFLIGHT)])
            if result.returncode:
                return 1
            proposal = proposed_reuse(args.run)
            if proposal is None:
                return 1
            write_json(args.run / PROPOSAL, proposal)
    except (KeyError, OSError, TypeError, ValueError) as error:
        print(f"CANARY PLACEMENT INPUTS: native placement required ({error})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
