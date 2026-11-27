#!/usr/bin/env python3
"""relocate_bind.py (QC-PLAN-R3 11-18, COORD): move a bind_out that names a source tree (or its own directory) to another
tree/directory without re-binding.  Shared tool for every die (was private relocate_bind_x.py / rebind_self.py).

    relocate_bind.py refsha OLD_TREE BIND_OUT REF.json         sha256 of every OLD_TREE path BIND_OUT names (run where OLD_TREE is)
    relocate_bind.py tree OLD_TREE NEW_TREE BIND_OUT OUT [--refsha REF.json] [--alias OLD_REL=NEW_REL ...] [--also OLD2 ...]
        OUT = copy of BIND_OUT (hard links for untouched files), every text file naming OLD_TREE/ rewritten to NEW_TREE/.
        Refuses unless EVERY rewritten path exists in NEW_TREE with the bytes it had in OLD_TREE (REF.json, or OLD_TREE read
        directly when it is local).  --alias maps an OLD_TREE file that is not in NEW_TREE (e.g. an absolute-path bind
        manifest) to an in-tree equivalent; it is checked against that file's NEW_TREE bytes.
    relocate_bind.py self OLD_BIND RAW OUT
        pass 2: OUT (= the tree-relocated copy) names its source bind dir OLD_BIND; rewrite OLD_BIND/ -> OUT/.  Every named path
        must exist in RAW (byte copy of the source bind) and OUT.  Files are replaced by write+rename (never through a hard link).
    relocate_bind.py fork-sidecars OLD_TREE NEW_TREE OLD_BIND NEW_BIND STAGED_BIND [--refsha REF.json]
        ot-tree-fork hook for a staged bind copy. Only live path sidecars are rewritten; RTL and reset receipts are byte-exact.
    relocate_bind.py check-receipts BIND_OUT                    0 = every rtl/*.reset_tree.json receipt matches its bound RTL

HDL bytes (QC-TYPES-R3 11-18: 17/130 receipts broke on N3 -> kit-rtl "captured reset identity differs"): bound RTL is hashed by
its reset receipt (rtl/<module>.reset_tree.json bound_rtl_sha256, bound_reset_contract.source).  An .sv/.v/.svh/.vh file whose
every old-path occurrence sits in a // comment (yosys source-location notes) is left byte-identical (path not checked either:
comments do not elaborate).  An HDL file naming the old path in code is rewritten and each receipt that hashed its old bytes is
re-hashed to the new bytes (write+rename).  Both modes end with check-receipts on OUT and fail (tree: OUT not created) on any
mismatch.  Writes/extends OUT/RELOCATED.json.
Ended scoped binds also carry per-type stream records used by kit-rtl when there is no whole die top.  Both passes verify
the original record and all captured bytes before changing path provenance, then retie only the context and file digests
affected by the checked rewrites.  The original run, plan, parameters, timestamp and end marker still govern the record.
Paths written into the bind are NEW_TREE / OUT as given (abspath), never their realpath: a host-local symlink (epyc2 kw45 ->
scratch3) must not leak into a bind that is copied to other hosts.  --also adds more old prefixes (e.g. the realpath
spelling of an earlier tree that kit_rtl file lists use), byte-checked against that prefix and rewritten to NEW_TREE."""
import argparse, hashlib, json, os, re, shutil, sys, tempfile
from contextlib import contextmanager
from pathlib import Path

HDL = (".sv", ".v", ".svh", ".vh")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _pat(old):
    return re.compile(re.escape(old) + r"(/[A-Za-z0-9_.+@=/-]*)?")


def comment_only(txt, old):
    """True when every occurrence of old is after // on its line."""
    for line in txt.splitlines():
        i = line.find(old)
        while i >= 0:
            c = line.find("//")
            if c < 0 or c > i:
                return False
            i = line.find(old, i + 1)
    return True


