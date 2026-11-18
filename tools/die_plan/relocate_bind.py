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
    relocate_bind.py check-receipts BIND_OUT                    0 = every rtl/*.reset_tree.json receipt matches its bound RTL

HDL bytes (QC-TYPES-R3 11-18: 17/130 receipts broke on N3 -> kit-rtl "captured reset identity differs"): bound RTL is hashed by
its reset receipt (rtl/<module>.reset_tree.json bound_rtl_sha256, bound_reset_contract.source).  An .sv/.v/.svh/.vh file whose
every old-path occurrence sits in a // comment (yosys source-location notes) is left byte-identical (path not checked either:
comments do not elaborate).  An HDL file naming the old path in code is rewritten and each receipt that hashed its old bytes is
re-hashed to the new bytes (write+rename).  Both modes end with check-receipts on OUT and fail (tree: OUT not created) on any
mismatch.  Writes/extends OUT/RELOCATED.json.
Paths written into the bind are NEW_TREE / OUT as given (abspath), never their realpath: a host-local symlink (epyc2 kw45 ->
scratch3) must not leak into a bind that is copied to other hosts.  --also adds more old prefixes (e.g. the realpath
spelling of an earlier tree that kit_rtl file lists use), byte-checked against that prefix and rewritten to NEW_TREE."""
import argparse, hashlib, json, os, re, shutil, sys
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


def _rehash(out, rewritten_hdl, log):
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
        tmp = str(meta) + ".tmp.%d" % os.getpid()
        Path(tmp).write_text(json.dumps(rec, indent=1) + "\n"); os.replace(tmp, meta)
        log.append(str(meta.relative_to(out)))


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
    _rehash(tmp, hdl, rehashed)
    rbad = receipt_errors(tmp)
    if rbad:
        shutil.rmtree(tmp)
        print(f"REFUSE {len(rbad)} reset receipt(s) do not match the relocated RTL: {rbad[:5]}"); sys.exit(3)
    json.dump(dict(tool="relocate_bind.py tree", old_tree=olds, new_tree=new, source=src, alias=alias, paths_checked=len(checked),
                   rewritten=rewritten, hdl_comment_only_kept=kept, receipts_rehashed=rehashed,
                   receipts_checked=len(list(Path(tmp, "rtl").glob("*.reset_tree.json")))),
              open(os.path.join(tmp, "RELOCATED.json"), "w"), indent=1)
    os.rename(tmp, out)
    print(f"RELOCATED {out}: {len(rewritten)} file(s) rewritten, {len(kept)} HDL kept (comment-only), {len(rehashed)} receipt(s) "
          f"re-hashed, {len(checked)} distinct paths byte-checked, reset receipts 0 mismatch")


def cmd_self(a):
    old = a.old_bind.rstrip("/"); raw, out = os.path.realpath(a.raw), os.path.abspath(a.out)
    pat = _pat(old); bad, checked, rew, kept, hdl = [], set(), [], [], []
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
            tmp = p + ".tmp.%d" % os.getpid(); open(tmp, "w").write(new); os.chmod(tmp, os.stat(p).st_mode & 0o777); os.replace(tmp, p)
            rew.append(dict(file=os.path.relpath(p, out), sha_before=hashlib.sha256(data).hexdigest(), sha_after=sha(p)))
            if fn.endswith(HDL):
                hdl.append((rew[-1]["file"], rew[-1]["sha_before"], rew[-1]["sha_after"]))
    assert not bad, ("REFUSE missing", bad[:10])
    left = [os.path.relpath(os.path.join(dp, f), out) for dp, _, fs in os.walk(out) for f in fs
            if f != "RELOCATED.json" and os.path.relpath(os.path.join(dp, f), out) not in kept
            and not os.path.islink(os.path.join(dp, f)) and old.encode() in open(os.path.join(dp, f), "rb").read()]
    assert not left, ("still names old", left[:5])
    rehashed = []; _rehash(out, hdl, rehashed)
    rbad = receipt_errors(out)
    rp = os.path.join(out, "RELOCATED.json")
    r = json.load(open(rp)) if os.path.isfile(rp) else {}
    r["pass2_self"] = dict(tool="relocate_bind.py self", old_bind=old, new_bind=out, paths_checked=len(checked), rewritten=rew,
                           hdl_comment_only_kept=kept, receipts_rehashed=rehashed, receipt_mismatch=rbad)
    tmp = rp + ".tmp"; json.dump(r, open(tmp, "w"), indent=1); os.replace(tmp, rp)
    if rbad:
        print(f"FAIL {len(rbad)} reset receipt(s) do not match: {rbad[:5]}"); sys.exit(3)
    print(f"PASS2 {len(rew)} files rewritten, {len(kept)} HDL kept (comment-only), {len(rehashed)} receipt(s) re-hashed, "
          f"{len(checked)} paths checked, reset receipts 0 mismatch")


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
    p = sp.add_parser("check-receipts"); p.add_argument("bind_out"); p.set_defaults(f=cmd_check)
    a = ap.parse_args(argv); a.f(a)


if __name__ == "__main__":
    main()
