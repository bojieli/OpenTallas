"""Prototype producer receipt for a publication-prepared, same-path place attempt."""

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import shlex
import sys
import tempfile

SCHEMA = "opentallas.published_place_ready.v1"
INPUTS = ".kw_inputs.json"
INPUTS_SCHEMA = "opentallas.kw_stage_resume.v1"
REQUIRED = ("kit_rtl", "kit_topology", "gen", "gen_kit", "gen_lint", "preflight")
SCHEDULING_ONLY = {
    "dry_gen", "start_delay_s", "place_mem_gb", "place_threads", "place_prefer",
    "hosts", "roam_hosts", "place_spill", "crit", "ot_run",
}


def digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def generation_identity(spec):
    # Work path, event, source/plan, every recipe, and producer are intentionally retained.
    return digest({k: v for k, v in spec.items() if k not in SCHEDULING_ONLY})


def signature(path):
    owner = path.lstat()
    if not stat.S_ISREG(owner.st_mode):
        raise ValueError(f"prepared dependency is not a regular file: {path.name}")
    return [owner.st_dev, owner.st_ino, owner.st_size, owner.st_ctime_ns]


def path_layout(spec):
    root = Path(spec["work"])
    item = spec["item"]
    if not root.is_absolute() or root.resolve() != root or not re.fullmatch(r"[A-Za-z0-9_]+", item):
        raise ValueError("expected exact producer work directory and type selector")
    if spec.get("kind") != "type" or spec.get("kit_rtl", {}).get("mode") != "bind":
        raise ValueError("prototype supports actual native-bound partition types")
    return root, root / "gen" / item


def capture(spec, result, stages, form_sha, plan_sha, preflight):
    """Called on the physical producer with the controller's actual completed stages."""
    root, kit = path_layout(spec)
    source = result["src_manifest"]
    identity = {"manifest": spec["src_manifest_hash"], "plan": plan_sha, "form": form_sha}
    if not all(re.fullmatch(r"[0-9a-f]{64}", v) for v in identity.values()):
        raise ValueError("prepared identity requires full source, plan and form digests")
    if (source.get("manifest_hash") != identity["manifest"] or source.get("host") != spec["gen_host"]
            or source.get("tree") != spec["src"] or source.get("tree_read_only") is not True):
        raise ValueError("earlier producer receipt must cover this immutable source")
    if (result.get("evidence") != f"{spec['gen_host']}:{kit}" or result.get("stage") != "preflight"
            or result.get("verdict") != "DRY-PASS" or result.get("preflight_fail_advisory")
            or any(stages.get(stage) != 0 for stage in REQUIRED)):
        raise ValueError("exact strict preparation did not finish")
    preflight = Path(preflight)
    if preflight.parent != root or not re.fullmatch(r"preflight\.[0-9]+\.json", preflight.name):
        raise ValueError("PRE receipt is not this attempt's write-once output")
    checked = json.loads(preflight.read_text())
    if checked.get("kit") != str(kit) or checked.get("verdict") != "PASS":
        raise ValueError("stock PRE report did not qualify the prepared kit")

    manifest = kit / INPUTS
    raw = manifest.read_bytes()
    stock = json.loads(raw)
    if (stock.get("schema") != INPUTS_SCHEMA or not stock.get("files")
            or "config.mk" not in stock["files"] or not any(n.startswith("rtl/") for n in stock["files"])):
        raise ValueError("expected the existing stock kit input inventory including RTL and config")
    files = {}
    for name in stock["files"]:
        path = kit / name
        if Path(name).is_absolute() or ".." in Path(name).parts or path.resolve() != path:
            raise ValueError(f"invalid generated input path: {name}")
        files[str(path.relative_to(root))] = signature(path)
    files[str(manifest.relative_to(root))] = signature(manifest)
    files[str(preflight.relative_to(root))] = signature(preflight)
    files["gen/run_kit.sh"] = signature(root / "gen/run_kit.sh")
    return {
        "schema": SCHEMA, **identity, "generation_identity": generation_identity(spec),
        "producer": spec["gen_host"], "work": str(root), "kit": str(kit),
        "inputs_sha256": hashlib.sha256(raw).hexdigest(), "preflight": str(preflight),
        "stages": {key: stages[key] for key in REQUIRED}, "files": files,
    }


def verify(receipt, spec, accepted_publication, current_review):
    """Validate a same-host prepared kit after exact publication and ordinary plan review."""
    root, kit = path_layout(spec)
    source = {"manifest": receipt["manifest"], "plan": receipt["plan"], "form": receipt["form"]}
    if accepted_publication != {"verdict": "PASS", "manifest": source["manifest"], "plan": source["plan"]}:
        raise ValueError("current publication does not authorize the prepared source")
    if current_review != {"verdict": "GOOD", "form": source["form"]}:
        raise ValueError("current committed review does not authorize this source form")
    if (receipt.get("schema") != SCHEMA or receipt["generation_identity"] != generation_identity(spec)
            or receipt["producer"] != spec["gen_host"] or receipt["work"] != str(root) or receipt["kit"] != str(kit)
            or any(receipt["stages"].get(stage) != 0 for stage in REQUIRED)):
        raise ValueError("prepared recipe, location or producer differs")
    for rel, saved in receipt["files"].items():
        path = root / rel
        if Path(rel).is_absolute() or ".." in Path(rel).parts or path.resolve() != path or signature(path) != saved:
            raise ValueError(f"prepared input changed: {rel}")
    manifest = kit / INPUTS
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != receipt["inputs_sha256"]:
        raise ValueError("stock kit input inventory changed")
    return kit