def _digest(value):
    value = json.loads(json.dumps(value))
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _moved_path(path, olds, new, alias):
    for old in olds:
        if path == old or path.startswith(old + "/"):
            rel = path[len(old):].lstrip("/")
            return str(Path(new) / alias.get(rel, rel))
    return path


def receipt_errors(bind):
    """the bound_reset_contract.source/validate identity checks, on every receipt of a bind dir -> [(receipt, reason)]"""
    bad = []
    for meta in sorted(Path(bind, "rtl").glob("*.reset_tree.json")):
        rec = json.loads(meta.read_text())
        sv = meta.with_name(meta.name[:-len(".reset_tree.json")] + ".sv")
        if rec.get("tree_sha256") != _digest(rec.get("tree")):
            bad.append((meta.name, "tree content differs from receipt"))
        elif rec.get("bound_module") != sv.stem or not sv.is_file():
            bad.append((meta.name, "bound module missing"))
        elif rec.get("bound_rtl_sha256") != sha(sv):
            bad.append((meta.name, "bound RTL identity differs"))
    return bad


def _rehash(out, rewritten_hdl, log, stream_changes, replace=os.replace):
    """re-hash receipts whose bound RTL was rewritten (only when the receipt held exactly the pre-rewrite sha)"""
    for rel, before, after in rewritten_hdl:
        p = Path(out, rel)
        meta = p.with_name(p.stem + ".reset_tree.json")
        if not meta.is_file():
            continue
        rec = json.loads(meta.read_text())
        if rec.get("bound_rtl_sha256") != before:
            continue
        rec["bound_rtl_sha256"] = after
        rec.setdefault("relocated", []).append(dict(bound_rtl_sha256_before=before, tool="relocate_bind.py"))
        meta_before = sha(meta)
        tmp = str(meta) + ".tmp.%d" % os.getpid()
        Path(tmp).write_text(json.dumps(rec, indent=1) + "\n"); replace(tmp, meta)
        rel = str(meta.relative_to(out))
        log.append(rel)
        stream_changes.append(dict(file=rel, sha_before=meta_before, sha_after=sha(meta)))


def _stream_source(root, old_bind=None):
    """Verify an ended scoped bind's final records against its captured local bytes."""
    root = Path(root)
    folder = root / "native_topology.d"
    ended = folder / "_ended"
    report = root / "bind_report.json"
    if not ended.is_file() or not report.is_file():
        return None
    report_doc = json.loads(report.read_text())
    if not report_doc.get("probe_only"):
        return None
    ctx_path = folder / "_context.json"
    if any(p.is_symlink() for p in (folder, ended, report, ctx_path)):
        raise ValueError("bind stream source identity needs regular captured files")
    ctx_bytes = ctx_path.read_bytes()
    ctx = json.loads(ctx_bytes)
    ctx_sha = hashlib.sha256(ctx_bytes).hexdigest()
    run_id, plan_sha = ctx["run_id"], ctx["plan_sha256"]
    if (ctx.get("schema") != "opentallas.native_topology_stream_context.v1" or not run_id
            or json.loads(ended.read_text()).get("run_id") != run_id
            or report_doc.get("plan_sha256") != plan_sha):
        raise ValueError("bind stream source has unrelated scope, plan or end marker")
    records = {}
    for path in sorted(folder.glob("*.json")):
        if path == ctx_path:
            continue
        record = json.loads(path.read_text())
        if record.get("final") is not True:
            continue
        if (path.is_symlink() or record.get("schema") != "opentallas.native_topology_stream.v1"
                or path.stem != record.get("type") or record.get("run_id") != run_id
                or record.get("context_sha256") != ctx_sha or record.get("plan_sha256") != plan_sha):
            raise ValueError(f"bind stream source record has unrelated identity: {path.name}")
        # The absolute producer paths can be unavailable after cross-host rsync.
        # bind_cells.sv identifies the bind root; the staged copy supplies the bytes.
        cells = [Path(p) for p in record["bind_f"] if Path(p).parts[-2:] == ("rtl", "bind_cells.sv")]
        if len(cells) != 1 or not cells[0].is_absolute() or (old_bind and cells[0].parents[1] not in {Path(old_bind), root}):
            raise ValueError(f"bind stream source record has no unique bind root: {path.name}")
        prefix = cells[0].parents[1]
        files = {}
        for name, expected in record["files"].items():
            rel = Path(name).relative_to(prefix)
            captured = root / rel
            if (not rel.parts or ".." in rel.parts or captured.is_symlink() or not captured.is_file()
                    or not captured.resolve().is_relative_to(root.resolve()) or sha(captured) != expected):
                raise ValueError(f"bind stream source file differs from record: {name}")
            files[name] = str(rel)
        if str(cells[0]) not in files:
            raise ValueError(f"bind stream source record does not cover bind cells: {path.name}")
        records[path.name] = record, files
    return ctx, records


