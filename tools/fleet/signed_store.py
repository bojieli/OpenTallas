#!/usr/bin/env python3
"""signed_store.py: the durable record store of counted sign-offs (COUNT-ARCHIVE-1, OWNER 2026-11-08 22:3x:
"the hosts are volatile and we cannot point anything from a counted record to inside the directory").

A counted record lives here and on AGIdock, never only on a fleet host:
  <coord>/signed-store/records/<id[:2]>/<id>.json.gz    one file per sign-off record (schema opentallas.signed_store.v1): die, rows, verdict,
      flow tag, src commit, the scan fields the counter needs, aliases (host:path copies), archive dir, files (rel path, size, sha256),
      the signoff.json and PROVENANCE.json themselves (gz+b64), routed netlist sha256, pin table.
  <agidock>:/archive/opentallas-signed-1106/_signed-store/store-<stamp>.tar.gz    a copy, never overwritten.

Counter: tools/release_tree_plan.py reads load_records() when OT_COUNT_SOURCE=store (no host walk, no ssh).
New sign-offs: ot-autoclean's archive step calls ingest() after a verified archive, with no agent.
Consumers: `stage` pushes signed views from the archive through localhost to a host dir (the AGIdock key is localhost only).

  signed_store.py show [--die D] [--key K]
  signed_store.py stage --host H --dest DIR --die D [--key K ...] [--classes v,spef,sdc,lef,lib,odb,def,gds] [--layout die_ci|raw]
  signed_store.py verify [--sample N]      re-hash archive files on AGIdock against the manifest
"""
import argparse
import base64
import fcntl
import gzip
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time

HOME = os.path.expanduser("~")
STORE = os.environ.get("OT_SIGNED_STORE", os.path.join(HOME, "coord", "signed-store"))
RECORDS = "records"
SCHEMA = "opentallas.signed_store.v1"
ARCHIVE_ROOT = "/archive/opentallas-signed-1106"
AGIDOCK = ["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
           "-i", os.path.join(HOME, ".ssh/agidock_ot"), "ubuntu@155.103.253.53"]
SCAN_FIELDS = ("name", "top", "generated", "host", "pins_path", "src_commit", "flow_tag", "prov_file", "resign", "routed_db",
               "build_commit", "lec", "versioned", "resign_error", "legacy", "source_commit")
CLASS_SUFFIX = {"v": (".v", ".v.gz"), "spef": (".spef", ".spef.gz"), "sdc": (".sdc",), "lef": (".lef",), "lib": (".lib", ".lib.gz"),
                "odb": (".odb",), "def": (".def", ".def.gz"), "gds": (".gds", ".gds.gz")}
DIE_CI_NAMES = ("6_final.v", "6_final.spef", "6_final.sdc")


def records_dir(store=None):
    return os.path.join(store or STORE, RECORDS)


def entry_path(eid, store=None):
    return os.path.join(records_dir(store), eid[:2], eid + ".json.gz")


def blob(obj):
    return base64.b64encode(gzip.compress(json.dumps(obj, sort_keys=True).encode(), 9)).decode()


def unblob(s):
    return json.loads(gzip.decompress(base64.b64decode(s))) if s else None


def read_entry(p):
    with gzip.open(p, "rt") as fh:
        return json.load(fh)


def read_manifest(store=None):
    """every store entry (one file per sign-off record; a removed file is a removed manifest row)"""
    out = []
    root = records_dir(store)
    for dp, _, fns in os.walk(root):
        for fn in sorted(fns):
            if fn.endswith(".json.gz"):
                out.append(read_entry(os.path.join(dp, fn)))
    return sorted(out, key=lambda e: e["id"])


def write_entry(e, store=None):
    """atomic; never rewrites an existing entry with different content (sign-off records are immutable, id = sha256 of signoff.json)"""
    p = entry_path(e["id"], store)
    data = gzip.compress((json.dumps(e, sort_keys=True) + "\n").encode(), 9, mtime=0)
    if os.path.exists(p):
        return False
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".e.")
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    os.replace(tmp, p)
    return True


def store_lock(store=None):
    d = store or STORE
    os.makedirs(d, exist_ok=True)
    fh = open(os.path.join(d, ".lock"), "w")
    fcntl.flock(fh, fcntl.LOCK_EX)
    return fh


def _alias_split(a):
    h, _, p = a.partition(":")
    return h, p


