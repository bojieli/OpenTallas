"""host_drain.py -- ONE drain-aware host filter for every launch path (FLOW-OPS-0900 fix 4, FABLE-FLOW-0745 class c).

A host is DRAINING while its scratch free GB is under its admit cap: the per-die dies.<die>.gen_host_min_free_gb of autopilot/kit_wave.json
(intel1 and epyc9 at 250 GB on 11-21, the restore-to-250-GiB rule), max over the dies, plus an optional top-level host_drain {host: GB}.
Before this the cap lived in kit_wave.json only and only the wave gen/place lists read it: ot-run obeyed an explicit --hosts, auto-resign pinned
to the DB host, the wave's frozen spec host lists and restage kept capped hosts, and every filter fell back to the full list when all were capped.

Readers: ot-run (refuses a job pinned only to draining hosts; drops them from a host list; --status prints DRAINING), kit_wave (gen hosts, the
place re-check, queued-wait repick, private-spec --host), auto_resign (DB host draining -> the staged any-host form).
Rule kept from the review: a job whose --dir already holds data on that host still runs there (no rail removed; memory admission, disk floors,
delete guard and OOM protection are untouched)."""
import json, os, subprocess, time

HUB = os.environ.get("OT_HUB_NAME", "intel2")
KIT_WAVE_JSON = os.path.expanduser(os.environ.get("OT_KIT_WAVE_JSON", "~/coord/autopilot/kit_wave.json"))
CACHE = os.path.expanduser(os.environ.get("OT_DRAIN_CACHE", "~/.cache/ot-run/drain_caps.json"))
CACHE_S = int(os.environ.get("OT_DRAIN_CACHE_S", "60"))   # FLOW-OPS-1300 (FABLE-FLOW-1240 d): was 600 s, an undrain took up to 10 min to be seen off the hub
REMOTE_PY = ("import json,os;c=json.load(open(os.path.expanduser('~/coord/autopilot/kit_wave.json')));"
             "print(json.dumps({'dies':{k:{'gen_host_min_free_gb':(v or {}).get('gen_host_min_free_gb') or {}} for k,v in (c.get('dies') or {}).items()},'host_drain':c.get('host_drain') or {}}))")


def caps_from_cfg(cfg):
    """{host: cap GB} = max over dies of gen_host_min_free_gb, and top-level host_drain.  Pure."""
    out = {}
    srcs = [(d or {}).get("gen_host_min_free_gb") or {} for d in ((cfg or {}).get("dies") or {}).values()] + [(cfg or {}).get("host_drain") or {}]
    for m in srcs:
        for h, v in m.items():
            try:
                v = int(v)
            except (TypeError, ValueError):
                continue
            if v > 0:
                out[h] = max(out.get(h, 0), v)
    return out


