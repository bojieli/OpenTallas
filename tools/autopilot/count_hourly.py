#!/usr/bin/env python3
"""count_hourly.py -- refresh the release count and append lanes/SIGN-RATE.tsv each hour with no agent (FLOW-29, owner 11-04).

Why: in the limit 11-04 01:30-03:10 nothing rescanned, so SIGN-RATE has a gap from 00:36 to 03:30 and the first sign-off
back counted hours late.  Runs on the coord host, where the cache and the counter live, at :05, nice, by a timer
(systemd/count-hourly.timer).  COORD's own hourly refresh sits around :30 and the render timer at :40.

Each run: stop file -> nothing.  Cache younger than FRESH_S -> no scan (somebody just ran it), the row still goes in.
Otherwise release_tree_plan.py --force.  A scan that fails or leaves the cache unchanged appends no row and exits 1, so
systemctl and the journal show it; a gap in the file stays a true gap.  The row has the same shape as the hand rows, with
'auto' at the end; an hour already holding the same counts gets no new row.  Reads only; it credits nothing.
"""
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
COORD = Path(os.environ.get("COUNT_COORD", str(HOME / "coord")))
CACHE = Path(os.environ.get("COUNT_CACHE", str(HOME / ".local/state/fleet-viz/release_tree_plan_cache.json")))
COUNTER = os.environ.get("COUNT_TOOL", str(COORD / "tools" / "release_tree_plan.py"))
COMMIT = os.environ.get("COUNT_COMMIT", str(COORD / "bin" / "coord-commit.sh"))
STATE = Path(os.environ.get("COUNT_STATE", str(HOME / ".local/state/fleet-viz")))
RATE = "lanes/SIGN-RATE.tsv"
LEDGER = Path(os.environ.get("COUNT_LEDGER", str(HOME / ".local/state/ot-auto-export/ledger.json")))
FRESH_S = 30 * 60
SCAN_TIMEOUT_S = 25 * 60
DIES = (("s81", "s81"), ("s81_head", "head"), ("qwen_compute", "qc"), ("qwen_kvsys", "kv"), ("hbm", "hbm"))


VARIANT = re.compile(r"__(a\d+_\d{4}|legalrows_\d+)$")   # AUTO-EXPORT / re-sign name suffixes: the same type as the bare name, not a new unit
INDEX_DIES = {die for die, _ in DIES}


def load_element_alias(path=None):
    """(die, archived element) -> element from tools/autopilot/archive_element_alias.tsv (ARCHIVE-ALIAS-1124): an archived unit exported under a
    wrong element name maps to its real design; the append-only INDEX itself is never edited.  Missing / unreadable file -> {}."""
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".", "archive_element_alias.tsv")
    out = {}
    try:
        lines = open(p).read().splitlines()
    except OSError:
        return out
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) >= 3 and f[0] and f[1] and f[2]:
            out[(f[0], f[1])] = f[2]
    return out




def index_rows(index_json):
    """-> [(die, element, kind)] of the ARCHIVED rows of the AGIdock INDEX.tsv the counter mirrored in agidock_archive_index.json"""
    try:
        a = json.loads(Path(index_json).read_text())
    except (OSError, ValueError):
        return []
    rows = []
    for ln in (a.get("agidock_index_tsv") or "").splitlines()[1:]:
        f = ln.split("\t")
        if len(f) > 10 and f[0] in INDEX_DIES and f[10].startswith(("ARCHIVED", "RTX-FULL-AGI-META")):
            rows.append((f[0], f[1], f[2]))
    return rows


def index_units(index_json):
    """-> [dict(die, element, kind, odb_sha, src)] of the ARCHIVED / RTX-FULL rows of the mirrored AGIdock INDEX.tsv (same filter as index_rows)"""
    try:
        a = json.loads(Path(index_json).read_text())
    except (OSError, ValueError):
        return []
    out = []
    for ln in (a.get("agidock_index_tsv") or "").splitlines()[1:]:
        f = ln.split("\t")
        if len(f) > 10 and f[0] in INDEX_DIES and f[10].startswith(("ARCHIVED", "RTX-FULL-AGI-META")):
            out.append(dict(die=f[0], element=f[1], kind=f[2], odb_sha=f[7], src=f[11] if len(f) > 11 else ""))
    return out