def _retie_stream(state, root, map_path, changes, replace=os.replace):
    """Retie records only to exact path rewrites and verified file replacements."""
    if state is None:
        return []
    old_ctx, records = state
    root = Path(root)
    folder = root / "native_topology.d"
    ctx_path = folder / "_context.json"
    expected_ctx = dict(old_ctx)
    for key in ("plan", "asbuilt"):
        if old_ctx.get(key):
            expected_ctx[key] = map_path(old_ctx[key])
    if json.loads(ctx_path.read_text()) != expected_ctx:
        raise ValueError("bind stream context changed fields other than its source paths")
    if expected_ctx.get("plan") != old_ctx.get("plan") and sha(expected_ctx["plan"]) != old_ctx["plan_sha256"]:
        raise ValueError("relocated bind stream plan bytes differ")
    if expected_ctx.get("asbuilt") != old_ctx.get("asbuilt") and sha(expected_ctx["asbuilt"]) != old_ctx["receipt"]["asbuilt_sha256"]:
        raise ValueError("relocated bind stream as-built bytes differ")
    ctx_sha = sha(ctx_path)
    by_file = {}
    for change in changes:
        by_file.setdefault(change["file"], []).append(change)
    writes = []
    for name, (old, rel_files) in records.items():
        path = folder / name
        rec = dict(old, bind_f=[map_path(p) for p in old["bind_f"]],
                   extra_lib=[map_path(p) for p in old["extra_lib"]],
                   files={map_path(p): h for p, h in old["files"].items()})
        if (len(rec["files"]) != len(old["files"]) or json.loads(path.read_text()) != rec):
            raise ValueError(f"bind stream record changed fields other than its source paths: {name}")
        for source, rel in rel_files.items():
            expected = old["files"][source]
            for change in by_file.get(rel, []):
                if change["sha_before"] != expected:
                    raise ValueError(f"unrelated relocation input for bind stream file: {rel}")
                expected = change["sha_after"]
            if sha(root / rel) != expected:
                raise ValueError(f"bind stream relocated file differs from checked rewrite: {rel}")
            rec["files"][map_path(source)] = expected
        rec["context_sha256"] = ctx_sha
        if rec != json.loads(path.read_text()):
            writes.append((path, rec))
    for path, rec in writes:
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
        os.chmod(tmp, path.stat().st_mode & 0o777)
        replace(tmp, path)
    return [path.name for path, _ in writes]


def cmd_refsha(a):
    old = a.old_tree.rstrip("/"); pat = _pat(old); ref = {}
    for dp, _, fns in os.walk(a.bind_out):
        for fn in fns:
            s = os.path.join(dp, fn)
            if os.path.islink(s):
                continue
            data = open(s, "rb").read()
            if old.encode() not in data:
                continue
            for m in pat.finditer(data.decode("utf-8", "replace")):
                rel = (m.group(1) or "").lstrip("/").rstrip("/.")
                if rel in ref:
                    continue
                p = os.path.join(old, rel)
                ref[rel] = sha(p) if os.path.isfile(p) else ("DIR" if os.path.isdir(p) else "MISSING")
    json.dump({"old": old, "paths": ref}, open(a.ref, "w"), indent=0)
    print("REFSHA", len(ref), "missing", sum(v == "MISSING" for v in ref.values()))


