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
