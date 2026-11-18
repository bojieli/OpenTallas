#!/usr/bin/env python3
"""live_tree.py -- TOOLS-DECOUPLE phase 2 (OWNER 11-18 "simply fix on a shared version"; COORD; FABLE-WORKFLOW-0400 (c)).

One live source tree per die per gen host instead of a chain of versioned src_* trees, replicated whole:

  <kw45>/live_<die>/                  the die's ONLY writable tree (unpublished staging).  Directories writable, every file read-only.
                                      Written only by this tool: each changed file is a new file + rename (os.replace), never an
                                      in-place write, so a file a snapshot shares can never change under it (an in-place write fails: a-w).
  <kw45>/snap_<die>/<name>/           a snapshot = `cp -al` of the live tree (never of a published tree), directories made a-w,
                                      .snap-group names the live tree (src_manifest.verify accepts the inodes it shares with it and with
                                      the die's other snapshots).  Kits launch on a snapshot (dies.<die>.src), so a running kit never
                                      sees a change; rollback = point dies.<die>.src at the previous snapshot.

A change is a src_manifest delta pack (delta.json + files/, from `src_manifest.py delta-make` or data_pack.py): it is small, so it is
copied to every host and applied there in parallel (no 49 GB replication), and every host ends with the same manifest hash.

  live_tree.py seed  --die D --from TREE --hosts h1,h2         one-time: live_<die> = a real copy (cp -a, fresh inodes) of TREE per host
  live_tree.py apply --die D --pack DIR --hosts h1,h2 [--name N] [--candidate OLD.json --out NEW.json] [--event E]
        renames the pack's files into live_<die>, snapshots it to snap_<die>/<name> on every host, checks the hashes agree, and (with
        --candidate) writes the publish_apply candidate for the snapshot (every path of the old tree rewritten to the snapshot).
  live_tree.py snap  --die D --hosts h1,h2 [--name N] ...       a snapshot of the live tree as it is (an empty change)
Then the die owner runs publish_apply.py apply --candidate NEW.json (unchanged tool); strict bind / LATCHECK run after it as warnings.

  live_tree.py reloc-pack --tree LIVE --old PREFIX --new SNAP --files rel,... [--digest PLAN:WAVE_PREPARE] --out PACK
        a pack rewriting the absolute PREFIX (e.g. the published tree the live tree was seeded from) to the snapshot path SNAP in the named
        text files (a plan names its own inputs by absolute path), re-issuing wave_prepare.json prepared_plan_sha256 / sidecar_sha256
        (as data_pack.py --digest).  Then apply it with --name = SNAP's basename.
Host side (shipped over ssh stdin, stdlib only): host-seed, host-apply.
"""
import argparse
import concurrent.futures as CF
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import time

KW45 = "/srv/opentallas-scratch2/claude/kw45"
MANIFEST, HASHFILE, LINKBASE, SNAPGROUP = ".src-manifest.json", ".src-manifest.sha256", ".link-base", ".snap-group"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ControlPath=none"]


def live_path(die, root=KW45):
    return f"{root}/live_{die}"


def snap_root(die, root=KW45):
    return f"{root}/snap_{die}"


def manifest_hash(m):
    core = {k: m[k] for k in ("main_sha", "scope", "overlay", "files")}
    return hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write_new(path, data=None, src=None, mode=0o444):
    """rename-only write: a new file next to path, then os.replace (path's old inode, shared with snapshots, is never opened for writing)"""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".lt.{os.getpid()}.{os.path.basename(path)}")
    if os.path.lexists(tmp):
        os.unlink(tmp)
    if src is not None:
        shutil.copyfile(src, tmp)
    else:
        with open(tmp, "wb" if isinstance(data, bytes) else "w") as f:
            f.write(data)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def dirs_writable(root, on=True):
    """directories only (never a file: a file chmod reaches every tree sharing its inode)"""
    for dp, dn, _fn in os.walk(root):
        m = os.lstat(dp).st_mode
        os.chmod(dp, (m | stat.S_IWUSR) if on else (m & ~0o222))


def files_readonly(root):
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            if not os.path.islink(p):
                m = os.lstat(p).st_mode
                if m & 0o222:
                    os.chmod(p, m & ~0o222)


