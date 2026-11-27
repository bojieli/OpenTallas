"""Recheck the sole late BIND_SRC_OUTSIDE failure of a retained native partition."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import bind_stream
import bind_strict_src


SCHEMA = "opentallas.bind_source_postcheck.v1"


def _sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _read(path):
    return json.loads(path.read_text())


def _sealed_files(root, seal):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "autopilot"))
    try:
        from src_manifest import manifest_hash
    finally:
        sys.path.pop(0)
    marker = (root / ".src-manifest.sha256").read_text().strip()
    manifest = _read(root / ".src-manifest.json")
    if marker != seal or manifest.get("manifest_hash") != seal or manifest_hash(manifest) != seal:
        raise ValueError("source root does not have the requested manifest seal")
    return manifest["files"]


def inspect(plan, asbuilt, bind_out, type_name, source_root, source_seal):
    """Read-only. Both original and corrected stock checks must reproduce."""
    plan, asbuilt, out, root = (Path(p).resolve() for p in (plan, asbuilt, bind_out, source_root))
    report_path = out / "bind_report.json"
    report = _read(report_path)
    original = report.get("errors") or []
    if report.get("n_errors") != 1 or len(original) != 1 or not original[0].startswith("BIND_SRC_OUTSIDE "):
        raise ValueError("the sole final bind failure must be BIND_SRC_OUTSIDE")
    if type_name not in (report.get("probe_only") or {}).get("emitted", []):
        raise ValueError("the selected type must be present in the retained native probe")
    strict = report["strict_src"]
    roots = [Path(p).resolve() for p in strict["allowed_roots"]]
    if root in roots:
        raise ValueError("the approved source root was already allowed")

    directory = out / bind_stream.DIR
    context_path = directory / bind_stream.CTX
    context = _read(context_path)
    ended = _read(directory / "_ended")
    if not ended.get("run_id") or ended["run_id"] != context.get("run_id"):
        raise ValueError("the retained bind stream must have ended")
    if context.get("plan_sha256") != _sha(plan) or Path(context["plan"]).resolve() != plan:
        raise ValueError("plan does not match the completed native probe")
    if (Path(context["asbuilt"]).resolve() != asbuilt or
            context["receipt"]["asbuilt_sha256"] != _sha(asbuilt)):
        raise ValueError("asbuilt does not match the completed native probe")
    why = []
    native = bind_stream.records(out, type_name, why, require_live=False)
    if len(native) != 1 or native[0].get("type") != type_name:
        raise ValueError(f"no intact final native record for {type_name}: {why}")
    native = native[0]
    expected = (out / "rtl" / (report["types"][type_name]["module"] + ".sv")).resolve()
    if native.get("plan_sha256") != _sha(plan) or str(expected) not in native["files"]:
        raise ValueError("native record does not cover the selected RTL and plan")

    # Limit recovery to the exact scoped filelist and stock ordinary checks.
    files_path = out / "bind.f"
    asbuilt_sources = out / "asbuilt_sources.json"
    files = files_path.read_text().splitlines()
    base_lib = _read(asbuilt_sources)["lib"]
    extra_lib = report.get("extra_lib", [])
    emitted = report["files"]
    if (report.get("bound_groups") or files != base_lib + extra_lib + emitted or
            any(not Path(p).is_absolute() for p in files) or
            any(out not in Path(p).resolve().parents for p in emitted)):
        raise ValueError("retained filelist is not a supported exact scoped bind")
    if native.get("bind_f") != base_lib + extra_lib + [str(out / "rtl" / "bind_cells.sv"), str(expected)]:
        raise ValueError("native stream and final source filelist disagree")
    errors, _ = bind_strict_src.check(files, base_lib, extra_lib, emitted, [], roots)
    if errors != original:
        raise ValueError(f"original strict source failure is not reproducible: {errors}")

    manifest = _sealed_files(root, source_seal)
    if manifest.get(asbuilt.relative_to(root).as_posix()) != _sha(asbuilt):
        raise ValueError("the approved source manifest does not cover the captured asbuilt")
    exempt = {Path(p).resolve() for p in base_lib}
    recovered = {}
    for item in map(Path, files):
        resolved = item.resolve()
        if resolved in exempt or bind_strict_src._inside(resolved, roots):
            continue
        relative = resolved.relative_to(root).as_posix()
        actual = _sha(resolved)
        if manifest.get(relative) != actual:
            raise ValueError(f"approved source manifest hash mismatch for {relative}")
        recovered[relative] = actual
    if not recovered:
        raise ValueError("no exact outside source paths were recovered")
    errors, _ = bind_strict_src.check(files, base_lib, extra_lib, emitted, [], [*roots, root])
    if errors:
        raise ValueError(f"corrected strict source check failed: {errors}")

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "scope": "retained native source for one kit",
        "original_bind_result": "FAIL",
        "original_error": original[0],
        "type": type_name,
        "bind_out": str(out),
        "plan_sha256": _sha(plan),
        "asbuilt_sha256": _sha(asbuilt),
        "source_root": str(root),
        "source_seal": source_seal,
        "recovered_files": recovered,
        "retained_sha256": {str(path): _sha(path) for path in (
            report_path, files_path, asbuilt_sources, context_path, directory / "_ended",
            directory / (type_name + ".json"), *map(Path, files)
        )},
    }


def verify(receipt_path, *, plan, asbuilt, bind_out, type_name, source_root):
    payload = Path(receipt_path).read_bytes()
    saved = json.loads(payload)
    if saved.get("schema") != SCHEMA or saved.get("status") != "PASS":
        raise ValueError("expected a passing retained native source postcheck")
    current = inspect(plan, asbuilt, bind_out, type_name, source_root, saved["source_seal"])
    if current != saved:
        raise ValueError("retained native source postcheck differs from its verified inputs")
    return hashlib.sha256(payload).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    parser.add_argument("--asbuilt", required=True)
    parser.add_argument("--out", required=True, help="original native bind output, read-only")
    parser.add_argument("--type", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--source-seal", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if Path(args.out).resolve() in args.receipt.resolve().parents:
        parser.error("write the separate receipt outside the original native bind")
    try:
        receipt = inspect(args.plan, args.asbuilt, args.out, args.type, args.source_root, args.source_seal)
        with args.receipt.open("x") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"bind source postcheck: {error}\n")


if __name__ == "__main__":
    main()