def load_records(store=None):
    """-> (records, pins): one scan-format record per alias (the same dicts scan_host returned, so RETIRED / COUNT-REVOKED /
    COUNT-CREDIT keep working on their host:path keys) and pins {(scan_host, pins_path): stored pin table}.  No host is read."""
    recs, pins = [], {}
    for e in read_manifest(store):
        if str(e.get("origin", "")).startswith("origin/main:"):
            continue                                # counted from the git tree (main_records); the entry holds its archive copy
        s = {k: e["scan"][k] for k in SCAN_FIELDS if k in (e.get("scan") or {})}
        p = e.get("pins")
        for a in e.get("aliases") or [e["origin"]]:
            h, ap = _alias_split(a)
            r = dict(s, path=ap, scan_host=h, store_id=e["id"], archive=e.get("archive"), netlist_sha=e.get("netlist_sha"))
            r.setdefault("versioned", bool(r.get("src_commit") and r.get("flow_tag")))
            recs.append(r)
            if p is not None and r.get("pins_path"):
                pins[(h, r["pins_path"])] = p
    return recs, pins


def entry_files(e, classes=None):
    """[[rel, size, sha, archive base]]: the unit's files, then the extra archived sets (routed views found outside the unit)"""
    fl = [list(f[:3]) + [e["archive"]] for f in e.get("files") or []]
    for x in e.get("extra") or []:
        fl += [list(f[:3]) + [x["archive"]] for f in x["files"]]
    if classes:
        suf = tuple(y for c in classes for y in CLASS_SUFFIX[c])
        fl = [f for f in fl if f[0].endswith(suf)]
    return fl


def add_extra(eid, archive, files, note, store=None):
    """add an archived file set to an entry (the record itself stays immutable: only 'extra' grows); an extra with the same note is not added twice"""
    p = entry_path(eid, store)
    with store_lock(store):
        e = read_entry(p)
        if any(x.get("note") == note for x in e.get("extra") or []):
            return False
        e.setdefault("extra", []).append(dict(archive=archive, files=files, note=note))
        data = gzip.compress((json.dumps(e, sort_keys=True) + "\n").encode(), 9, mtime=0)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".e.")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, p)
    return True


def late_provenance(eid, scan, prov_json, archive, files, store=None, changed_logs=()):
    """COUNT-ARCHIVE-2 11-09: a re-sign writes PROVENANCE.json (and lec/) after signoff.json; an ingest that ran in between stored
    the record without them, so the counter saw it unversioned (QC NK nk_eco2_resign_fc, 02:08 vs 03:26).  Same sign-off (same id):
    take the scan fields and provenance once, and the new unit files as an archived extra set.  Only for an entry that is not
    versioned yet (no provenance, or an unversioned one); a versioned provenance is never replaced.  -> True when the entry changed."""
    p = entry_path(eid, store)
    with store_lock(store):
        e = read_entry(p)
        # 11-09 07:0x: an entry whose stored provenance is UNVERSIONED (no flow tag + src commit; e.g. the kit's own
        # i1/PROVENANCE.json taken before the re-sign wrote resign_gj/PROVENANCE.json, HBM rootg1c) also takes the fresh,
        # versioned one; the old one is kept in late_provenance.replaced.  A versioned provenance is never replaced.
        if (e.get("flow_tag") and e.get("src_commit")) or not scan.get("prov_file") or not prov_json:
            return False
        if not (scan.get("flow_tag") and scan.get("src_commit")) or scan.get("prov_file") == e.get("prov_file"):
            return False
        replaced = dict(prov_file=e.get("prov_file"), provenance_json=e.get("provenance_json")) if e.get("provenance_json") else None
        e["scan"] = dict(e.get("scan") or {}, **{k: scan[k] for k in SCAN_FIELDS if k in scan})
        for k in ("flow_tag", "src_commit", "prov_file"):
            if scan.get(k) is not None:
                e[k] = scan[k]
        e["provenance_json"] = blob(prov_json)
        note = "late-provenance %s" % time.strftime("%F %T %Z")
        if files:
            e.setdefault("extra", []).append(dict(archive=archive, files=files, note=note))
        e["late_provenance"] = dict(time=time.strftime("%F %T %Z"), prov_file=scan["prov_file"], files=len(files or []),
                                    changed_logs_kept_first_version=list(changed_logs), replaced=replaced)
        data = gzip.compress((json.dumps(e, sort_keys=True) + "\n").encode(), 9, mtime=0)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), prefix=".e.")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, p)
    return True


def find_entries(die, keys=None, entries=None):
    es = read_manifest() if entries is None else entries
    keys = set(keys or ())
    out = []
    for e in es:
        rows = [r for r in e.get("rows") or [] if r.get("die") == die]
        if rows and (not keys or keys & {r["key"] for r in rows}):
            out.append(e)
    return out