def cmd_tree(a):
    # paths written into the bind stay as given (abspath, never realpath): a tree reached through a host-local symlink
    # (epyc2 kw45 -> scratch3) must keep its fleet-wide name, or the bind breaks on every other host
    olds = [a.old_tree.rstrip("/")] + [x.rstrip("/") for x in a.also]
    new, out = os.path.abspath(a.new_tree), os.path.abspath(a.out); src = os.path.realpath(a.bind_out)
    if a.refsha:
        assert not a.also, "--refsha covers OLD_TREE only; --also prefixes must be local"
        ref = json.load(open(a.refsha)); assert ref["old"] == olds[0], (ref["old"], olds[0]); ref = ref["paths"]
    else:
        assert os.path.isdir(olds[0]), "OLD_TREE not local: pass --refsha (relocate_bind.py refsha on its host)"
        ref = None
    for o in olds[1:]:
        assert os.path.isdir(o), f"--also {o} is not local"
    olds.sort(key=len, reverse=True)          # longest prefix first (one old may be a prefix of another)
    alias = dict(x.split("=", 1) for x in a.alias)
    assert not os.path.exists(out), f"REFUSE existing {out}"
    pats = {o: _pat(o) for o in olds}; bad, checked, rewritten, kept, hdl = [], {}, [], [], []
    tmp = out + ".tmp.%d" % os.getpid()
    stream = _stream_source(src)

    def want_of(o, rel):
        if ref is not None and o == a.old_tree.rstrip("/"):
            return ref.get(rel, "MISSING")
        p = os.path.join(o, rel)
        return sha(p) if os.path.isfile(p) else ("DIR" if os.path.isdir(p) else "MISSING")

    for dp, _, fns in os.walk(src):
        rel_dir = os.path.relpath(dp, src)
        os.makedirs(os.path.join(tmp, rel_dir), exist_ok=True)
        for fn in fns:
            s, t = os.path.join(dp, fn), os.path.join(tmp, rel_dir, fn)
            rel_f = os.path.normpath(os.path.join(rel_dir, fn))
            if os.path.islink(s):
                os.symlink(os.readlink(s), t); continue
            data = open(s, "rb").read()
            hit = [o for o in olds if o.encode() in data]
            if not hit:
                os.link(s, t); continue
            txt = data.decode("utf-8")
            if fn.endswith(HDL) and all(comment_only(txt, o) for o in hit):
                os.link(s, t); kept.append(rel_f); continue
            for o in hit:
                for m in set(pats[o].findall(txt)):
                    sub = m.strip("/").rstrip(".")
                    if (o, sub) in checked:
                        continue
                    if sub in alias:
                        n = os.path.join(new, alias[sub]); w = sha(n) if os.path.isfile(n) else "MISSING"
                    else:
                        n = os.path.join(new, sub); w = want_of(o, sub)
                    ok = w != "MISSING" and (os.path.isdir(n) if w == "DIR" else (os.path.isfile(n) and sha(n) == w))
                    checked[(o, sub)] = ok
                    if not ok:
                        bad.append(f"{o}/{sub}")
            for o in hit:
                for ao, an in alias.items():
                    txt = txt.replace(o + "/" + ao, new + "/" + an)
                txt = txt.replace(o + "/", new + "/").replace('"' + o + '"', '"' + new + '"')
            open(t, "w").write(txt); os.chmod(t, os.stat(s).st_mode & 0o777)
            after = sha(t); rewritten.append(dict(file=rel_f, sha_before=hashlib.sha256(data).hexdigest(), sha_after=after))
            if fn.endswith(HDL):
                hdl.append((rel_f, rewritten[-1]["sha_before"], after))
    if bad:
        shutil.rmtree(tmp)
        print(f"REFUSE {len(bad)} path(s) differ or are missing in the new tree: {bad[:10]}"); sys.exit(2)
    rehashed = []                # receipts in tmp may be hard links into BIND_OUT: _rehash replaces them by write+rename
    stream_changes = []
    _rehash(tmp, hdl, rehashed, stream_changes)
    rbad = receipt_errors(tmp)
    if rbad:
        shutil.rmtree(tmp)
        print(f"REFUSE {len(rbad)} reset receipt(s) do not match the relocated RTL: {rbad[:5]}"); sys.exit(3)
    try:
        retied = _retie_stream(stream, tmp, lambda p: _moved_path(p, olds, new, alias), rewritten + stream_changes)
    except (OSError, ValueError, KeyError):
        shutil.rmtree(tmp)
        raise
    json.dump(dict(tool="relocate_bind.py tree", old_tree=olds, new_tree=new, source=src, alias=alias, paths_checked=len(checked),
                   rewritten=rewritten, hdl_comment_only_kept=kept, receipts_rehashed=rehashed, stream_records_retied=retied,
                   receipts_checked=len(list(Path(tmp, "rtl").glob("*.reset_tree.json")))),
              open(os.path.join(tmp, "RELOCATED.json"), "w"), indent=1)
    os.rename(tmp, out)
    print(f"RELOCATED {out}: {len(rewritten)} file(s) rewritten, {len(kept)} HDL kept (comment-only), {len(rehashed)} receipt(s) "
          f"re-hashed, {len(checked)} distinct paths byte-checked, reset receipts 0 mismatch")