# ------------------------------------------------------------------ host side
def host_seed(src, live):
    if os.path.exists(live):
        raise SystemExit(f"LIVE_TREE refuse: {live} exists")
    if not os.path.isfile(os.path.join(src, MANIFEST)):
        raise SystemExit(f"LIVE_TREE refuse: {src} has no {MANIFEST}")
    part = live + ".seeding"
    if os.path.exists(part):
        dirs_writable(part)
        shutil.rmtree(part)
    subprocess.run(["cp", "-a", "--reflink=never", src, part], check=True)       # a real copy: the live tree never shares a published tree's inodes
    dirs_writable(part)
    files_readonly(part)                                                          # fresh inodes: the a-w mode is the live tree's own
    for n in (LINKBASE, SNAPGROUP):
        if os.path.lexists(os.path.join(part, n)):
            os.unlink(os.path.join(part, n))
    os.rename(part, live)
    m = json.load(open(os.path.join(live, MANIFEST)))
    print(f"LIVE_TREE SEEDED {live} from {src} hash {m['manifest_hash']} files {len(m['files'])}")


def host_apply(live, pack, snaps, name):
    """pack (may be '') -> live, then snapshot live -> snaps/name.  Prints LIVE_TREE SNAP <path> <hash>."""
    m = json.load(open(os.path.join(live, MANIFEST)))
    final = os.path.join(snaps, name)
    if os.path.exists(final):                                    # idempotent rerun: the snapshot of this change exists
        sm = json.load(open(os.path.join(final, MANIFEST)))
        print(f"LIVE_TREE SNAP {final} {sm['manifest_hash']} (existed)")
        return
    if pack:
        d = json.load(open(os.path.join(pack, "delta.json")))
        if d.get("old_manifest_hash") != m["manifest_hash"]:
            raise SystemExit(f"LIVE_TREE refuse: pack is for tree {str(d.get('old_manifest_hash'))[:12]}, live is {m['manifest_hash'][:12]}")
        files = dict(m["files"])
        for path in d.get("delete") or []:
            p = os.path.join(live, path)
            if os.path.lexists(p):
                os.unlink(p)
            files.pop(path, None)
        for path, e in (d.get("add") or {}).items():
            srcf = os.path.join(pack, "files", path)
            got = sha256_file(srcf)
            if got != e["sha256"]:
                raise SystemExit(f"LIVE_TREE refuse: pack file {path} sha {got[:12]} is not the declared {e['sha256'][:12]}")
            write_new(os.path.join(live, path), src=srcf, mode=0o555 if e.get("exec") else 0o444)
            files[path] = e["sha256"]
        ov = dict(m["overlay"])
        for k in d.get("overlay_drop") or []:
            ov.pop(k, None)
        ov.update(d.get("overlay_add") or {})
        m = {"version": 1, "main_sha": d.get("new_main") or m["main_sha"], "scope": m["scope"], "overlay": ov, "files": files}
        m["manifest_hash"] = manifest_hash(m)
        write_new(os.path.join(live, MANIFEST), json.dumps(m, indent=0, sort_keys=True))
        write_new(os.path.join(live, HASHFILE), m["manifest_hash"] + "\n")
    os.makedirs(snaps, exist_ok=True)
    part = final + ".part"
    if os.path.exists(part):
        dirs_writable(part)
        shutil.rmtree(part)
    subprocess.run(["cp", "-al", live, part], check=True)       # a snapshot of the unpublished live tree (directories are new, files shared)
    for n in (LINKBASE,):
        if os.path.lexists(os.path.join(part, n)):
            os.unlink(os.path.join(part, n))
    with open(os.path.join(part, SNAPGROUP), "w") as f:         # a new file of the snapshot only
        f.write(os.path.realpath(live) + "\n")
    os.chmod(os.path.join(part, SNAPGROUP), 0o444)
    dirs_writable(part, on=False)
    os.chmod(snaps, os.lstat(snaps).st_mode | stat.S_IWUSR)
    os.rename(part, final)
    print(f"LIVE_TREE SNAP {final} {m['manifest_hash']}")