def ledger_by_odb(path):
    """AUTO-EXPORT ledger (~/.local/state/ot-auto-export/ledger.json) -> {odb sha256: (scan host, signoff.json path, 6_final.v sha256)}"""
    try:
        units = json.loads(Path(path).read_text()).get("units") or {}
    except (OSError, ValueError, AttributeError):
        return {}
    out = {}
    for key, u in units.items():
        if not isinstance(u, dict) or u.get("state") != "done" or not u.get("odb_sha"):
            continue
        out[u["odb_sha"]] = (u.get("host") or key.partition(":")[0], u.get("signoff") or "", (u.get("shas") or {}).get("6_final.v") or "")
    return out


def stop_rows(coord):
    """COUNT-REVOKED rows (name, key) and COUNT-DO-NOT-COUNT HOLD dirs, read like release_tree_plan.revoked_rows / split_dnc"""
    rev, hold = [], []
    try:
        for ln in (Path(coord) / "lanes" / "COUNT-REVOKED.tsv").read_text().splitlines():
            f = [x.strip() for x in ln.split("\t")]
            if ln.strip() and not ln.startswith("#") and len(f) >= 3 and f[1] and f[2]:
                rev.append((f[1], f[2]))
    except OSError:
        pass
    try:
        for ln in (Path(coord) / "lanes" / "COUNT-DO-NOT-COUNT.tsv").read_text().splitlines():
            f = ln.split("\t")
            if not ln.startswith("#") and len(f) >= 2 and f[1].strip() == "HOLD":
                hold.append(f[0].strip())
    except OSError:
        pass
    return rev, hold


DIGEST_NAME = re.compile(r"__(?:cl|pv)[0-9a-f]{8,10}$")   # the type name carries its plan block digest, so the name IS the current block


def credit_archived(cache, units, ledger, rev, hold, alias=None):
    """COUNT-PRIVATE-1124 (flow review #3): a sign-off from a private kit or lane dir reaches the count only through the AGIdock INDEX
    (AUTO-EXPORT ledger), never through the wave scan, so even an EQUIVALENT one stayed 'deferred' until someone wrote a COUNT-CREDIT row
    (sle_st_b_v2 pv41c959f3, slw_fe_v1 cl08d14f0d).  An archived unit whose name (alias, VARIANT, module -> type) is a current-plan TYPE
    whose name carries its block digest, not yet signed there, and not stopped by COUNT-REVOKED (name + 6_final.v sha or host:dir) or a
    COUNT-DO-NOT-COUNT HOLD dir, is credited as a signed type of that plan, once per type.  A unit with no ledger entry is credited only
    when no COUNT-REVOKED row names its type (its netlist is unknown).  -> (cache copy, [(die, type, src)])"""
    alias = load_element_alias() if alias is None else alias
    cache = json.loads(json.dumps(cache))
    owner = {}
    for e in (cache.get("plans") or {}).values():
        signed = set(e.get("signed_types") or {}) | set(e.get("signed_cores") or {}) | set(e.get("signed_designs") or {})
        for t, m in (e.get("plan_types") or {}).items():
            owner[(e.get("die"), t)] = (e, signed)
            if m and m != t:
                owner.setdefault((e.get("die"), "\0mod\0" + m), (e, t))
    credited = []
    for u in units:
        die, el = u["die"], alias.get((u["die"], u["element"]), u["element"])
        base = VARIANT.sub("", el)
        for cand in (el, base):
            m = owner.get((die, "\0mod\0" + cand))
            if m:
                base = m[1]
                break
        else:
            base = el if (die, el) in owner else base
        hit = owner.get((die, base))
        if not hit or not DIGEST_NAME.search(base) or base in hit[1]:
            continue
        host, signoff, vsha = ledger.get(u.get("odb_sha") or "", ("", "", ""))
        names = {el, base, u["element"]}
        stop = False
        for name, key in rev:
            if name not in names:
                continue
            if not vsha:
                stop = True
            elif key.startswith("sha256:"):
                stop = stop or key[7:] == vsha
            else:
                h, _, d = key.partition(":")
                stop = stop or (h == host and signoff.startswith(d.rstrip("/") + "/"))
        for k in hold:
            h, _, d = k.partition(":")
            stop = stop or (bool(signoff) and h == host and signoff.startswith(d.rstrip("/") + "/"))
        if stop:
            continue
        e, signed = hit
        e.setdefault("signed_types", {})[base] = ["INDEX-CREDIT " + (u.get("src") or "")[:300]]
        signed.add(base)
        credited.append((die, base, u.get("src") or ""))
    return cache, credited


