#!/usr/bin/env python3
"""HBM-NEXT-CMTP: bit-exact goldens for the next die (AR, MTP accept + reject, 4 users) from the RELEASED
DeepSeek-V4.1-Flash checkpoint, with digests, for lane HBM-NEXT-VEH.

Where the bytes are: the full snapshot (476 GB) is only on the workstation; the fleet (ot-epyc5) has a 14 GB SPARSE
copy holding every tensor whole except the routed experts, the Engram tables, the token embedding and the MTP stages
(tools/hgi_sim/ckpt_subset.py).  The link is ~3.5 MB/s, so the golden runs ON THE FLEET (owner rule: no heavy local
runs) over a FETCH-ON-DEMAND checkpoint: the first read of a missing tensor (or embedding / Engram row) writes a
request file on the fleet and blocks; a light local daemon (`serve`) copies exactly those byte ranges from the
workstation snapshot into the fleet's sparse shard files and acknowledges.  Bytes never fetched read as zero only if
the ledger is wrong, and the ledger is the request log (every fetched range is recorded), so a golden can be re-run
from its ledger offline.

GOLDENS (all HDC_V41_ARITH=chunk8, hdc_golden_v41 via rtl_v41_fullshape_layer_campaign.build_model, the pinned
golden of every DS lane):
  ar_mtp_g5   EXISTING (results/arch/hbm_mtp_1015/sim_gamma5, released checkpoint, real DSpark drafter): prompt [0],
              y 5, drafts [223, 18, 16, 223, 18], targets [223, 939, 16, 23, 89804, 16]: draft 1 ACCEPTED, draft 2
              REJECTED (accept + reject paths), 6 verify positions = 6 AR columns (positions 1..6), per-layer h / pre
              of every position, the draft block rows and the seeds.  `package` checks its npz against the committed
              SHA256SUMS and writes a per-array digest manifest.
  mtp_all5    NEW: forced drafter = the AR continuation (no corruption): all 5 drafts accepted + the bonus token
              (ds_mtp_kernels.golden --corrupt 5 --layer-major: also proves the layer-major (verify) order equals AR).
  mu4         NEW: 4 independent users, 2-token prompts [u0, u1] (distinct histories), positions 0 and 1 each: the
              4-user step's golden = 4 independent AR tokens; per-layer h / pre digests, argmax.

    python3 tools/hbm_next/goldens.py package --src DIR --out DIR                       (local, light)
    python3 tools/hbm_next/goldens.py serve --remote ot-epyc5 --dir FLEETDIR            (local, light I/O daemon)
    python3 tools/hbm_next/goldens.py serve2 --remote ot-epyc5 --dir FLEETDIR --writers 4  (persistent connections,
                                                                   dedupe + routed-expert prefetch; ~30x serve)
    PYTHONPATH=tools python3 tools/hbm_next/goldens.py mu4 --snap SPARSE --fetch FLEETDIR/fetch --out DIR    (fleet)
    PYTHONPATH=tools python3 tools/hbm_next/goldens.py mtp_all5 --snap SPARSE --fetch FLEETDIR/fetch --out DIR (fleet)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))

F = np.float32
SPARSE_ALWAYS = re.compile(r"(\.ffn\.experts\.\d+\.)|(engram\.embed\.)|(^embed\.weight$)|(^mtp\.)")
MU_PROMPTS = [[0, 5], [2, 12366], [3, 4521], [4, 17808]]     # 4 users, distinct 2-token histories (vocab ids);
# user 0 = [0, 5] is the CONTROL: its positions 0 / 1 are the committed ar_mtp_g5 golden's positions 0 / 1 (prompt [0],
# y = 5), so the fleet + fetch-on-demand path must reproduce h_0_L / h_1_L of golden_spec.npz bit for bit


# ======================================================================================================================
# fetch-on-demand checkpoint (fleet side)
# ======================================================================================================================
def fetch_checkpoint_class():
    import rtl_v41_fullshape_layer_campaign as LC

    class FetchCheckpoint(LC.Checkpoint):
        """LC.Checkpoint over the fleet's sparse shards; a range not in the ledger is fetched before it is read."""

        def __init__(self, snap: Path, fetch: Path):
            super().__init__(snap)
            self.fetch = Path(fetch)
            (self.fetch / "req").mkdir(parents=True, exist_ok=True)
            (self.fetch / "done").mkdir(parents=True, exist_ok=True)
            self.ledger = self.fetch / "ledger.jsonl"
            self.have = set()
            sub = json.loads((snap / "SUBSET.json").read_text()) if (snap / "SUBSET.json").exists() else {}
            for L, ex in (sub.get("experts") or {}).items():
                for e in ex:
                    for w in ("w1", "w2", "w3"):
                        for sfx in ("weight", "scale"):
                            self.have.add(f"layers.{L}.ffn.experts.{e}.{w}.{sfx}")
            if self.ledger.exists():
                for ln in self.ledger.read_text().splitlines():
                    x = json.loads(ln)
                    self.have.add(x["key"])
            self.nreq = 0

        def _need(self, key, f, ranges):
            if key in self.have:
                return
            rid = f"{os.getpid()}_{self.nreq:06d}"
            self.nreq += 1
            (self.fetch / "req" / f"{rid}.json").write_text(json.dumps(dict(key=key, file=f, ranges=ranges)))
            t0 = time.time()
            done = self.fetch / "done" / f"{rid}.json"
            while not done.exists():
                time.sleep(0.5)
                if time.time() - t0 > 7200:
                    raise SystemExit(f"fetch {key} not served in 2 h")
            with open(self.ledger, "a") as fh:
                fh.write(json.dumps(dict(key=key, file=f, ranges=ranges, sha256=json.loads(done.read_text())["sha256"]))
                         + "\n")
            self.have.add(key)
            self._mm.pop(f, None)
            self._hdr.pop(f, None)

        def raw(self, name):
            if SPARSE_ALWAYS.search(name) and not name.startswith("embed.") and "engram.embed" not in name:
                m, base, f = self.meta(name)
                s, e = m["data_offsets"]
                self._need(name, f, [[base + s, e - s]])
            return super().raw(name)

        def rows(self, name, ids):
            if name == "embed.weight" or "engram.embed" in name:
                m, base, f = self.meta(name)
                s, e = m["data_offsets"]
                width = {"BF16": 2, "F32": 4, "F8_E4M3": 1, "F8_E8M0": 1}[m["dtype"]]
                rb = m["shape"][1] * width
                for i in sorted(set(int(x) for x in np.asarray(ids).reshape(-1))):
                    self._need(f"{name}#{i}", f, [[base + s + i * rb, rb]])
            return super().rows(name, ids)
    return FetchCheckpoint