@contextmanager
def _self_edits(out):
    """Keep a scoped output retryable and publish its audit only after successful edits."""
    marker = Path(out, "RELOCATED.json")
    undo = Path(tempfile.mkdtemp(prefix=".bind-self-", dir=marker.parent.parent))
    saved_marker = undo / "marker"
    originals = {}
    started = False

    def replace(src, dst):
        nonlocal started
        dst = Path(dst)
        try:
            if not started:
                if os.path.lexists(marker):
                    os.replace(marker, saved_marker)
                started = True
            if dst != marker and dst not in originals:
                saved = undo / str(len(originals))
                os.link(dst, saved, follow_symlinks=False)
                originals[dst] = saved
            os.replace(src, dst)
        except OSError:
            Path(src).unlink(missing_ok=True)
            raise

    try:
        yield replace
    except BaseException:
        if started:
            marker.unlink(missing_ok=True)
            for dst, saved in reversed(originals.items()):
                os.replace(saved, dst)
            if os.path.lexists(saved_marker):
                os.replace(saved_marker, marker)
        shutil.rmtree(undo)
        raise
    else:
        shutil.rmtree(undo)


def cmd_self(a):
    old = a.old_bind.rstrip("/"); raw, out = os.path.realpath(a.raw), os.path.abspath(a.out)
    stream = _stream_source(out, old)
    if stream is None:
        _rewrite_self(old, raw, out, None, os.replace)
    else:
        with _self_edits(out) as replace:
            _rewrite_self(old, raw, out, stream, replace)