def any_plan_extra(cache, rows, by_die=False):
    """archived (AGIdock INDEX) units that the current plan's signed set does not hold, split (COORD r711 correction 11-18):
    deferred = name or VARIANT-stripped name is a type / type module / hard core of that die's current plan that is NOT signed there (the re-sign backlog);
    retired  = no current-plan name at all (old-plan units: QC sta_region_nb0_*, S81 ot_s81_svc_*, KV hub-C split children) that will never be re-signed.
    Units already signed on the current plan are in neither.  -> total int, or with by_die {"defer": {short: n}, "retired": {short: n}}"""
    plan_k, signed_k, mod_t = {}, {}, {}
    for e in (cache.get("plans") or {}).values():
        k = plan_k.setdefault(e.get("die"), set())
        sk = signed_k.setdefault(e.get("die"), set())
        for t, m in (e.get("plan_types") or {}).items():
            k.add(t); k.add(m)
            if m and m != t:
                mod_t[(e.get("die"), m)] = t
        for x in (e.get("hard_cores") or []):
            k.add(x)
        for x in list(e.get("signed_types") or {}) + list(e.get("signed_cores") or {}) + list(e.get("signed_designs") or {}):
            sk.add(x)
    dfr, ret = set(), set()
    alias = load_element_alias()
    for die, el, kind in rows:
        el = alias.get((die, el), el)
        base = VARIANT.sub("", el)
        # COUNT-PRIVATE-1124: a unit archived under its plan MODULE name (ot_s81hd_ctl, qfd_qc_slw_sc, s81p_slice_station__t36) is that
        # type, counted once: it used to count again as 'deferred' while the type was signed (18 units on the 11-24 hub data)
        el, base = mod_t.get((die, el), el), mod_t.get((die, base), base)
        sk, pk = signed_k.get(die, set()), plan_k.get(die, set())
        if el in sk or base in sk:
            continue
        (dfr if (el in pk or base in pk) else ret).add((die, base))
    if not by_die:
        return len(dfr) + len(ret)
    short = dict(DIES)
    out = {"defer": {}, "retired": {}}
    for key, st in (("defer", dfr), ("retired", ret)):
        for die, _ in st:
            n = short.get(die, die)
            out[key][n] = out[key].get(n, 0) + 1
    return out


def rate_row(cache, stamp, extra=0):
    """'YYYY-MM-DD HH:MM total s81=37 head=4+5t ... any=NNN auto'.  total = designs + directly signed types per die that MATCH THE CURRENT PLAN
    (the counter matches type names against the counted plan and keeps a renamed type whose plan block digest is unchanged, the same
    real-inputs test as WAVE-FLOW-R2 row_inputs_unchanged).  any=N adds the signed modules whose records exist but whose pins/outline no longer
    match a current plan design (design_unmatched): signed on some plan.  COORD r711 11-18: both numbers on every run and in every row."""
    by = extra if isinstance(extra, dict) else {}
    extra = sum(sum(v.values()) for v in by.values()) if isinstance(extra, dict) else extra
    total, any_extra, parts = 0, extra, []
    for die, short in DIES:
        d = t = 0
        for e in (cache.get("plans") or {}).values():
            if e.get("die") == die:
                d += len(e.get("signed_designs") or {})
                t += len(e.get("signed_types") or {})
        total += d + t
        parts.append("%s=%d%s" % (short, d, "+%dt" % t if t else ""))
    dfr = "".join(" %s=%s" % (key, ",".join("%s:%d" % (k, v) for k, v in sorted((by.get(src) or {}).items()) if v))
                  for key, src in (("defer", "defer"), ("retired", "retired")) if any((by.get(src) or {}).values()))
    return "%s %d %s any=%d%s auto" % (stamp, total, " ".join(parts), total + any_extra, dfr)


def headline(row):
    """COORD r711: 'signed any plan 450 | current plan 395 | deferred re-sign K (s81 n, ..) | retired-plan N (qc n, ..)' from a SIGN-RATE row.
    deferred re-sign = archived on an older block, name still in the current plan, not signed there; retired-plan = old-plan units never re-signed"""
    m = re.match(r"^\S+ \S+\s+(\d+)\s", row or "")
    a = re.search(r"\bany=(\d+)", row or "")
    if not m:
        return ""
    cur = int(m.group(1))
    anyn = int(a.group(1)) if a else cur

    def part(key):
        d = re.search(r"\b%s=(\S+)" % key, row or "")
        items = [x.split(":") for x in d.group(1).split(",")] if d else []
        n = sum(int(v) for _, v in items)
        return n, (" (%s)" % ", ".join("%s %s" % (k, v) for k, v in items) if items else "")
    kd, dt = part("defer")
    nr, rt = part("retired")
    return "signed any plan %d | current plan %d | deferred re-sign %d%s | retired-plan %d%s" % (anyn, cur, kd, dt, nr, rt)


