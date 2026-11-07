#!/usr/bin/env python3
"""ot_autoclean_archive.py (AUTOCLEAN-1, OWNER 2026-11-06 23:1x: "the stage result ODBs can be archived on the agidock").

Runs on localhost from cron, because the AGIdock key lives only there and may not be copied.  It drains closed units:
  1. ask each host for eligible units (ot_autoclean.closed_units: a kit whose own sign-off reads SIGNED / LOCAL_PASS / NEEDS_PARENT,
     not protected, no .keep, no ARCHIVED.json, not live or cited, quiet >= 6 h, and with stage ODBs to remove)
  2. stream it through localhost to /archive/opentallas-signed-1106/<host>/<path> (tar | zstd on the host, unzstd | tar on agidock;
     nothing lands on localhost)
  3. verify on both ends: file count, bytes, sha256 of every signoff.json, PROVENANCE.json, 6_final.odb
  4. on the host: re-check, write the manifest, empty the stage ODBs (1_*..5_*, 6_1_fill; the DB the sign-off read stays),
     write ARCHIVED.json.  Sign-off, PROVENANCE, 6_final.*, logs, reports, LEC and views stay in place.
Any failure leaves the unit untouched.  At most MAX_UNITS per run and STREAMS at once.  Off switch: same as ot_autoclean.
    ot_autoclean_archive.py [--dry] [--host H ...] [--max-units N]
"""
import json
import os
import shlex
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ot_autoclean as ac

AGIDOCK = "ubuntu@155.103.253.53"
KEY = os.path.expanduser("~/.ssh/agidock_ot")
ROOT = "/archive/opentallas-signed-1106"
MAX_UNITS = 5
STREAMS = 2
LOG = os.path.expanduser("~/.local/state/ot-autoclean/archive.log")
MEASURE = ("import hashlib,json,os,stat,sys\nk=sys.argv[1]\nn=b=0\nsha={}\n"
           "for d,ds,fs in os.walk(k):\n"
           " ds[:]=[x for x in ds if not os.path.islink(os.path.join(d,x))]\n"
           " for f in fs:\n"
           "  p=os.path.join(d,f)\n  st=os.lstat(p)\n"
           "  if not stat.S_ISREG(st.st_mode): continue\n"
           "  n+=1;b+=st.st_size\n"
           "  if f in ('signoff.json','PROVENANCE.json','6_final.odb'):\n"
           "   h=hashlib.sha256()\n"
           "   with open(p,'rb') as fh:\n"
           "    for c in iter(lambda:fh.read(1<<22),b''): h.update(c)\n"
           "   sha[os.path.relpath(p,k)]=h.hexdigest()\n"
           "print(json.dumps([n,b,sha]))\n")


def agidock(cmd, **kw):
    return subprocess.run(["ssh", "-i", KEY, "-o", "ControlPath=none", "-o", "BatchMode=yes", AGIDOCK, cmd], **kw)


def measure_host(host, k):
    r = subprocess.run(ac.ssh(host) + ["python3 -I -c " + shlex.quote(MEASURE) + " " + shlex.quote(k)], capture_output=True, text=True, timeout=3600)
    if r.returncode:
        raise RuntimeError(f"host measure rc {r.returncode}")
    return json.loads(r.stdout)


def measure_archive(path):
    r = agidock("python3 -I -c " + shlex.quote(MEASURE) + " " + shlex.quote(path), capture_output=True, text=True, timeout=3600)
    if r.returncode:
        raise RuntimeError(f"archive measure rc {r.returncode}")
    return json.loads(r.stdout)


def stream(host, k):
    dst = f"{ROOT}/{host}"
    src = subprocess.Popen(ac.ssh(host) + ["cd / && tar -cf - " + shlex.quote(k.lstrip("/")) + " | zstd -3 -T4 -q"], stdout=subprocess.PIPE)
    snk = subprocess.Popen(["ssh", "-i", KEY, "-o", "ControlPath=none", "-o", "BatchMode=yes", AGIDOCK,
                            f"mkdir -p {shlex.quote(dst)} && unzstd -q | tar -C {shlex.quote(dst)} -xf -"], stdin=src.stdout)
    src.stdout.close()
    rs, ri = snk.wait(timeout=6 * 3600), src.wait(timeout=60)
    if rs or ri:
        raise RuntimeError(f"stream rc {ri}/{rs}")
    return f"{dst}{k}"


def one(host, u, base):
    k = u["path"]
    before = measure_host(host, k)
    arch = stream(host, k)
    after = measure_archive(arch)
    if before[:2] != after[:2] or before[2] != after[2]:
        return dict(path=k, error=f"verify mismatch {before[:2]} vs {after[:2]}")
    return ac.run_on_host(host, dict(base, path=k, archive=f"agidock:{arch}", measured=before), "stub_unit")


def log(msg):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%F %T')} {msg}\n")
    print(msg)


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if ac.off():
        print("ot_autoclean_archive: OFF")
        return 0
    def opt(name):
        return [a[i + 1] for i, x in enumerate(a) if x == name]
    now = time.time()
    coord = os.path.expanduser(ac.COORD)
    hosts = opt("--host") or list(ac.HOSTS)
    limit = int((opt("--max-units") or [MAX_UNITS])[0])
    try:
        protected = ac.read_required(coord)
        cited, tokens = ac.read_cites(coord, now)
    except Exception as ex:
        log(f"FAIL CLOSED, nothing archived: {ex!r}")
        return 0
    all_live = set()
    for h in hosts:
        try:
            all_live |= ac.remote_live(h)
        except Exception as ex:
            log(f"{h}: live scan failed, host skipped: {ex!r}")
            hosts = [x for x in hosts if x != h]
    base = dict(protected=protected, cited=cited, tokens=tokens, other_host_live=sorted(all_live), now=now)
    import concurrent.futures as cf
    for h in hosts:
        r = ac.run_on_host(h, base, "closed_units")
        log(f"{h} held={ {k: [v[0], round(v[1], 1)] for k, v in (r.get('held') or {}).items()} } units={len(r.get('units') or [])} control={r.get('control_hits')} fail_closed={r.get('fail_closed')}")
        if r.get("fail_closed") or not r.get("control_hits") or "--dry" in a:
            continue
        units = (r.get("units") or [])[:limit]
        with cf.ThreadPoolExecutor(STREAMS) as ex:
            futs = {ex.submit(one, h, u, base): u for u in units}
            for fu in cf.as_completed(futs):
                try:
                    log(f"{h} {json.dumps(fu.result())}")
                except Exception as e:
                    log(f"{h} {futs[fu]['path']} ERROR {e!r}, unit untouched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