# ======================================================================================================================
# the local daemon: serve byte ranges from the workstation snapshot into the fleet's sparse shards
# ======================================================================================================================
APPLY = r'''
import sys, json, hashlib, os
d = sys.argv[1]; hdr = json.loads(sys.stdin.buffer.readline())
h = hashlib.sha256()
with open(os.path.join(d, hdr["file"]), "r+b") as fh:
    for off, n in hdr["ranges"]:
        b = sys.stdin.buffer.read(n)
        assert len(b) == n, (off, n, len(b))
        fh.seek(off); fh.write(b); h.update(b)
print(h.hexdigest())
'''


def serve(a):
    import rtl_v41_fullshape_layer_campaign as LC
    snap = LC.HF
    remote, fd, snapdir = a.remote, a.dir.rstrip("/"), a.snap.rstrip("/")
    log = open(a.log, "a") if a.log else sys.stdout
    served = 0
    while True:
        r = subprocess.run(["ssh", "-o", "ControlPath=none", remote, f"ls {fd}/req 2>/dev/null"], capture_output=True,
                           text=True, timeout=120)
        reqs = sorted(x for x in r.stdout.split() if x.endswith(".json"))
        for q in reqs:
            if subprocess.run(["ssh", "-o", "ControlPath=none", remote, f"test -e {fd}/done/{q}"],
                              timeout=120).returncode == 0:
                continue
            spec = json.loads(subprocess.run(["ssh", "-o", "ControlPath=none", remote, f"cat {fd}/req/{q}"],
                                             capture_output=True, text=True, timeout=120, check=True).stdout)
            h = hashlib.sha256()
            payload = [json.dumps(dict(file=spec["file"], ranges=spec["ranges"])).encode() + b"\n"]
            with open(snap / spec["file"], "rb") as fh:
                for off, n in spec["ranges"]:
                    fh.seek(off)
                    b = fh.read(n)
                    h.update(b)
                    payload.append(b)
            t0 = time.time()
            p = subprocess.run(["ssh", "-o", "ControlPath=none", remote, f"python3 -c '{APPLY}' {snapdir}"],
                               input=b"".join(payload), capture_output=True, timeout=7200)
            got = p.stdout.decode().strip()
            if p.returncode or got != h.hexdigest():
                print(f"FAIL {q} {spec['key']}: rc {p.returncode} {p.stderr.decode()[-300:]}", file=log, flush=True)
                continue
            subprocess.run(["ssh", "-o", "ControlPath=none", remote,
                            f"echo '{json.dumps(dict(sha256=got))}' > {fd}/done/{q}"], timeout=120, check=True)
            served += 1
            nb = sum(n for _, n in spec["ranges"])
            print(f"{time.strftime('%H:%M:%S')} served {q} {spec['key']} {nb / 1e6:.1f} MB "
                  f"{nb / 1e6 / max(1e-3, time.time() - t0):.2f} MB/s (total {served})", file=log, flush=True)
        if a.until and Path(a.until).exists():
            return 0
        if a.stop_remote and subprocess.run(["ssh", "-o", "ControlPath=none", remote, f"test -e {a.stop_remote}"],
                                            timeout=120).returncode == 0:
            print("stop marker seen", file=log, flush=True)
            return 0
        time.sleep(a.poll)


