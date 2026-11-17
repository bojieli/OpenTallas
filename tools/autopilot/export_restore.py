#!/usr/bin/env python3
"""export_restore (FLEET-OPS-R, COORD r585 (b)): a file an original kit left behind and a child view's provenance.json still names is restored from the SIGNED EXPORT, hash checked
against the export's own record, instead of failing the kit (KIT_INPUT_MISSING).  Which files are restorable follows what the export holds per signed element:
    export/odb      <- INDEX.tsv row whose record column starts with provenance export.signoff_sha256 (db file, sha256 column = the check)
    export/signoff  <- the element dir's signoff.json when sha256(file) == the record id (exact bytes of the signed record)
    export/lec      <- the element dir's lec.json when its sha256 is one the record's file list names
    export/kit, export/base  <- directories: created empty (only their children are read)
Anything else is reported unrestorable (a re-sign copy's signoff.json is another file than the element's and cannot be verified).
The export lives off the fleet (AGIdock /archive/opentallas-signed-1114, rtx-pro ~/signed-export-1114).  fetch(src_path, dst) is injected: a local copy in tests, `ssh HOST cat` or rsync from a
configured export host in production (kit_wave.json option signed_export = {"root": ..., "ssh": "host or ''"}); no option = this stage does nothing."""
import csv, hashlib, json, os


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load_index(root):
    with open(os.path.join(root, "INDEX.tsv")) as f:
        rows = list(csv.reader(f, delimiter="\t"))
    hdr = rows[0]
    return [dict(zip(hdr, r)) for r in rows[1:] if len(r) >= len(hdr)]


def plan(missing, provenance_of, index_rows, root):
    """missing: [(path, provenance.json path)]; provenance_of(path) -> parsed provenance dict.  -> [(dst path, kind, source path or None, expected sha or None)], [unrestorable (path, why)]"""
    out, bad = [], []
    for path, by in missing:
        prov = provenance_of(by) or {}
        ex = prov.get("export") if isinstance(prov.get("export"), dict) else {}
        rid = (ex.get("signoff_sha256") or "")
        key = next((k for k, v in ex.items() if v == path), None)
        if not key:
            bad.append((path, "not an export/* path of its provenance")); continue
        if key in ("kit", "base"):
            out.append((path, "dir", None, None)); continue
        rows = [r for r in index_rows if rid and r.get("record", "").startswith(rid[:12])]
        if not rows:
            bad.append((path, "no signed export row for record " + rid[:12])); continue
        if key == "odb":
            r = rows[0]
            out.append((path, "odb", os.path.join(root, os.path.relpath(r["db"], "/archive/opentallas-signed-1114")), r["sha256"]))
        elif key == "signoff":
            e = os.path.dirname(os.path.join(root, os.path.relpath(rows[0]["db"], "/archive/opentallas-signed-1114")))
            out.append((path, "signoff", os.path.join(e, "signoff.json"), "id:" + rid))
        elif key == "lec":
            e = os.path.dirname(os.path.join(root, os.path.relpath(rows[0]["db"], "/archive/opentallas-signed-1114")))
            out.append((path, "lec", os.path.join(e, "lec.json"), "any:" + ",".join(ex.get("lec_sha256_any") or [])))
        else:
            bad.append((path, "kind " + key + " not in the export"))
    return out, bad


def restore(items, fetch, tmpdir, hash_ok=sha256_file):
    """fetch(src, dst) copies the exported file to dst.  -> (restored dsts, failures [(dst, why)]).  A file whose hash does not match is never placed."""
    done, fail = [], []
    for dst, kind, src, want in items:
        if kind == "dir":
            os.makedirs(dst, exist_ok=True); done.append(dst); continue
        tmp = os.path.join(tmpdir, hashlib.md5(dst.encode()).hexdigest())
        try:
            fetch(src, tmp)
            got = hash_ok(tmp)
        except Exception as e:
            fail.append((dst, "fetch failed: %s" % e)); continue
        ok = (got == want) if not want.startswith(("id:", "any:")) else (got.startswith(want[3:15]) if want.startswith("id:") else (not want[4:] or got in want[4:].split(",")))
        if not ok:
            os.unlink(tmp); fail.append((dst, "sha256 %s does not match the signed record" % got[:12])); continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.replace(tmp, dst); done.append(dst)
    return done, fail

# ---- request path (COORD 11-17: no hub key, no mirror): kit_snap queues RESTORE-NEEDED rows, a copy-only worker on rtx-pro pushes the hash-checked files ----
import time


def store_sha(record, path, store_dir=None):
    """expected sha256 of an original-kit file from its signed STORE record (files [path, size, sha]); '' when the record or the file is unknown"""
    import glob, gzip
    d = store_dir or os.path.expanduser("~/coord/signed-store/records")
    for f in glob.glob(os.path.join(d, record[:2], record[:12] + "*.json.gz")):
        try:
            rec = json.loads(gzip.open(f).read())
        except (OSError, ValueError):
            continue
        for e in rec.get("files") or []:
            if e[0].lstrip("/") == path.lstrip("/"):
                return e[2]
    return ""