def claim(receipt, spec, accepted_publication, current_review, attempt):
    """Claim the producer directory once so two controllers cannot place the same kit."""
    if not attempt or not isinstance(attempt, str):
        raise ValueError("normal controller attempt identity is required")
    kit = verify(receipt, spec, accepted_publication, current_review)
    work = Path(receipt["work"])
    path = work / ".published_place_claim.json"
    with tempfile.NamedTemporaryFile("w", dir=work, delete=False) as handle:
        staged = Path(handle.name)
        json.dump({"attempt": attempt, "receipt_sha256": digest(receipt), "kit": str(kit)}, handle, sort_keys=True)
    try:
        os.link(staged, path)
    except FileExistsError as exc:
        if path.read_bytes() != staged.read_bytes():
            raise ValueError("prepared kit was already claimed") from exc
    finally:
        staged.unlink()
    return kit


def read_publication(coord, spec_path, publication, current):
    """Resolve the existing publication record and its exact committed adopted tuple."""
    raw = Path(spec_path).read_bytes()
    spec = json.loads(raw)
    if not spec.get("private") or spec.get("goal") != "place" or not spec.get("dry_gen") or not spec.get("publish_place_prepare"):
        raise ValueError("publication did not prepare one ordinary private place-only spec")
    die = spec["die"]
    manifest = spec["src_manifest_hash"]
    if not re.fullmatch(r"[A-Za-z0-9_]+", die) or not re.fullmatch(r"[0-9a-f]{64}", manifest):
        raise ValueError("invalid prepared die or source manifest")
    canonical = Path(coord) / "autopilot/publish_gate" / die / (manifest + ".json")
    if Path(publication).resolve() != canonical.resolve():
        raise ValueError("expected the canonical publication gate record")
    pub = json.loads(canonical.read_bytes())
    plan_sha = spec["publish_place_prepare"]["plan_sha256"]
    if (pub.get("schema") != "opentallas.publish_gate.v1" or pub.get("verdict") != "PASS"
            or any((pub.get("checks", {}).get(k) or {}).get("verdict") != "PASS"
                   for k in ("schema", "pre_g0", "hashes", "contained", "dry_gen"))
            or any(pub.get(k) != v for k,v in {"die":die, "item":spec["item"], "tree":spec["src"], "plan":spec["plan"],
                                               "manifest_hash":manifest, "plan_sha256":plan_sha}.items())):
        raise ValueError("published PASS does not cover this exact prepared source and type")
    if (any(current.get(k) != spec[v] for k,v in {"src":"src", "plan":"plan", "event":"event",
                                                  "src_manifest_hash":"src_manifest_hash"}.items())
            or current.get("plan_sha256") != plan_sha or spec["gen_host"] not in current.get("gen_hosts", ())):
        raise ValueError("prepared publication is not the committed adopted source/event/producer")
    dry = pub["checks"]["dry_gen"]
    origin = Path(dry["dir"])
    ref = dry["published_place_ready"]
    if (Path(spec_path).resolve() != (origin / "spec.json").resolve()
            or hashlib.sha256(raw).hexdigest() != dry.get("spec_sha256")
            or dry.get("proof_kind") != "published-gen" or dry.get("gen_host") != spec["gen_host"]):
        raise ValueError("prepared controller spec is not the exact sealed publisher spec")
    result = (origin / "result.json").read_bytes()
    if (hashlib.sha256(result).hexdigest() != dry.get("result_sha256")
            or json.loads(result).get("published_place_ready") != ref):
        raise ValueError("prepared producer reference differs from the sealed dry result")
    return raw, {"ref":ref, "publication":{"verdict":"PASS","manifest":manifest,"plan":plan_sha}}


READY_NAME = ".published_place_ready.json"
PREFIX = "KW_PUBLISHED_PLACE_READY "


def producer_command(operation, payload):
    code = Path(__file__).read_text()
    return "python3 -I -c " + shlex.quote(code) + " " + shlex.quote(operation) + " " + shlex.quote(json.dumps(payload))


def write_once(path, data):
    """Keep the first exact bytes even across retries or simultaneous controllers."""
    path = Path(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        staged = Path(handle.name)
        handle.write(data)
    try:
        os.link(staged, path)
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError(f"different producer identity already occupies {path}")
    finally:
        staged.unlink()


def producer(operation, payload):
    spec = payload["spec"]
    work, kit = path_layout(spec)
    target = work / READY_NAME
    if operation == "capture":
        receipt = capture(spec, payload["result"], payload["stages"], payload["form"], payload["plan"], payload["preflight"])
        encoded = (json.dumps(receipt, sort_keys=True) + "\n").encode()
        write_once(target, encoded)
        return {"path": str(target), "sha256": hashlib.sha256(encoded).hexdigest(), "kit": str(kit)}
    if operation != "claim":
        raise ValueError("unknown producer operation")
    ref = payload["ref"]
    if target != Path(ref["path"]) or target.resolve() != target:
        raise ValueError("prepared receipt is outside the original producer directory")
    blob = target.read_bytes()
    if hashlib.sha256(blob).hexdigest() != ref["sha256"]:
        raise ValueError("prepared receipt changed")
    receipt = json.loads(blob)
    resolved = claim(receipt, spec, payload["publication"], payload["review"], payload["attempt"])
    return {"path": str(target), "sha256": ref["sha256"], "kit": str(resolved)}


if __name__ == "__main__":
    print(PREFIX + json.dumps(producer(sys.argv[1], json.loads(sys.argv[2])), sort_keys=True))
