"""Seal a completed whole-die bind for publication without another ELAB, bind or LATCHECK.

A producer receipt is written into the selected output before it is made read-only.
Each replica is enrolled once against the producer's artifact digest. Publication
then checks the sealed local receipt and filesystem identities without reopening
the generated HDL. The source seal is still checked by the normal apply.
"""
import hashlib
import json
from pathlib import Path
import re
import stat

RECEIPT = ".publish-bind-receipt.json"
REPLICA = ".publish-bind-replica.json"
INPUT = "publish_bind_inputs.json"
RESULT = "publish_bind_result.json"


def canonical(doc):
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def require(ok, cause):
    if not ok:
        raise ValueError(cause)


def relative(path, root):
    try:
        return path.relative_to(root)
    except ValueError:
        return None


def checked_file(path):
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and not st.st_mode & 0o222, f"expected immutable regular file: {path}")
    require(path.resolve() == path, f"noncanonical file: {path}")
    return [st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def receipt_inputs(spec, marker):
    return dict(tree=spec["tree"], src_manifest=marker.get("manifest_hash") or marker["src_manifest_sha"],
                plan=spec["plan"], plan_sha256=marker["plan_sha256"], asbuilt=spec["asbuilt"],
                tools_sha=spec["tools_sha"], env=spec["env"])


def normalize_filelist(bind, tree, source_files):
    """Replace only same-inode source aliases.

    Bind's historical ELAB aliases can be live on the producer alone. The
    canonical source is already in the source seal and on every generation host.
    """
    filelist = bind / "bind.f"
    lines = []
    for line in filelist.read_text().splitlines():
        p = Path(line)
        if not p.is_absolute():
            lines.append(line)
            continue
        if relative(p, tree) is not None or relative(p, bind) is not None:
            lines.append(line)
            continue
        candidates = [tree.joinpath(*p.parts[i:]) for i in range(2, len(p.parts))
                      if p.parts[i] in {"rtl", "physical"} and "/".join(p.parts[i:]) in source_files]
        current = next((q for q in candidates if p.samefile(q)), None)
        require(current is not None, f"unproved external HDL alias: {p}")
        lines.append(str(current))
    filelist.write_text("\n".join(lines) + "\n")


def bound_files(bind, tree, source_files):
    names = ("bind.f", "bind_report.json", "provenance_bind.json")
    texts = [(bind / name).read_text() for name in names]
    refs = {Path(line) if line.startswith("/") else tree / line
            for line in texts[0].splitlines() if line.endswith((".sv", ".v", ".vh"))}
    refs.update(Path(p) for p in read(bind / "bind_report.json").get("extra_lib", []))
    refs.update(Path(p) for text in texts[1:] for p in re.findall(r'"(/[^"\s]+\.(?:sv|v|vh))"', text))
    for ref in refs:
        part = relative(ref, tree)
        require(relative(ref, bind) is not None or (part is not None and str(part) in source_files),
                f"bind references an unsealed input: {ref}")
    return sorted(str(p) for p in refs)


def verify_run(bind, producer, inputs):
    """Join existing strict and LATCHECK evidence to the same complete output."""
    tree = Path(inputs["tree"])
    src = read(tree / ".src-manifest.json")
    require(src["manifest_hash"] == inputs["src_manifest"], "source manifest mismatch")
    files = src["files"]
    plan_sha = inputs["plan_sha256"]
    require(files.get(inputs["plan"]) == plan_sha, "plan is outside the exact source seal")
    asbuilt_sha = files[inputs["asbuilt"]]
    plan = read(tree / inputs["plan"])
    ab = read(tree / inputs["asbuilt"])
    require(read(producer / INPUT) == inputs, "producer source, tools, or environment mismatch")
    require(read(producer / RESULT) == {"elab": 0, "bind": 0, "latcheck": 0}, "producer did not complete strict ELAB, bind and LATCHECK")
    r, topo, errors, tool = [read(bind / f) for f in ("bind_report.json", "native_topology.json", "bind_errors_all.json", "bind_tool.json")]
    require(r.get("plan_sha256") == plan_sha and topo.get("asbuilt_sha256") == asbuilt_sha,
            "reported plan/asbuilt identity mismatch")
    require(bool(inputs["tools_sha"]) and tool.get("tools_sha") == inputs["tools_sha"][:12],
            "bound tools differ from the pinned runtime")
    require(r.get("n_errors") == r.get("unmapped") == 0 and r.get("errors") == [] and not r.get("probe_only")
            and errors.get("verdict") == "PASS" and errors.get("n_errors") == 0 and errors.get("errors") == [],
            "strict whole-die bind is incomplete or has errors")
    types = set(plan["partition_types"])
    require(bool(types) and set(r["types"]) == set(topo["types"]) == types, "not the exact whole-die type set")
    parallel = read(bind / "bind_emit_par.json")
    require(parallel.get("jobs", 0) > 1, "whole-die bind is missing parallel emit evidence")
    lat = read(producer / "latcheck.json")
    sm, rows = lat["summary"], lat["lanes"]
    require(sm["scope"] == "die" and sm["pricing"] == "as-bound" and sm["bound_pricing"] == ab.get("kit_source_station_pricing")
            and sm["verdict"] == "PASS" and sm["failed"] == sm["unobserved"] == 0
            and sm["lanes"] == sm["passed"] == len(rows), "LATCHECK is not exact as-bound whole-die PASS")
    require(Path(sm["bind_dir"]).resolve() == (producer / "out").resolve(), "LATCHECK named a different bind")
    require((producer.parent / ".link-base").read_text().strip() == str(tree), "producer is not a copy of this source")
    checked_file(tree / inputs["plan"])
    checked_file(tree / inputs["asbuilt"])
    require((producer.parent / inputs["asbuilt"]).samefile(tree / inputs["asbuilt"]), "producer used a different asbuilt")
    require((producer.parent / sm["plan"]).samefile(tree / inputs["plan"]), "LATCHECK named a different plan")
    expected = read(bind / "bind_latency.json")["buses"]

    def key(row):
        return tuple(row[field] for field in ("lane", "src", "dst", "bus_out", "bus_in"))

    observed = {key(row) for row in rows}
    require(observed and len(observed) == len(rows) and observed == {key(row) for row in expected if row.get("lane")}
            and all(row["verdict"] == "PASS" and row["delta"] == 0 for row in rows),
            "LATCHECK has missing, duplicate, or failing bound lanes")
    return files, dict(types=len(types), lanes=len(rows))


PROOF_ARTIFACTS = ("bind.f", "bind_report.json", "native_topology.json", "bind_latency.json",
                   "bind_errors_all.json", "bind_emit_par.json", "bind_tool.json", "provenance_bind.json")


def artifact_paths(bind, refs):
    parts = {str(path.relative_to(bind)) for path in (bind / "rtl").rglob("*")
             if path.suffix in {".sv", ".v", ".vh"}}
    require(bool(parts), "no bound RTL")
    parts.update(PROOF_ARTIFACTS)
    parts.update(str(Path(ref).relative_to(bind)) for ref in refs if Path(ref).is_relative_to(bind))
    return sorted(parts)


def seal(bind):
    """Called on the finished producer; no copying or mutation of an existing sealed bind."""
    producer = bind.parent
    require(bind == producer / "out" and bind.resolve() == bind and bind.stat().st_mode & 0o200,
            "pass the completed, writable producer's exact out directory")
    require(not (bind / RECEIPT).exists(), "producer output is already recorded")
    inputs = read(producer / INPUT)
    tree = Path(inputs["tree"])
    source_files, counts = verify_run(bind, producer, inputs)
    normalize_filelist(bind, tree, source_files)
    refs = bound_files(bind, tree, source_files)
    payload = dict(version=1, bind=str(bind), inputs=inputs, counts=counts, refs=refs,
                   artifacts={rel: digest(bind / rel) for rel in artifact_paths(bind, refs)})
    (bind / RECEIPT).write_bytes(canonical(payload))
    return hashlib.sha256(canonical(payload)).hexdigest()


def replica_path(bind):
    return bind.parent / (bind.name + REPLICA)


def replica_inputs(bind, payload):
    checked_file(bind / RECEIPT)
    require(bind.resolve() == bind and not bind.stat().st_mode & 0o222, f"bind is writable: {bind}")
    artifacts = payload["artifacts"]
    require(sorted(artifacts) == artifact_paths(bind, payload["refs"]), "bound artifact set changed")
    entries = {rel: checked_file(bind / rel) for rel in artifacts}
    for ref in payload["refs"]:
        if not Path(ref).is_relative_to(bind):
            checked_file(Path(ref))
    return entries


def enroll(bind, expected):
    """After the normal immutable output transfer, once per replica."""
    payload = read(bind / RECEIPT)
    require(hashlib.sha256(canonical(payload)).hexdigest() == expected, "replica producer receipt differs")
    entries = replica_inputs(bind, payload)
    require(all(digest(bind / rel) == sha for rel, sha in payload["artifacts"].items()),
            "replica artifacts differ from the producer")
    require(entries == replica_inputs(bind, payload), "replica changed during enrollment")
    with replica_path(bind).open("xb") as stream:
        stream.write(canonical(dict(digest=expected, entries=entries)))
    replica_path(bind).chmod(0o444)


def verify(bind, inputs, expected):
    payload = read(bind / RECEIPT)
    require(payload["version"] == 1 and payload["bind"] == str(bind) and payload["inputs"] == inputs,
            "receipt source/plan/asbuilt/runtime/environment differs from the selected publication")
    require(hashlib.sha256(canonical(payload)).hexdigest() == expected, "receipt is not the named producer receipt")
    tree = Path(inputs["tree"])
    require((tree / ".src-manifest.sha256").read_text().split()[0] == inputs["src_manifest"],
            "local source seal differs from the producer")
    checked_file(replica_path(bind))
    enrollment = read(replica_path(bind))
    require(enrollment["digest"] == expected and enrollment["entries"] == replica_inputs(bind, payload),
            "replica filesystem identity differs from its enrollment")
    return payload["counts"]


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("seal", "enroll"):
        p = subs.add_parser(name)
        p.add_argument("bind", type=Path)
        if name == "enroll":
            p.add_argument("producer_sha256")
    args = parser.parse_args(argv)
    if args.command == "seal":
        print(seal(args.bind))
    else:
        enroll(args.bind, args.producer_sha256)


if __name__ == "__main__":
    main()