# serve2 (10-19, HBM-NEXT-CMTP): the same protocol (req/ -> done/, byte ranges into the fleet's sparse shards, the done
# file carries the sha256 the fleet ledger records), but over PERSISTENT ssh connections: one watcher streams new
# requests (0.2 s poll on the fleet), one ack writer, `--writers` data writers in parallel (measured 10-19: one stream
# ~5 MB/s, 4 streams ~20 MB/s, an ssh connect 2.6 s -- serve paid ~4 connects a tensor).  It also
#   * dedupes: a key already applied (the two goldens request the same tensors; each fleet process only knows its own
#     ledger) is acknowledged at once, no bytes moved;
#   * prefetches the routed expert: the first request of layers.L.ffn.experts.E.* applies all 6 tensors of expert E
#     (w1 / w2 / w3 weight + scale; the golden always reads all 6), so the 5 sibling requests are acknowledged at once.
# Every applied range is hashed locally and on the fleet; a mismatch is a FAIL (logged, the key is retried).
REMOTE_WATCH = r'''
import os, sys, time, json
d, stop = sys.argv[1], sys.argv[2]
seen, beat = set(), time.time()
while True:
    if stop and os.path.exists(stop):
        print("STOP", flush=True)
        break
    try:
        qs = sorted(x for x in os.listdir(d + "/req") if x.endswith(".json"))
    except FileNotFoundError:
        qs = []
    for q in qs:
        if q in seen:
            continue
        if os.path.exists(d + "/done/" + q):
            seen.add(q)
            continue
        try:
            spec = json.load(open(d + "/req/" + q))
        except Exception:
            continue
        seen.add(q)
        print(json.dumps(dict(rid=q, spec=spec)), flush=True)
    if time.time() - beat > 30:
        print("BEAT", flush=True)
        beat = time.time()
    time.sleep(0.2)
'''
REMOTE_WRITE = r'''
import os, sys, json, hashlib
snap, d = sys.argv[1], sys.argv[2]
inp = sys.stdin.buffer
while True:
    ln = inp.readline()
    if not ln:
        break
    h = json.loads(ln)
    if h["op"] == "apply":
        sh = hashlib.sha256()
        with open(os.path.join(snap, h["file"]), "r+b") as fh:
            for off, n in h["ranges"]:
                b = inp.read(n)
                assert len(b) == n, (off, n, len(b))
                fh.seek(off); fh.write(b); sh.update(b)
        print(json.dumps(dict(key=h["key"], sha256=sh.hexdigest())), flush=True)
    elif h["op"] == "ack":
        p = os.path.join(d, "done", h["rid"])
        with open(p + ".tmp", "w") as fh:
            fh.write(json.dumps(dict(sha256=h["sha256"])) + "\n")
        os.replace(p + ".tmp", p)
        print(json.dumps(dict(rid=h["rid"])), flush=True)
'''
EXPERT = re.compile(r"^(layers\.\d+\.ffn\.experts\.\d+)\.(w[123])\.(weight|scale)$")