def load_caps(now=None, fetch=None):
    """caps from the hub's kit_wave.json (read directly on the hub; elsewhere fetched by ssh and cached CACHE_S).  Unknown -> stale cache or {}."""
    now = time.time() if now is None else now
    if os.path.isfile(KIT_WAVE_JSON):
        try:
            return caps_from_cfg(json.load(open(KIT_WAVE_JSON)))
        except (OSError, ValueError):
            pass
    cached = {}
    try:
        c = json.load(open(CACHE))
        cached = c.get("caps") or {}
        if now - float(c.get("t", 0)) < CACHE_S:
            return cached
    except (OSError, ValueError):
        pass
    try:
        if fetch is None:
            r = subprocess.run(["ssh", "-o", "ControlPath=none", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes", HUB, "python3", "-I", "-c", repr(REMOTE_PY)],
                               capture_output=True, text=True, timeout=30)
            txt = r.stdout if r.returncode == 0 else ""
        else:
            txt = fetch()
        caps = caps_from_cfg(json.loads(txt)) if txt.strip() else None
    except (OSError, ValueError, subprocess.SubprocessError):
        caps = None
    if caps is None:
        return cached
    try:
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        tmp = CACHE + f".{os.getpid()}"
        json.dump({"t": now, "caps": caps}, open(tmp, "w"))
        os.replace(tmp, CACHE)
    except OSError:
        pass
    return caps


# FLOW-OPS-1300 / FABLE-FLOW-1900 (COORD URGENT 11-21: the 18:22-18:40 burst put 48 of 57 gens on drained hosts, epyc10 72 -> 35 GB under its floor; the
# drain was a hand-set 9999 cap that the gen pick never read).  The drain is COMPUTED for every host: a host whose scratch free GB is under
# floor + margin takes no new job dir.  floor = ot-run's scratch disk floor (OT_RUN_SCRATCH_DISK_FLOOR_GB[_HOSTS], default 50, never below 50),
# margin = OT_DRAIN_MARGIN_GB (default 40: room for the gens a burst starts before the next free-disk read).  A hand cap (gen_host_min_free_gb,
# host_drain) still raises it.  This module is THE admission function: ot-run, the wave gen-host pick and the wave hold all call draining() / admit().
HARD_FLOOR_GB = 50
DRAIN_MARGIN_GB = int(os.environ.get("OT_DRAIN_MARGIN_GB", "40"))


def floor_of(host):
    """ot-run's scratch disk floor for host (same env and the same 50 GB minimum as ot-run clamp_floor)"""
    per = {}
    for x in os.environ.get("OT_RUN_SCRATCH_DISK_FLOOR_GB_HOSTS", "").split(","):
        k, _, v = x.partition("=")
        try:
            per[k.strip()] = int(v)
        except ValueError:
            pass
    try:
        base = int(os.environ.get("OT_RUN_SCRATCH_DISK_FLOOR_GB", "50"))
    except ValueError:
        base = HARD_FLOOR_GB
    return max(HARD_FLOOR_GB, per.get(host, base))


def cap_of(caps, host, hub=HUB, computed=True):
    """the admit cap of host: max(hand cap, floor + margin).  computed=False = the hand cap only (old meaning)."""
    hand = int(caps.get(host) or (caps.get(hub) if host == "localhost" else 0) or 0)
    if not computed or os.environ.get("OT_DRAIN_COMPUTED", "1") == "0":
        return hand
    return max(hand, floor_of(host) + DRAIN_MARGIN_GB)


def admit(host, free_gb, need_gb=0, caps=None, hub=HUB):
    """-> (True, "") when host may take a new job dir needing need_gb, else (False, reason).  free_gb None = unknown = admitted."""
    if free_gb is None:
        return True, ""
    c = cap_of(caps if caps is not None else load_caps(), host, hub)
    if int(free_gb) - int(need_gb or 0) < c:
        return False, f"{host} DRAINING ({int(free_gb)} GB scratch free{', need %d' % need_gb if need_gb else ''}; cap {c} = max(hand cap, floor {floor_of(host)} + margin {DRAIN_MARGIN_GB}))"
    return True, ""


def draining(caps, free_gb, hub=HUB):
    """{host: (free, cap)} for hosts whose scratch free GB is under their cap.  free_gb {host: GB or None}; unknown free = not draining.  Pure."""
    out = {}
    for h, f in (free_gb or {}).items():
        c = cap_of(caps, h, hub)
        if c and f is not None and int(f) < c:   # FLOW-OPS-1300: c includes the computed floor + margin
            out[h] = (int(f), c)
    return out


def draining_from_status(caps, stt, hub=""):
    """same, from kit_wave.parse_otrun_status rows ({host: {scratch_gb}}; the hub is 'localhost' there)"""
    free = {}
    for h, v in (stt or {}).items():
        name = hub if (h == "localhost" and hub) else h
        free[name] = (v or {}).get("scratch_gb")
    return draining(caps, free, hub or HUB)


def describe(dr):
    return ", ".join(f"{h} DRAINING ({f} of {c} GB scratch free)" for h, (f, c) in sorted(dr.items()))


def filter_hosts(hosts, dr, keep=lambda h: False):
    """-> (kept, dropped): draining hosts are dropped unless keep(h) (the job's --dir already holds data there).  NO fall-back to the full list:
    an empty result means refuse / hold, never 'use the capped host anyway' (the bypass of the 11-21 filters)."""
    kept, dropped = [], []
    for h in hosts:
        (dropped if h in dr and not keep(h) else kept).append(h)
    return kept, dropped


def refusal(hosts, dr, alternatives):
    alt = [h for h in alternatives if h not in dr and h not in hosts]
    return (f"every requested host is draining: {describe({h: dr[h] for h in hosts if h in dr})}; a draining host takes no new job dir until its scratch is back over "
            f"its cap (dies.<die>.gen_host_min_free_gb in autopilot/kit_wave.json); a job whose --dir already holds data there still runs. Use --hosts "
            + (",".join(alt) if alt else "<another build host>"))