def _rewrite_self(old, raw, out, stream, replace):
    pat = _pat(old); bad, checked, rew, kept, hdl = [], set(), [], [], []
    rp = os.path.join(out, "RELOCATED.json")
    r = json.load(open(rp)) if os.path.isfile(rp) else {}
    for dp, _, fns in os.walk(out):
        for fn in fns:
            p = os.path.join(dp, fn)
            if os.path.islink(p) or fn == "RELOCATED.json":
                continue
            data = open(p, "rb").read()
            if old.encode() not in data:
                continue
            txt = data.decode("utf-8")
            if fn.endswith(HDL) and comment_only(txt, old):
                kept.append(os.path.relpath(p, out)); continue
            for m in set(pat.findall(txt)):
                rel = m.strip("/").rstrip(".")
                if rel in checked:
                    continue
                checked.add(rel)
                if not (os.path.exists(os.path.join(raw, rel)) and os.path.exists(os.path.join(out, rel))):
                    bad.append(rel or "/")
            new = txt.replace(old + "/", out + "/").replace('"' + old + '"', '"' + out + '"').replace(old + " ", out + " ").replace(old + "\n", out + "\n")
            tmp = p + ".tmp.%d" % os.getpid(); open(tmp, "w").write(new); os.chmod(tmp, os.stat(p).st_mode & 0o777); replace(tmp, p)
            rew.append(dict(file=os.path.relpath(p, out), sha_before=hashlib.sha256(data).hexdigest(), sha_after=sha(p)))
            if fn.endswith(HDL):
                hdl.append((rew[-1]["file"], rew[-1]["sha_before"], rew[-1]["sha_after"]))
    assert not bad, ("REFUSE missing", bad[:10])
    left = [os.path.relpath(os.path.join(dp, f), out) for dp, _, fs in os.walk(out) for f in fs
            if f != "RELOCATED.json" and os.path.relpath(os.path.join(dp, f), out) not in kept
            and not os.path.islink(os.path.join(dp, f)) and old.encode() in open(os.path.join(dp, f), "rb").read()]
    assert not left, ("still names old", left[:5])
    rehashed, stream_changes = [], []
    _rehash(out, hdl, rehashed, stream_changes, replace)
    rbad = receipt_errors(out)
    retied = _retie_stream(stream, out, lambda p: _moved_path(p, [old], out, {}), rew + stream_changes, replace) if not rbad else []
    previous = r.get("pass2_self", {})
    same_success = (stream is not None and previous.get("old_bind") == old and previous.get("new_bind") == out
                    and previous.get("receipt_mismatch") == [] and not (rew or retied or rbad))
    if not same_success:
        r["pass2_self"] = dict(tool="relocate_bind.py self", old_bind=old, new_bind=out, paths_checked=len(checked), rewritten=rew,
                               hdl_comment_only_kept=kept, receipts_rehashed=rehashed, stream_records_retied=retied, receipt_mismatch=rbad)
        tmp = rp + ".tmp"; json.dump(r, open(tmp, "w"), indent=1); replace(tmp, rp)
    if rbad:
        print(f"FAIL {len(rbad)} reset receipt(s) do not match: {rbad[:5]}"); sys.exit(3)
    print(f"PASS2 {len(rew)} files rewritten, {len(kept)} HDL kept (comment-only), {len(rehashed)} receipt(s) re-hashed, "
          f"{len(checked)} paths checked, reset receipts 0 mismatch")


FORK_PATH_SIDECARS = ("bind.f", "asbuilt.ys", "bind_report.json", "provenance_bind.json",
                      "provenance_elab.json", "asbuilt_sources.json", "type_defines.json")