def _remote_py(script, *args):
    import base64
    b = base64.b64encode(script.encode()).decode()
    return f"python3 -u -c \"import base64;exec(base64.b64decode('{b}'))\" " + " ".join(args)


def serve2(a):
    import queue
    import threading
    import rtl_v41_fullshape_layer_campaign as LC
    snap = LC.HF
    ck = LC.Checkpoint(snap)
    remote, fd, snapdir = a.remote, a.dir.rstrip("/"), a.snap.rstrip("/")
    log = open(a.log, "a") if a.log else sys.stdout
    lk = threading.Lock()

    def say(m):
        with lk:
            print(f"{time.strftime('%H:%M:%S')} {m}", file=log, flush=True)

    def conn(script, *args):
        return subprocess.Popen(["ssh", "-T", "-o", "ControlPath=none", "-o", "ServerAliveInterval=30", remote,
                                 _remote_py(script, *args)], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def ranges_of(name):
        m, base, f = ck.meta(name)
        s, e = m["data_offsets"]
        return f, [[base + s, e - s]]

    applied = {}            # key -> sha256 (applied on the fleet, verified)
    waiters = {}            # key -> [rid] (requests waiting for the key)
    inflight = set()
    work = queue.PriorityQueue()
    seq = [0]
    stats = dict(req=0, acked_dedupe=0, applied=0, mb=0.0, t0=time.time())

    ack_c = conn(REMOTE_WRITE, snapdir, fd)
    ack_lk = threading.Lock()

    def ack(rid, sha):
        with ack_lk:
            ack_c.stdin.write((json.dumps(dict(op="ack", rid=rid, sha256=sha)) + "\n").encode())
            ack_c.stdin.flush()
            r = json.loads(ack_c.stdout.readline())
            assert r["rid"] == rid, r

    def enqueue(key, f, rg, prio):
        if key in applied or key in inflight:
            return
        inflight.add(key)
        seq[0] += 1
        work.put((prio, seq[0], key, f, rg))

    def writer(i):
        c = conn(REMOTE_WRITE, snapdir, fd)
        while True:
            prio, _, key, f, rg = work.get()
            if key is None:
                c.stdin.close()
                return
            h = hashlib.sha256()
            parts = [json.dumps(dict(op="apply", key=key, file=f, ranges=rg)).encode() + b"\n"]
            with open(snap / f, "rb") as fh:
                for off, n in rg:
                    fh.seek(off)
                    b = fh.read(n)
                    h.update(b)
                    parts.append(b)
            t0 = time.time()
            try:
                c.stdin.write(b"".join(parts))
                c.stdin.flush()
                r = json.loads(c.stdout.readline())
            except Exception as e:  # connection lost: reconnect, retry the key
                say(f"writer {i} reconnect after {e!r} on {key}")
                c = conn(REMOTE_WRITE, snapdir, fd)
                work.put((prio, seq[0], key, f, rg))
                continue
            nb = sum(n for _, n in rg)
            if r.get("sha256") != h.hexdigest():
                say(f"FAIL {key}: fleet sha {r.get('sha256')} != local {h.hexdigest()} (retry)")
                work.put((prio, seq[0], key, f, rg))
                continue
            with lk:
                applied[key] = r["sha256"]
                inflight.discard(key)
                ws = waiters.pop(key, [])
                stats["applied"] += 1
                stats["mb"] += nb / 1e6
            for rid in ws:
                ack(rid, r["sha256"])
            el = time.time() - stats["t0"]
            say(f"w{i} applied {key} {nb / 1e6:.1f} MB {nb / 1e6 / max(1e-3, time.time() - t0):.2f} MB/s"
                f"{' (requested)' if ws else ' (prefetch)'}; totals req {stats['req']} applied {stats['applied']} "
                f"dedupe {stats['acked_dedupe']} {stats['mb']:.0f} MB {stats['mb'] / max(1.0, el):.2f} MB/s avg")

    ths = [threading.Thread(target=writer, args=(i,), daemon=True) for i in range(a.writers)]
    for t in ths:
        t.start()
    while True:
        w = conn(REMOTE_WATCH, fd, a.stop_remote or "")
        say(f"serve2 watching {remote}:{fd} with {a.writers} writers")
        for ln in w.stdout:
            ln = ln.decode().strip()
            if ln == "BEAT":
                continue
            if ln == "STOP":
                say("stop marker seen")
                return 0
            q = json.loads(ln)
            rid, spec = q["rid"], q["spec"]
            key = spec["key"]
            stats["req"] += 1
            with lk:
                if key in applied:
                    sha, now = applied[key], True
                else:
                    now = False
                    waiters.setdefault(key, []).append(rid)
            if now:
                stats["acked_dedupe"] += 1
                ack(rid, sha)
                continue
            with lk:
                enqueue(key, spec["file"], spec["ranges"], 0)
                m = EXPERT.match(key)
                if m:
                    for wn in ("w1", "w3", "w2"):
                        for sfx in ("weight", "scale"):
                            k2 = f"{m.group(1)}.{wn}.{sfx}"
                            if k2 != key:
                                f2, rg2 = ranges_of(k2)
                                enqueue(k2, f2, rg2, 1)
        say("watcher connection ended; reconnecting in 5 s")
        time.sleep(5)


# ======================================================================================================================
# goldens (fleet side)
# ======================================================================================================================
def _digest(x):
    a = np.ascontiguousarray(np.asarray(x))
    return hashlib.sha256(a.tobytes()).hexdigest()


def mu4(a):
    """4 independent users: prompt [t0, t1] at positions 0, 1; the step = position 1 of every user (AR, each user's own
    KV state).  Records per user and position: argmax, logits digest, per-layer h / pre digests (+ arrays npz)."""
    import hdc_golden_v41 as V
    import rtl_v41_fullshape_layer_campaign as LC
    from hgi_sim import ds_mtp_kernels as K
    K.npy_check()
    FC = fetch_checkpoint_class()
    ck = FC(Path(a.snap), Path(a.fetch))
    m, init_sha = LC.build_model(ck, engram=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    arrs, users = {}, []
    t0 = time.time()
    for u, prompt in enumerate(MU_PROMPTS[:a.users]):
        state = m.new_state()
        rec = dict(user=u, prompt=prompt, positions=[])
        for p, t in enumerate(prompt):
            state["tokens"].append(int(t))
            ctx = {"pos": p, "hist": list(state["tokens"]),
                   "h": np.repeat(ck.rows("embed.weight", [t]), m.hc, axis=0).astype(F),
                   "pre": np.array([1, 0, 0, 0], dtype=F)[:m.hc]}
            lay = []
            for L in range(m.L):
                m.layer(L, ctx, state)
                arrs[f"u{u}_p{p}_h{L}"], arrs[f"u{u}_p{p}_pre{L}"] = ctx["h"].copy(), ctx["pre"].copy()
                lay.append(dict(L=L, h=_digest(ctx["h"]), pre=_digest(ctx["pre"])))
                for k_ in [k_ for k_ in m.w if ".ffn.experts." in k_ or k_.startswith(f"layers.{L}.")]:
                    del m.w[k_]
            xf = V.rmsnorm_fold(m.hc_pre(ctx["h"], ctx["pre"]), m.w["norm.weight"], m.eps)
            lg = V.mv(m.w["head.weight"], xf)
            rec["positions"].append(dict(pos=p, token=int(t), argmax=int(np.argmax(lg)), margin=float(V.margin(lg)),
                                         logits_sha256=LC.digest(lg), layers=lay))
            print(f"user {u} pos {p} token {t} -> {int(np.argmax(lg))} ({time.time() - t0:.0f} s)", flush=True)
        users.append(rec)
    control = None
    if a.control:
        z = np.load(a.control)
        bad = [k for p in (0, 1) for L in range(m.L) for k in (f"h_{p}_{L}", f"pre_{p}_{L}")
               if not np.array_equal(np.asarray(z[k]).view(np.uint32),
                                     np.asarray(arrs[k.replace(f"h_{p}_", f"u0_p{p}_h").replace(f"pre_{p}_", f"u0_p{p}_pre")]).view(np.uint32))]
        control = dict(npz=str(a.control), npz_sha256=hashlib.sha256(Path(a.control).read_bytes()).hexdigest(),
                       compared=2 * 2 * m.L, mismatches=bad[:10], nbad=len(bad), PASS=not bad)
        print("CONTROL", "PASS" if not bad else f"FAIL {len(bad)}", flush=True)
    np.savez_compressed(out / "mu4.npz", **arrs)
    summ = dict(schema="opentallas.hbm_next_1019.cmtp.golden_mu4.v1", model="DeepSeek-V4.1-Flash released checkpoint "
                "(hdc_golden_v41 chunk8 via rtl_v41_fullshape_layer_campaign.build_model)", users=users,
                step="position 1 of every user = the 4-user N = 4 step (users mode, CTL.USERS banks)",
                control=control, init_sha=init_sha, golden=LC.golden_pin(), npz_sha256=hashlib.sha256((out / "mu4.npz").read_bytes())
                .hexdigest(), fetch_ledger=str(Path(a.fetch) / "ledger.jsonl"), wall_s=round(time.time() - t0, 1))
    (out / "mu4.json").write_text(json.dumps(summ, indent=1) + "\n")
    return 0


def mtp_all5(a):
    """ds_mtp_kernels.golden (forced drafter, corrupt = gamma = 5: every draft = the AR continuation -> all 5
    accepted + bonus) over the fetch-on-demand checkpoint, with the layer-major (verify order) identity check"""
    import rtl_v41_fullshape_layer_campaign as LC
    from hgi_sim import ds_mtp_kernels as K
    FC = fetch_checkpoint_class()
    snap, fetch = Path(a.snap), Path(a.fetch)
    LC.Checkpoint = lambda *x, **y: FC(snap, fetch)          # the golden builds LC.Checkpoint()
    ns = argparse.Namespace(out=a.out, p0=a.p0, gamma=5, corrupt=5, layer_major=True)
    return K.golden(ns)


# ======================================================================================================================
# package an existing golden: verify against its committed digests, per-array manifest
# ======================================================================================================================
def package(a):
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sums = {}
    if a.sums:
        for ln in Path(a.sums).read_text().splitlines():
            if ln.strip():
                h, f = ln.split()
                sums[f] = h
    res = dict(schema="opentallas.hbm_next_1019.cmtp.golden_manifest.v1", src=str(src), files={}, arrays={})
    for f in sorted(src.iterdir()):
        if f.suffix not in (".json", ".npz"):
            continue
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        res["files"][f.name] = dict(sha256=h, bytes=f.stat().st_size, committed_sha256=sums.get(f.name),
                                    matches_committed=(sums.get(f.name) == h) if f.name in sums else None)
        if f.suffix == ".npz":
            z = np.load(f)
            for k in sorted(z.files):
                x = z[k]
                res["arrays"][f"{f.name}:{k}"] = dict(shape=list(x.shape), dtype=str(x.dtype), sha256=_digest(x))
    bad = [k for k, v in res["files"].items() if v["matches_committed"] is False]
    res["verdict"] = "FAIL: differs from committed digests " + ",".join(bad) if bad else "PASS"
    (out / "manifest.json").write_text(json.dumps(res, indent=1) + "\n")
    print(res["verdict"], len(res["arrays"]), "arrays")
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("package")
    p.add_argument("--src", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--sums")
    s = sub.add_parser("serve")
    s.add_argument("--remote", default="ot-epyc5")
    s.add_argument("--dir", required=True, help="fleet fetch dir (req/, done/)")
    s.add_argument("--snap", required=True, help="fleet sparse snapshot dir")
    s.add_argument("--poll", type=float, default=5.0)
    s.add_argument("--log")
    s.add_argument("--until")
    s.add_argument("--stop-remote")
    s2 = sub.add_parser("serve2")
    s2.add_argument("--remote", default="ot-epyc5")
    s2.add_argument("--dir", required=True, help="fleet fetch dir (req/, done/)")
    s2.add_argument("--snap", required=True, help="fleet sparse snapshot dir")
    s2.add_argument("--writers", type=int, default=4)
    s2.add_argument("--log")
    s2.add_argument("--stop-remote")
    for nm in ("mu4", "mtp_all5"):
        g = sub.add_parser(nm)
        g.add_argument("--snap", required=True)
        g.add_argument("--fetch", required=True)
        g.add_argument("--out", required=True)
        g.add_argument("--users", type=int, default=4)
        g.add_argument("--p0", type=int, default=0)
        g.add_argument("--control")
    a = ap.parse_args()
    return dict(package=package, serve=serve, serve2=serve2, mu4=mu4, mtp_all5=mtp_all5)[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