def restore_rows_ex(missing, provenance_of, host, now=None, sha_of=None):
    """COORD FABLE-FLOW-1500 (B): EVERY missing view-ref path is queued, not only provenance export keys (the failing paths were original-kit files: face_guard.json, kit
    files).  kind = the export key (odb / signoff / lec / base / kit) or 'original-kit'; module and record id come from the view's provenance; an original-kit row carries the
    expected sha256 from the signed store record when it lists the file.  -> (rows, skips [(path, reason)])"""
    rows, skips = [], []
    for path, by in missing:
        prov = provenance_of(by)
        if not prov:
            skips.append((path, "provenance.json %s unreadable" % by)); continue
        ex = prov.get("export") if isinstance(prov.get("export"), dict) else {}
        kit = prov.get("kit") if isinstance(prov.get("kit"), dict) else {}
        rid = ex.get("signoff_sha256") or ""
        if not rid:
            skips.append((path, "no export.signoff_sha256 (record id) in %s" % by)); continue
        key = next((k for k, v in ex.items() if v == path), None)
        kind = key or "original-kit"
        row = {"module": kit.get("module") or "", "record": rid, "key": kind, "path": path, "host": host, "by": by,
               "lec_sha256_any": ex.get("lec_sha256_any") or [], "t": now or time.time(), "status": "NEEDED"}
        if kind == "original-kit":
            row["sha256"] = (sha_of or store_sha)(rid, path)
            if not row["sha256"]:
                row["note"] = "expected hash unknown (store record does not list the file): the worker restores it only if exactly one export file has that name and the record has no other candidate"
        rows.append(row)
    return rows, skips


def restore_rows(missing, provenance_of, host, now=None, sha_of=None):
    return restore_rows_ex(missing, provenance_of, host, now, sha_of)[0]


def queue_append(qfile, rows, done=()):
    """append rows not already queued or done for the same (host, path); -> number appended"""
    seen = {(r["host"], r["path"]) for r in read_jsonl(qfile)} | {(r["host"], r["path"]) for r in done}
    new = [r for r in rows if (r["host"], r["path"]) not in seen]
    if new:
        os.makedirs(os.path.dirname(qfile), exist_ok=True)
        with open(qfile, "a") as f:
            for r in new:
                f.write(json.dumps(r, sort_keys=True) + "\n")
    return len(new)


def read_jsonl(path):
    out = []
    try:
        for ln in open(path):
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def pending(queue_rows, done_rows):
    d = {(r["host"], r["path"]) for r in done_rows}
    return [r for r in queue_rows if (r["host"], r["path"]) not in d]


def resolve(row, index_rows, root):
    """-> (kind, source file, expected sha spec) or (None, why).  Same rules as plan(): odb / signoff / lec / dir."""
    key, rid = row["key"], row["record"]
    if key in ("kit", "base"):
        return "dir", None, None
    if key == "original-kit":
        rows = [r for r in index_rows if r.get("record", "").startswith(rid[:12])]
        if not rows:
            return None, "no signed export row for record " + rid[:12], None
        e = os.path.dirname(os.path.join(root, os.path.relpath(rows[0]["db"], "/archive/opentallas-signed-1114")))
        name = os.path.basename(row["path"])
        found = []
        for dp, dn, fn in os.walk(e):
            if name in fn:
                found.append(os.path.join(dp, name))
        if not found:
            return None, "no file named %s in the export of record %s" % (name, rid[:12]), None
        want = row.get("sha256") or ""
        if want:
            for f in found:
                if sha256_file(f) == want:
                    return "original-kit", f, want
            return None, "no export file named %s has the recorded sha256 %s" % (name, want[:12]), None
        if len(found) == 1:
            return "original-kit", found[0], "any:"                    # unique name, hash unknown: accepted without a check only when nothing else could match
        return None, "%d export files named %s and no expected hash" % (len(found), name), None
    rows = [r for r in index_rows if r.get("record", "").startswith(rid[:12])]
    if not rows:
        return None, "no signed export row for record " + rid[:12], None
    base = os.path.join(root, os.path.relpath(rows[0]["db"], "/archive/opentallas-signed-1114"))
    if key == "odb":
        return "odb", base, rows[0]["sha256"]
    e = os.path.dirname(base)
    if key == "signoff":
        return "signoff", os.path.join(e, "signoff.json"), "id:" + rid
    if key == "lec":
        return "lec", os.path.join(e, "lec.json"), "any:" + ",".join(row.get("lec_sha256_any") or [])
    return None, "kind " + key + " not in the export", None


def check_sha(got, want):
    if want.startswith("id:"):
        return got.startswith(want[3:15])
    if want.startswith("any:"):
        return (not want[4:]) or got in want[4:].split(",")
    return got == want


def work(queue_rows, done_rows, index_rows, root, push, hash_file=sha256_file, now=None):
    """push(host, src, dst) / push(host, None, dst) for dirs.  -> list of done rows (status DONE or FAILED reason).  A file whose hash does not match is never pushed."""
    out = []
    for r in pending(queue_rows, done_rows):
        kind, src, want = resolve(r, index_rows, root)
        if kind is None:
            out.append(dict(r, status="UNRESTORABLE", why=src, done=now or time.time())); continue
        try:
            if kind == "dir":
                push(r["host"], None, r["path"])
            else:
                if not os.path.exists(src):
                    out.append(dict(r, status="UNRESTORABLE", why="export file missing: " + src, done=now or time.time())); continue
                got = hash_file(src)
                if not check_sha(got, want):
                    out.append(dict(r, status="UNRESTORABLE", why="export file sha256 %s does not match the signed record" % got[:12], done=now or time.time())); continue
                push(r["host"], src, r["path"])
            out.append(dict(r, status="DONE", done=now or time.time()))
        except Exception as e:
            pass                                    # transient (host down): stays pending, retried next run
    return out
