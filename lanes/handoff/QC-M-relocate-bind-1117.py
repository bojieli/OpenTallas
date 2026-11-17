"""Exact M bind-context relocation, parameterized from the qualified L2 relocation; no ELAB/bind replay."""
from pathlib import Path
import json, hashlib, sys, shutil, os, re
spec=json.loads(Path(sys.argv[1]).read_text())
P=Path(spec["work"]);S0=spec["old_bind"];J=spec["old_root"]
RAW=Path(spec["raw_snapshot"]);N=Path(spec["published_tree"])
B=Path(spec["context_parent"]);D=Path(spec["context"])
PL=N/spec["plan_relative"];A=N/spec["manifest_relative"]
ISO=spec["isolated_manifest"]
# HDL bytes and reset emission receipts are immutable; source-location comments are provenance.
SUFFIX=(".json",".f",".ys",".tcl")
HDL_SUFFIX=(".sv",".v",".svh",".vh")


def sha(p):
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for v in iter(lambda: f.read(4 << 20), b""):
            h.update(v)
    return h.hexdigest()


def main():
    host = sys.argv[2]
    pub = json.loads(Path(spec["publication_record"].format(host=host)).read_text())
    assert pub["status"] == "PUBLISHED" and (N / ".src-manifest.sha256").read_text().strip() == pub["manifest_hash"]
    assert sha(PL)==pub["plan_sha256"] and sha(A)==pub["asbuilt_sha256"] and not B.exists()
    lst = [l.split("  ", 1) for l in Path(spec["raw_inventory"]).read_text().splitlines()]
    for h, f in lst:
        assert sha(RAW / f) == h, f
    assert sum(1 for p in RAW.rglob("*") if p.is_file()) == len(lst)
    sys.path.insert(0, str(N / "tools/die_plan"))
    import kit_topology as K, manifest_paths as M
    raw = json.loads(PL.read_text()); ab = json.loads(A.read_text())
    assert M.check(ab, A.parent, repo=N) == []
    old = json.loads((RAW / "native_topology.json").read_text())
    after = K.native_contract(raw, str(A), str(PL))
    keys = ["schema", "types", "ownership", "clock_table_sha256", "reset", "transport"]
    diff = [k for k in keys if old.get(k) != after.get(k)]
    assert not diff, ("native contract differs", diff)
    JREF = json.loads(Path(spec["old_refs"]).read_text())
    B.mkdir(parents=True); shutil.copytree(RAW, D)
    selected={x["original"]:x for x in json.loads(Path(spec["selected_source_map"]).read_text())}
    pat = re.compile(rb"/srv/[A-Za-z0-9_.\-]+/claude/[A-Za-z0-9_./\-]+")
    kept, mapped, rewritten = {}, {}, []
    shacache = {}

    def nsha(n):
        if n not in shacache:
            shacache[n] = sha(n)
        return shacache[n]

    def sub(m):
        s = m.group(0).decode(); t = s.rstrip(".,:;"); tail = s[len(t):]
        if t == S0 or t.startswith(S0 + "/"):
            return (str(D) + t[len(S0):] + tail).encode()
        if t == ISO:
            mapped[t] = str(A); return (str(A) + tail).encode()
        if t in selected:
            item=selected[t]; rel=Path(item["packaged"]).relative_to(Path(spec["stage"]))
            n=str(N/rel)
            assert nsha(n)==item["sha256"],("selected source changed",t)
            mapped[t]=n;return (n+tail).encode()
        if t == J or t.startswith(J + "/"):
            n = (str(N) + t[len(J):]); w = JREF.get(t)
            if (w == "DIR" and os.path.isdir(n)) or (w not in (None, "DIR", "MISSING") and os.path.isfile(n) and nsha(n) == w):
                mapped[t] = n; return (n + tail).encode()
        kept[t] = kept.get(t, 0) + 1
        return m.group(0)

    for p in sorted(D.rglob("*")):
        if not p.is_file() or (p.name == "asbuilt.json" or p.name.endswith(".reset_tree.json")) or p.suffix not in SUFFIX:
            continue
        v = p.read_bytes(); w = pat.sub(sub, v)
        if w != v:
            p.chmod(p.stat().st_mode | 0o200); p.write_bytes(w); rewritten.append(str(p.relative_to(D)))
    assert sha(D / "asbuilt.json") == sha(RAW / "asbuilt.json")
    hdl_preserved = []
    for p in RAW.rglob("*"):
        if p.is_file() and (p.suffix in HDL_SUFFIX or p.name.endswith(".reset_tree.json")):
            rel = p.relative_to(RAW)
            assert sha(p) == sha(D / rel), ("immutable bound emission changed", str(rel))
            hdl_preserved.append(str(rel))
    badf = []
    for f in D.rglob("*.f"):
        for word in re.split(r"\s+", f.read_text()):
            if word.startswith("/srv/opentallas-scratch3/") or (word.startswith("/srv/") and word.endswith((".sv", ".v", ".vh", ".svh")) and not os.path.isfile(word)):
                badf.append([str(f.relative_to(D)), word])
    assert not badf, badf[:10]
    K.write_bind_receipt(raw, str(D), str(A), topology=after, plan_path=str(PL))
    passed = [tn for tn in raw["partition_types"] if K.bind_matches(raw, tn, str(D), str(A), str(PL))]
    assert len(passed) == len(raw["partition_types"]), ("bind_matches", len(passed), len(raw["partition_types"]))
    proof = dict(
        tree=str(N), manifest_hash=pub["manifest_hash"], plan=str(PL), plan_sha256=sha(PL), asbuilt=str(A), asbuilt_sha256=sha(A),
        bind_out=str(D), raw_bind="epyc2:" + S0, raw_bind_sha256_list=sha(Path(spec["raw_inventory"])),
        native_contract_equal=True, normal_manifest_policy_errors=[], bind_matches_n=len(passed), bind_matches=passed,
        compiled_asbuilt_sha256=sha(D / "asbuilt.json"), immutable_emission_files=hdl_preserved, path_rewritten_files=rewritten, mapped_paths_n=len(mapped),
        mapped_iso_to_portable={ISO: str(A)}, kept_provenance_paths=kept, native_topology_sha256=sha(D / "native_topology.json"),
        gates_of_record=spec["gates_of_record"])
    (B / "M_relocation_PASS.json").write_text(json.dumps(proof, indent=1) + "\n")
    print("M_CONTEXT_PASS", json.dumps({k: proof[k] for k in ["manifest_hash", "plan_sha256", "asbuilt_sha256", "bind_out",
          "bind_matches_n", "mapped_paths_n", "native_topology_sha256"]}), "kept", len(kept), flush=True)


if __name__ == "__main__":
    main()