def reloc_pack(tree, old, new, files, out, digest=""):
    m = json.load(open(os.path.join(tree, MANIFEST)))
    if os.path.exists(out):
        raise SystemExit(f"LIVE_TREE refuse: {out} exists")
    add = {}
    for rel in files:
        if rel not in m["files"]:
            raise SystemExit(f"LIVE_TREE refuse: {rel} is not in the tree manifest")
        b = open(os.path.join(tree, rel), "rb").read().replace(old.rstrip("/").encode(), new.rstrip("/").encode())
        dst = os.path.join(out, "files", rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(b)
        add[rel] = {"sha256": hashlib.sha256(b).hexdigest(), "exec": False}
    if digest:
        plan_rel, wave_rel = digest.split(":")
        side_rel = os.path.join(os.path.dirname(plan_rel), "source_sidecar.json")
        def cur(rel):
            p = os.path.join(out, "files", rel)
            return p if os.path.exists(p) else os.path.join(tree, rel)
        w = json.load(open(cur(wave_rel)))
        w["prepared_plan_sha256"] = sha256_file(cur(plan_rel))
        w["sidecar_sha256"] = sha256_file(cur(side_rel))
        dst = os.path.join(out, "files", wave_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        b = (json.dumps(w, indent=1, sort_keys=True)).encode()
        open(dst, "wb").write(b)
        add[wave_rel] = {"sha256": hashlib.sha256(b).hexdigest(), "exec": False}
    json.dump({"old_manifest_hash": m["manifest_hash"], "old_main": m["main_sha"], "new_main": m["main_sha"], "scope": m["scope"],
               "add": add, "delete": [], "overlay_add": {k: v["sha256"] for k, v in add.items()}},
              open(os.path.join(out, "delta.json"), "w"), indent=0, sort_keys=True)
    print(f"LIVE_TREE RELOC-PACK {out}: {len(add)} files")
    return add


# ------------------------------------------------------------------ hub side
def on_host(host, argv, timeout=7200):
    """run this script's host-side subcommand on host (script on stdin, nothing installed there)"""
    code = open(os.path.abspath(__file__)).read()
    cmd = "python3 -I - " + " ".join(shlex.quote(a) for a in argv)
    full = ([] if host in ("localhost", "") else SSH + [host]) + (["bash", "-c", cmd] if host in ("localhost", "") else [cmd])
    p = subprocess.run(full, input=code, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def push_pack(host, pack, dest):
    if host in ("localhost", ""):
        if os.path.realpath(pack) != os.path.realpath(dest):
            subprocess.run(["rsync", "-a", "--delete", pack.rstrip("/") + "/", dest + "/"], check=True)
        return
    subprocess.run(SSH + [host, f"mkdir -p {shlex.quote(dest)}"], check=True, timeout=300)
    subprocess.run(["rsync", "-a", "--delete", "-e", " ".join(SSH), pack.rstrip("/") + "/", f"{host}:{dest}/"], check=True, timeout=3600)


def fanout(hosts, fn):
    with CF.ThreadPoolExecutor(max_workers=max(1, len(hosts))) as ex:
        return dict(zip(hosts, ex.map(fn, hosts)))


def snap_name(die, pack):
    tag = hashlib.sha256(open(os.path.join(pack, "delta.json"), "rb").read()).hexdigest()[:12] if pack else "same"
    return f"{die}_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}_{tag}"


def rewrite_candidate(old, old_tree, new_tree, new_hash, event="", pack_shas=None):
    """every string naming old_tree points at new_tree; the manifest fields carry the snapshot's hash"""
    def walk(v):
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        return v.replace(old_tree, new_tree) if isinstance(v, str) else v
    c = walk(old)
    c["tree"] = new_tree
    c["manifest_hash"] = c["src_manifest_sha"] = new_hash
    if event:
        c.setdefault("config", {})["event"] = event
    for k, rel_k in (("plan", "plan_sha256"), ("sidecar", "sidecar_sha256")):
        if pack_shas and isinstance(c.get(k), str) and c[k].startswith(new_tree + "/") and os.path.relpath(c[k], new_tree) in pack_shas:
            c[rel_k] = pack_shas[os.path.relpath(c[k], new_tree)]          # a relocated plan: its new bytes
    c["live_tree"] = {"snapshot": new_tree, "made": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "tool": "live_tree.py (TOOLS-DECOUPLE phase 2)"}
    return c


def hub_apply(a, pack):
    hosts = [h for h in a.hosts.split(",") if h]
    live, snaps = live_path(a.die, a.root), snap_root(a.die, a.root)
    name = a.name or snap_name(a.die, pack)
    stage = f"{a.root}/live_packs/{name}" if pack else ""

    def one(h):
        try:
            if pack:
                push_pack(h, pack, stage)
            return on_host(h, ["host-apply", live, stage, snaps, name])
        except Exception as e:                              # noqa: one host never stops the others
            return 1, f"{type(e).__name__}: {e}"
    res = fanout(hosts, one)
    hashes = {}
    for h, (rc, txt) in res.items():
        line = [ln for ln in txt.splitlines() if ln.startswith("LIVE_TREE SNAP ")]
        print(f"[{h}] rc {rc} " + (line[-1] if line else txt.strip()[-400:]))
        if rc == 0 and line:
            hashes[h] = line[-1].split()[3]
    ok = sorted(hashes)
    if not ok or len(set(hashes.values())) != 1:
        raise SystemExit(f"LIVE_TREE FAIL: hosts ok {ok}, hashes {hashes}")
    new_tree, new_hash = f"{snaps}/{name}", next(iter(hashes.values()))
    bad = [h for h in hosts if h not in hashes]
    print(f"LIVE_TREE OK {new_tree} hash {new_hash} hosts {','.join(ok)}" + (f" (FAILED: {','.join(bad)}: drop them from gen_hosts)" if bad else ""))
    if a.candidate:
        old = json.load(open(a.candidate))
        shas = {k: v["sha256"] for k, v in (json.load(open(os.path.join(pack, "delta.json"))).get("add") or {}).items()} if pack else {}
        c = rewrite_candidate(old, old["tree"], new_tree, new_hash, a.event, shas)
        c["hosts"] = ok
        if isinstance(c.get("config"), dict) and c["config"].get("gen_hosts"):
            c["config"]["gen_hosts"] = [h for h in c["config"]["gen_hosts"] if h in ok]
            if c["config"].get("gen_host") not in ok:
                c["config"]["gen_host"] = ok[0]
        with open(a.out, "w") as f:
            json.dump(c, f, indent=1)
        print(f"LIVE_TREE CANDIDATE {a.out} (next: publish_apply.py apply --candidate {a.out} --expect-source {old['tree']} ...)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    hs = sp.add_parser("host-seed")
    hs.add_argument("src")
    hs.add_argument("live")
    ha = sp.add_parser("host-apply")
    ha.add_argument("live")
    ha.add_argument("pack")
    ha.add_argument("snaps")
    ha.add_argument("name")
    rp = sp.add_parser("reloc-pack")
    rp.add_argument("--tree", required=True)
    rp.add_argument("--old", required=True)
    rp.add_argument("--new", required=True)
    rp.add_argument("--files", required=True)
    rp.add_argument("--digest", default="")
    rp.add_argument("--out", required=True)
    for n in ("seed", "apply", "snap"):
        p = sp.add_parser(n)
        p.add_argument("--die", required=True)
        p.add_argument("--hosts", required=True)
        p.add_argument("--root", default=KW45)
        if n == "seed":
            p.add_argument("--from", dest="src", required=True)
        else:
            if n == "apply":
                p.add_argument("--pack", required=True)
            p.add_argument("--name", default="")
            p.add_argument("--candidate", default="")
            p.add_argument("--out", default="")
            p.add_argument("--event", default="")
    a = ap.parse_args(argv)
    if a.cmd == "reloc-pack":
        reloc_pack(a.tree, a.old, a.new, [f for f in a.files.split(",") if f], a.out, a.digest)
        return 0
    if a.cmd == "host-seed":
        return host_seed(a.src, a.live)
    if a.cmd == "host-apply":
        return host_apply(a.live, a.pack, a.snaps, a.name)
    if a.cmd == "seed":
        hosts = [h for h in a.hosts.split(",") if h]
        res = fanout(hosts, lambda h: on_host(h, ["host-seed", a.src, live_path(a.die, a.root)], timeout=6 * 3600))
        for h, (rc, txt) in res.items():
            print(f"[{h}] rc {rc} {txt.strip()[-300:]}")
        return 0 if all(rc == 0 for rc, _ in res.values()) else 1
    if a.candidate and not a.out:
        raise SystemExit("--candidate needs --out")
    hub_apply(a, a.pack if a.cmd == "apply" else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