def counts_of(row):
    return re.sub(r"\s+auto\s*$", "", row.split(" ", 2)[2]) if row.count(" ") >= 2 else ""


DROP_FRAC = 0.85


def last_total(text):
    for r in reversed((text or "").splitlines()):
        m = re.match(r"^\d{4}-\d\d-\d\d \d\d:\d\d\s+(\d+)\s+s81=", r)
        if m:
            return int(m.group(1))
    return 0


def same_hour_same_counts(text, row):
    hour = row[:13]
    return any(r.startswith(hour) and counts_of(r) == counts_of(row) for r in (text or "").splitlines())


def read_cache():
    return json.loads(CACHE.read_text())


def run(now=None, scan=None, commit=None, force=None):
    """-> process exit code"""
    now = now or time.time()
    if (STATE / "count_hourly.stop").exists():
        print("count_hourly: stop file, nothing done")
        return 0
    STATE.mkdir(parents=True, exist_ok=True)
    lock = open(STATE / "count_hourly.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("count_hourly: another run holds the lock")
        return 0
    before = None
    try:
        before = float(read_cache().get("generated") or 0)
    except (OSError, ValueError) as e:
        print("count_hourly: cache unreadable before the scan: %s" % e)
    if force is None:
        force = "--force" in sys.argv[1:]   # COUNT-DIAG-1118: --force used to be ignored, a cache under 30 min old was read as is
    if force or before is None or now - before >= FRESH_S:
        rc = (scan or _scan)()
        if rc:
            print("count_hourly: scan rc %s, no row" % rc, file=sys.stderr)
            return 1
    try:
        cache = read_cache()
    except (OSError, ValueError) as e:
        print("count_hourly: cache unreadable: %s, no row" % e, file=sys.stderr)
        return 1
    if now - float(cache.get("generated") or 0) >= FRESH_S:
        print("count_hourly: cache still %d min old after the scan, no row" % ((now - float(cache.get("generated") or 0)) / 60), file=sys.stderr)
        return 1
    idx = CACHE.with_name("agidock_archive_index.json")
    rev, hold = stop_rows(COORD)
    cache, credited = credit_archived(cache, index_units(idx), ledger_by_odb(LEDGER), rev, hold)
    for die, t, src in credited:
        print("count_hourly: INDEX-CREDIT %s/%s (%s)" % (die, t, src[:160]))
    row = rate_row(cache, time.strftime("%Y-%m-%d %H:%M", time.localtime(now)), any_plan_extra(cache, index_rows(idx), by_die=True))
    p = COORD / RATE
    last = last_total(p.read_text() if p.exists() else "")
    total = int(row.split(" ")[2])
    if last and total < DROP_FRAC * last:
        print("count_hourly: total %d is more than %d%% under the last row %d: a degraded scan, no row (cache generated %s)"
              % (total, round((1 - DROP_FRAC) * 100), last, time.strftime("%H:%M:%S", time.localtime(float(cache.get("generated") or 0)))), file=sys.stderr)
        print(row)
        return 1
    if same_hour_same_counts(p.read_text() if p.exists() else "", row):
        print("count_hourly: this hour already holds these counts: " + row)
        print("count_hourly: " + headline(row))             # WAVE-PILOT-FIX 11-19: the summary line also on a repeat run (it ended at the 'already holds' line, which read as a crash)
        return 0
    with open(p, "a") as f:
        f.write(row + "\n")
    print(row)
    print("count_hourly: " + headline(row))
    return (commit or _commit)()


def _scan():
    try:
        return subprocess.run([sys.executable, COUNTER, "--force"], cwd=str(COORD), timeout=SCAN_TIMEOUT_S,
                              stdout=subprocess.DEVNULL).returncode
    except subprocess.TimeoutExpired:
        return 124


def _commit():
    """a lost race on coord/state leaves the row in the tree; the next hour's commit carries it"""
    try:
        r = subprocess.run([COMMIT, "count hourly (auto)", RATE], timeout=280, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print("count_hourly: coord-commit timed out; the row is in the tree for the next commit", file=sys.stderr)
        return 1
    if r.returncode:
        print("count_hourly: coord-commit rc %d: %s" % (r.returncode, r.stderr[-300:]), file=sys.stderr)
    return r.returncode


if __name__ == "__main__":
    sys.exit(run())