COLLECT_PY = r"""
import json, os, sys
out = {}
for p in sys.stdin.read().split("\n"):
    if not p:
        continue
    o = {}
    try:
        o["signoff"] = open(p).read()
    except OSError as e:
        out[p] = {"err": str(e)[:100]}
        continue
    q = os.path.dirname(p)
    for _ in range(7):
        f = os.path.join(q, "PROVENANCE.json")
        if os.path.exists(f):
            o["prov"], o["prov_file"] = open(f).read(), f
            break
        q = os.path.dirname(q)
    out[p] = o
print(json.dumps(out))
"""


def _rtp():
    """the counter module (scan and pin logic), in host-reading mode whatever the live source is"""
    sys.path.insert(0, os.path.join(HOME, "coord", "tools"))
    import release_tree_plan as rtp
    rtp.SIGNED_SOURCE = "hosts"
    return rtp


def netlist_of(rec, shas):
    """sha256 of the record's routed 6_final.v, the same file rec_netlist_sha reads; shas = {abs path: [size, sha]}"""
    if rec.get("routed_db"):
        v = shas.get(os.path.join(os.path.dirname(rec["routed_db"]), "6_final.v"))
        return v[1] if v else None
    base = os.path.dirname(os.path.dirname(rec["path"])) + "/run/results/"
    c = [v for p, v in shas.items() if p.startswith(base) and p.endswith("/base/6_final.v")]
    return c[0][1] if len(c) == 1 else None


def ingest(host, shas, archive_base, runner=None, store=None, rtp=None, aliases=None):
    """called by the auto-archive after a verified copy (shas = {abs path: [size, sha256]} of the archived unit).  One store entry per
    SIGNED record in the unit, using the counter's own scan and pin code on the host.  Unsigned records and known ids are skipped."""
    rtp = rtp or _rtp()
    run = runner or (lambda cmd, inp: subprocess.run(host_argv(host) + [cmd], input=inp, capture_output=True, text=True, timeout=600))
    paths = sorted(p for p in shas if os.path.basename(p) == "signoff.json" or p.endswith(".signoff.json"))
    if not paths:
        return []
    r = run("python3 -I -c %s" % shlex.quote(rtp.SCAN_PY), "\n".join(paths) + "\nOT_WALK_RC=0\n")
    recs = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else []
    if not recs:
        return []
    c = run("python3 -I -c %s" % shlex.quote(COLLECT_PY), "\n".join(x["path"] for x in recs) + "\n")
    texts = json.loads(c.stdout)
    for x in recs:
        x["scan_host"] = host
    hosts0 = rtp.HOSTS
    rtp.HOSTS = [host]
    try:
        pin = rtp.fetch_rec_pins(recs)
    finally:
        rtp.HOSTS = hosts0
    done = []
    with store_lock(store):
        for x in recs:
            t = texts.get(x["path"]) or {}
            if "signoff" not in t:
                continue
            d = json.loads(t["signoff"])
            p = pin.get((host, x.get("pins_path")))
            e = dict(schema=SCHEMA, id=hashlib.sha256(t["signoff"].encode()).hexdigest(), origin="%s:%s" % (host, x["path"]), rows=[],
                     verdict=d.get("verdict"), local_verdict=d.get("local_verdict"), flow_tag=x.get("flow_tag"), src_commit=x.get("src_commit"),
                     generated=x.get("generated"), name=x.get("name"), top=x.get("top"), scan={k: x[k] for k in SCAN_FIELDS if k in x},
                     aliases=sorted(set((aliases or {}).get(x["path"], []) + ["%s:%s" % (host, x["path"])])), archive=archive_base,
                     files=[[f.lstrip("/"), v[0], v[1]] for f, v in sorted(shas.items())], bytes=sum(v[0] for v in shas.values()),
                     netlist_sha=netlist_of(x, shas), pins=dict(p, shapes={k: [list(q) for q in v] for k, v in p["shapes"].items()}) if p and p.get("shapes") else p,
                     signoff_json=blob(d), provenance_json=blob(json.loads(t["prov"])) if t.get("prov") else None, prov_file=t.get("prov_file"),
                     ingest=dict(kind="auto-archive", time=time.strftime("%F %T %Z")))
            if write_entry(e, store):
                done.append(e["id"])
    return done


def host_argv(host):
    return ["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", host]