def cmd_fork_sidecars(a):
    """Rebase path consumers in a new inode-private bind before ot-tree-fork publishes it."""
    stage = Path(a.staged_bind)
    old_tree, new_tree = a.old_tree.rstrip("/"), a.new_tree.rstrip("/")
    old_bind, new_bind = a.old_bind.rstrip("/"), a.new_bind.rstrip("/")
    if not all(os.path.isabs(x) for x in (old_tree, new_tree, old_bind, new_bind)):
        raise ValueError("fork-sidecars needs absolute paths")
    if stage.parent.resolve() != Path(new_bind).parent.resolve() or not stage.name.startswith(Path(new_bind).name + ".forking-"):
        raise ValueError("fork-sidecars needs the private staged bind created by ot-tree-fork")
    if not (stage / "bind.f").is_file() or not Path(new_tree).is_dir():
        raise ValueError("staged bind.f and the destination tree must exist")
    bad = receipt_errors(stage)
    if bad:
        raise ValueError(f"reset receipts do not match source RTL: {bad[:5]}")
    for meta in (stage / "rtl").glob("*.reset_tree.json"):
        rtl = meta.with_name(meta.name.removesuffix(".reset_tree.json") + ".sv")
        text = rtl.read_text()
        if ((old_tree != new_tree and not comment_only(text, old_tree + "/")) or
                (old_bind != new_bind and not comment_only(text, old_bind + "/"))):
            raise ValueError(f"captured RTL has an active absolute path; rebind for the new tree: {rtl.name}")
    refs = None
    if a.refsha:
        ref = json.loads(Path(a.refsha).read_text())
        if ref["old"] != old_tree:
            raise ValueError("source reference does not match the old tree")
        refs = ref["paths"]
    checked = set()

    def replace(text, old, new, actual):
        pattern = re.compile(re.escape(old) + r"(/[A-Za-z0-9_.+@=/-]*)?(?=$|[\s\x22\x27:,])")
        def path(m):
            rel = (m.group(1) or "").strip("/")
            key = (old, rel)
            if key not in checked:
                src, dst = Path(old, rel), Path(actual, rel)
                if old == old_bind:
                    ok = dst.exists()
                else:
                    expected = refs.get(rel, "MISSING") if refs is not None else (
                        sha(src) if src.is_file() else "DIR" if src.is_dir() else "MISSING")
                    ok = dst.is_dir() if expected == "DIR" else dst.is_file() and sha(dst) == expected
                if not ok:
                    raise ValueError(f"bind path missing or changed at destination: {src}")
                checked.add(key)
            return new + (m.group(1) or "")
        return pattern.sub(path, text)

    rewrites = []
    for name in FORK_PATH_SIDECARS:
        file = stage / name
        if not file.is_file():
            continue
        if file.is_symlink():
            raise ValueError(f"bind path sidecar is a symlink: {file}")
        text = file.read_text()
        moved = replace(replace(text, old_tree, new_tree, new_tree), old_bind, new_bind, stage)
        if moved != text:
            rewrites.append((file, moved))
    for file, moved in rewrites:
        tmp = file.with_name(file.name + ".relocating")
        with tmp.open("x") as f:
            f.write(moved)
        os.chmod(tmp, file.stat().st_mode & 0o777)
        os.replace(tmp, file)
    print(f"BIND-FORK {len(rewrites)} sidecars relocated, {len(checked)} paths checked, reset receipts match")


def cmd_check(a):
    n = len(list(Path(a.bind_out, "rtl").glob("*.reset_tree.json"))); bad = receipt_errors(a.bind_out)
    for b in bad:
        print("RECEIPT_MISMATCH", *b)
    print(f"RECEIPTS {n} checked, {len(bad)} mismatch")
    sys.exit(1 if bad else 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("refsha"); p.add_argument("old_tree"); p.add_argument("bind_out"); p.add_argument("ref"); p.set_defaults(f=cmd_refsha)
    p = sp.add_parser("tree"); p.add_argument("old_tree"); p.add_argument("new_tree"); p.add_argument("bind_out"); p.add_argument("out")
    p.add_argument("--refsha"); p.add_argument("--alias", action="append", default=[])
    p.add_argument("--also", action="append", default=[], help="another local old-tree prefix (e.g. the realpath spelling) rewritten to NEW_TREE")
    p.set_defaults(f=cmd_tree)
    p = sp.add_parser("self"); p.add_argument("old_bind"); p.add_argument("raw"); p.add_argument("out"); p.set_defaults(f=cmd_self)
    p = sp.add_parser("fork-sidecars")
    for name in ("old_tree", "new_tree", "old_bind", "new_bind", "staged_bind"):
        p.add_argument(name)
    p.add_argument("--refsha")
    p.set_defaults(f=cmd_fork_sidecars)
    p = sp.add_parser("check-receipts"); p.add_argument("bind_out"); p.set_defaults(f=cmd_check)
    a = ap.parse_args(argv)
    if a.cmd == "fork-sidecars":
        try:
            a.f(a)
        except (OSError, ValueError, KeyError) as error:
            ap.exit(3, f"BIND-FORK REFUSED: {error}\n")
    else:
        a.f(a)


if __name__ == "__main__":
    main()