def stream_files(entry, host, destdir, files, rename=None, throttle="", timeout=7200):
    """archive -> localhost -> host:destdir, verified by sha256 on the host.  files = [[rel, size, sha, archive base]], one base; rename {rel: name}"""
    base = files[0][3] if files and len(files[0]) > 3 else entry["archive"]
    rels = [f[0] for f in files]
    src = (f"set -o pipefail; cd {shlex.quote(base)} && tar --null -T - -cf - ")
    dst = f"mkdir -p {shlex.quote(destdir)} && tar -C {shlex.quote(destdir)} -xf -"
    p1 = subprocess.Popen(AGIDOCK + [src], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(host_argv(host) + [dst], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p1.stdin.write(("\0".join(rels) + "\0").encode()); p1.stdin.close()
    p1.stdout.close()
    out, err = p2.communicate(timeout=timeout)
    if p1.wait(60) or p2.returncode:
        raise RuntimeError(f"stream {base} -> {host}:{destdir} failed: {err.decode(errors='replace')[-200:]}")
    want = {os.path.join(destdir, (rename or {}).get(f[0], f[0])): f[2] for f in files}
    if rename:
        mv = "; ".join(f"mv -f {shlex.quote(os.path.join(destdir, r))} {shlex.quote(os.path.join(destdir, n))}" for r, n in rename.items())
        subprocess.run(host_argv(host) + [f"mkdir -p {shlex.quote(destdir)} && {mv}"], check=True, timeout=120)
    chk = "\n".join(f"{sha}  {p}" for p, sha in want.items()) + "\n"
    r = subprocess.run(host_argv(host) + ["sha256sum --quiet -c -"], input=chk, text=True, capture_output=True, timeout=7200)
    if r.returncode:
        raise RuntimeError(f"sha mismatch on {host}: {r.stdout[-300:]}")
    return len(want)


def stage(args):
    """push the signed views of rows to host:dest.  layout die_ci: <dest>/<die>/<type>/6_final.{v,spef,sdc} (die_ci.resolve_view);
    raw: <dest>/<key>/<archive-relative path>.  Writes <dest>/.../FETCHED.json with manifest id, archive and sha list."""
    entries = find_entries(args.die, args.key)
    if not entries:
        raise SystemExit(f"no store entries for die {args.die} keys {args.key}")
    classes = args.classes.split(",") if args.classes else ["v", "spef", "sdc", "lef", "lib"]
    done = 0
    for e in entries:
        keys = [r["key"] for r in e["rows"] if r.get("die") == args.die and (not args.key or r["key"] in args.key)]
        fl = entry_files(e, classes)
        if args.layout == "die_ci":
            names = {}
            for f in fl:
                b = os.path.basename(f[0])
                if b in DIE_CI_NAMES and b not in names.values():
                    names[f[0]] = b
            fl = [f for f in fl if f[0] in names]
            for k in keys:
                d = os.path.join(args.dest, args.die, k)
                for base in {f[3] for f in fl}:
                    sub = [f for f in fl if f[3] == base]
                    stream_files(e, args.host, d, sub, {f[0]: names[f[0]] for f in sub})
                done += 1
        else:
            for k in keys:
                d = os.path.join(args.dest, k)
                for base in {f[3] for f in fl}:
                    stream_files(e, args.host, d, [f for f in fl if f[3] == base])
                done += 1
    print(f"stage: {done} rows to {args.host}:{args.dest}")
    return 0


def verify(args):
    entries = read_manifest()
    if args.sample:
        import random
        random.seed(int(time.time()))
        entries = random.sample(entries, min(args.sample, len(entries)))
    bad = 0
    n = 0
    for e in entries:
        fl = entry_files(e)
        n += len(fl)
        fail = ""
        for base in sorted({f[3] for f in fl}):
            chk = "\n".join(f"{f[2]}  {f[0]}" for f in fl if f[3] == base) + "\n"
            r = subprocess.run(AGIDOCK + [f"cd {shlex.quote(base)} && nice -n 15 sha256sum --quiet -c -"], input=chk,
                               capture_output=True, text=True, timeout=7200)
            if r.returncode:
                fail += f" {base}: {r.stdout[:300]}{r.stderr[:200]}"
        if fail:
            bad += 1
            print(f"MISMATCH {e['id']}{fail}")
    print(f"verify: {len(entries)} entries, {n} files, {bad} entries with mismatches")
    return 1 if bad else 0


def show(args):
    for e in read_manifest():
        rows = e.get("rows") or []
        if args.die and not any(r.get("die") == args.die for r in rows):
            continue
        if args.key and not any(r.get("key") == args.key for r in rows):
            continue
        print(json.dumps({k: e.get(k) for k in ("id", "rows", "verdict", "flow_tag", "src_commit", "archive", "origin")}), f"files {len(e.get('files') or [])}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show"); s.add_argument("--die"); s.add_argument("--key")
    s = sub.add_parser("stage"); s.add_argument("--host", required=True); s.add_argument("--dest", required=True); s.add_argument("--die", required=True)
    s.add_argument("--key", action="append"); s.add_argument("--classes"); s.add_argument("--layout", choices=("die_ci", "raw"), default="raw")
    s = sub.add_parser("verify"); s.add_argument("--sample", type=int)
    a = ap.parse_args(argv)
    return {"show": show, "stage": stage, "verify": verify}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
