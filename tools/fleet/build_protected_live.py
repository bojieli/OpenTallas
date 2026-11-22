#!/usr/bin/env python3
"""build_protected_live (FLEET-OPS-R, COORD FABLE-FLOW-0700 (1)): the delete guard's protected list from LIVE structured references only.
Sources: kit_wave.json dies (CURRENT keys: every key whose name does not mark history -- prev / retired / superseded / history / old / note), the tree-switch markers
(same key rule), PROTECTED-DBS files.  NOT handoff prose or COORD-REVIEW-QUEUE.md (97 % of the old list; a refusal post renewed its own protection).
Running jobs, waiter command lines and units are NOT in the list: ot_delete_guard.refuse() checks the live process table at delete time.
usage: build_protected_live.py COORD_DIR OUT [MARKER_DIR ...]"""
import glob, importlib.util, json, os, re, sys, time

HIST = re.compile(r"(^|_)(prev|previous|retired|superseded|history|old|note|notes|rollback_hist|source_qualification|qualification|smoke_detail)(_|$)", re.I)
RX = re.compile(r"/srv/opentallas-scratch[0-9]*/claude/[A-Za-z0-9._+/@=~-]+")


def paths_in(obj, out, canon):
    """add every scratch path in obj to out, skipping history keys"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if HIST.search(str(k)):
                continue
            paths_in(v, out, canon)
    elif isinstance(obj, list):
        for v in obj:
            paths_in(v, out, canon)
    elif isinstance(obj, str):
        for m in RX.finditer(obj):
            t = m.group().rstrip("/.-")
            if t.count("/") >= 5:
                out.add(canon(t))


def build(coord, markers=(), canon=os.path.normpath, scope=None):
    out = set()
    try:
        cfg = json.load(open(os.path.join(coord, "autopilot/kit_wave.json")))
    except (OSError, ValueError):
        raise SystemExit("kit_wave.json unreadable: refusing to build an empty list")
    paths_in(scope.dies(cfg) if scope is not None else (cfg.get("dies") or {}), out, canon)
    for d in markers:
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if f.startswith("tree_switch_") and f.endswith(".json"):
                try:
                    mk = json.load(open(os.path.join(d, f)))
                    if isinstance(mk, dict) and str(mk.get("status") or "").upper().startswith("SUPERSEDED"):
                        continue                       # a marker its owner / COORD marked SUPERSEDED no longer protects anything (kept for history)
                    if scope is None:
                        paths_in(mk, out, canon)
                    else:
                        scope.add(mk, out, record_time(os.path.join(d, f)), "marker")
                except (OSError, ValueError):
                    pass
    for f in ("PROTECTED-DBS.txt", "lanes/PROTECTED-DBS.txt"):
        try:
            for l in open(os.path.join(coord, f)):
                l = l.split("#")[0].strip()
                if l.startswith("/srv/"):
                    out.add(canon(l))
        except OSError:
            pass
    return out


def prose_paths(files, out, canon, now=None, max_age_h=24.0, skip=("COORD-REVIEW-QUEUE.md",)):
    """(d) scratch paths quoted in the given handoff files changed in the last max_age_h, never COORD-REVIEW-QUEUE (it renews its own protection)"""
    now = now or time.time()
    for f in files:
        if os.path.basename(f) in skip or os.path.basename(f).startswith(("COORD", "CODEX")):
            continue
        try:
            if now - os.stat(f).st_mtime > max_age_h * 3600:
                continue
            for m in RX.finditer(open(f, errors="replace").read()):
                t = m.group().rstrip("/.-")
                if t.count("/") >= 5:
                    out.add(canon(t))
        except OSError:
            pass


# FLOW-OPS-1300 item 13b (FLOW-CANARY retire pass 11-21 freed ~0 GB): a hub checkout rewrote the mtime of 457 / 488 lanes/handoff/*.json at 11-19 05:56, so 5-day-old
# receipts counted as "recent", and a delete-pass receipt (E9_DELETE_GUARD_REAL_PASS_1116.json, its allow list) protected the 60 trees it had cleared for deletion.
# The age is the date in the file name when it carries one (_1116, -1120, 20261120-...), else the mtime; delete / retire / cleanup receipts never protect.
NAME_DATE = re.compile(r"(?:^|[_.-])(?:20\d\d)?(1[0-2]|0[1-9])([0-3]\d)(?=[_.-]|$)")
RECEIPT_NAME = re.compile(r"delete|retire|reaper|cleanup|autoclean|reclaim|_freed", re.I)


def name_age_h(base, now):
    """hours since the newest MMDD / YYYYMMDD date token in a file name, None if it carries none"""
    import datetime
    t_now = datetime.datetime.fromtimestamp(now)
    best = None
    for m in NAME_DATE.finditer(os.path.splitext(base)[0]):
        mo, dd = int(m.group(1)), int(m.group(2))
        if not 1 <= dd <= 31:
            continue
        for y in (t_now.year, t_now.year - 1):
            try:
                d = datetime.datetime(y, mo, dd)
            except ValueError:
                break
            if d <= t_now + datetime.timedelta(days=1):
                a = (t_now - d).total_seconds() / 3600 - 24      # the whole named day counts as its date
                best = a if best is None else min(best, a)
                break
    return None if best is None else max(best, 0.0)


def event_paths(coord, out, canon, now=None, max_age_h=72.0, scope=None):
    """(b) bind / LATCHECK / G0 inputs of in-flight plan events: structured json that names them (tree checks, handoff json: plan events, candidates, receipts), recent only"""
    now = now or time.time()
    for pat in ("autopilot/tree_checks/*", "lanes/handoff/*.json", "autopilot/*candidate*.json", "autopilot/events/*.json"):
        for f in glob.glob(os.path.join(coord, pat)):
            try:
                base = os.path.basename(f)
                if now - os.stat(f).st_mtime > max_age_h * 3600 or "_atomic_apply_" in base or RECEIPT_NAME.search(base):
                    continue                        # a receipt of an apply / delete pass that already happened is history, not an input
                na = name_age_h(base, now)
                if na is not None and na > max_age_h:
                    continue                        # the named date wins over an mtime a checkout rewrote
                if scope is None:
                    paths_in(json.load(open(f)), out, canon)
                else:
                    scope.add(json.load(open(f)), out, record_time(f, now), "event")
            except (OSError, ValueError):
                pass


# CLEAN-AGGR-1121 (OWNER 11-21 19:1x "apply all the aggressive cleanup rules"; OWNER 11-12: keep only live jobs, live / queued refs, signed until archived, the
# protected lists).  FLEET-WATCH-R7 / FLOW-CANARY: the guard still refused most idle trees through RECORDS of superseded events: S81 D8D..D8J5 source candidates,
# old proposal tree_switch markers, KV-D25e3 fault-row lists of CANCELLED attempts.  A record (tree_switch marker, handoff / candidate / tree-check json) now protects
#   - a source tree only when it is a CURRENT tree (named by the kit_wave.json die config: src, rollback_tree, bound_trees, item_inputs ...) or the record was written
#     AFTER its die adopted the current tree (the candidate of the next event, applying now);
#   - a kit-wave attempt dir (.../kit-wave/.../items/<item>/attempt_N) only when a live / queued row lists it (live_attempt_paths);
#   - every other path as before.  kit_wave.json, PROTECTED-DBS, live command lines, posts and the provenance cache are not scoped.
# ENQUEUED rows sit in the route queue with a complete kit in their attempt dir (gen done): they read the attempt, not the source tree (COORD 11-21 FABLE-FLOW-1900:
# 62 ENQUEUED + 113 ROUTE-HELD rows on superseded events pinned old trees).  A route that reads outside its kit is the kit failure (OWNER 11-12).
TREE_READER_STATES = ("RUNNING", "LAUNCHING", "RETRY-INFRA", "WAITING")
TREE_OF = re.compile(r"^(/srv/opentallas-scratch[0-9]*/claude/(?:kw45/snap_[^/]+/[^/]+|kw45/[^/]+|[^/]+/src_[^/]+))(?:/|$)")
WAVE_ATTEMPT_OF = re.compile(r"^(/srv/opentallas-scratch[0-9]*/claude/.*/kit-wave/.*/items/[^/]+/attempt_\d+)(?:/|$)")
TREE_DIE = (("src_kv_", "qwen_kvsys"), ("src_qc_", "qwen_compute"), ("qwen_compute", "qwen_compute"), ("src_head_", "s81_head"), ("s81_head", "s81_head"),
            ("src_s81_", "s81"), ("src_hbm_", "hbm"))


def tree_root(p):
    m = TREE_OF.match(p)
    return m.group(1) if m else None


def tree_die(root):
    name = os.path.basename(root or "")
    for pre, die in TREE_DIE:
        if name.startswith(pre):
            return die
    return None


def record_time(f, now=None):
    """when a record was written: its mtime, capped by the end of the day named in its file name (a hub checkout rewrites mtimes)"""
    now = now or time.time()
    t = os.stat(f).st_mtime
    na = name_age_h(os.path.basename(f), now)
    if na:
        t = min(t, now - na * 3600)
    return t


class RecordScope:
    """keep(path, written) -> does a record written at `written` still protect `path` (see CLEAN-AGGR-1121 above)"""

    def __init__(self, coord, cfg, canon, live_attempts):
        self.canon = canon
        self.adopted = {}
        for die in ((cfg or {}).get("dies") or {}):
            try:
                self.adopted[die] = os.stat(os.path.join(coord, "lanes/handoff/tree_switch_%s.json" % die)).st_mtime
            except OSError:
                pass
        self.live = set(live_attempts)
        self.dropped = {}
        # plan shas of rows that will still READ their bound source tree (unstarted / running); ROUTE-HELD / SIGNED rows read only their own attempt dir
        self.live_plans = set()
        try:
            st = json.load(open(os.path.join(coord, "autopilot/kit_wave_state.json")))
            for r in (st.get("items") or {}).values():
                if isinstance(r, dict) and str(r.get("status") or "") in TREE_READER_STATES and r.get("plan_sha"):
                    self.live_plans.add(str(r["plan_sha"]))
        except (OSError, ValueError, AttributeError):
            self.live_plans = None                   # unreadable state: every bound tree stays protected
        cur = set()
        paths_in(self.dies(cfg), cur, canon)
        self.dropped.pop("bound_tree", None)
        self.current = {r for r in (tree_root(p) for p in cur) if r}

    def bound_ok(self, bt):
        """a kit_wave bound_trees entry protects its tree only while an unstarted / running row is bound to its plan"""
        if self.live_plans is None or not isinstance(bt, dict):
            return True
        ps = str(bt.get("plan_sha256") or bt.get("plan_sha") or "")
        return not ps or any(ps.startswith(x) or x.startswith(ps) for x in self.live_plans)

    def dies(self, cfg):
        """kit_wave.json dies with the bound_trees entries no live row reads removed"""
        out = {}
        for name, d in ((cfg or {}).get("dies") or {}).items():
            if isinstance(d, dict) and isinstance(d.get("bound_trees"), list):
                keep = [bt for bt in d["bound_trees"] if self.bound_ok(bt)]
                self.dropped["bound_tree"] = self.dropped.get("bound_tree", 0) + len(d["bound_trees"]) - len(keep)
                d = dict(d, bound_trees=keep)
            out[name] = d
        return out

    def keep(self, p, written):
        r = tree_root(p)
        if r:
            if r in self.current:
                return True
            at = self.adopted.get(tree_die(r))
            return at is None or written is None or written > at + 60      # unknown die / no adoption marker: keep; else only the next event's candidate
        m = WAVE_ATTEMPT_OF.match(p)
        if m:
            return m.group(1) in self.live
        return True

    def add(self, obj, out, written, kind):
        s = set()
        paths_in(obj, s, self.canon)
        for p in s:
            if self.keep(p, written):
                out.add(p)
            else:
                self.dropped[kind] = self.dropped.get(kind, 0) + 1


HUB_ALIAS = "intel2"
OTRUN_HOSTS = re.compile(r"(?:^|\s)--hosts[ =]([A-Za-z0-9_,.-]+)")


def otrun_hosts(cmd):
    """CLEAN-AGGR-R3 (COORD 11-21: epyc7 copies of fable-fix-kv-hub/r5 kept because a hub ot-run of the same --dir ran on epyc8): the host set an ot-run
    command line places its job on (+ the hub, which spills / copies back), or None when the command is not an ot-run with an explicit --hosts list"""
    if "ot-run" not in cmd.split(" -- ", 1)[0]:
        return None
    m = OTRUN_HOSTS.search(cmd.split(" -- ", 1)[0])
    if not m:
        return None
    hs = {h.strip() for h in m.group(1).split(",") if h.strip()}
    hs = {HUB_ALIAS if h == "localhost" else h for h in hs}
    return sorted(hs | {HUB_ALIAS}) if hs else None


SSH_OPT_ARG = set("BbcDEeFIiJLlmOoPpQRSWw")
FLEET = re.compile(r"^(intel\d+|epyc\d+)$")


def ssh_host(argv):
    """the fleet host an `ssh [opts] HOST cmd` argv runs on (ot-run's remote job leg), else None"""
    if not argv or os.path.basename(argv[0]) != "ssh":
        return None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a.startswith("-") and len(a) > 1:
            i += 2 if (len(a) == 2 and a[1] in SSH_OPT_ARG) else 1
            continue
        h = a.split("@", 1)[-1]
        return h if FLEET.match(h) else None
    return None


def live_cmd_paths(out, canon, proc="/proc", unit_dirs=("~/.config/systemd/user",)):
    """(c) scratch paths named by running process command lines on this host (ot-run queue clients and waiters, jobs) and by user systemd unit files.
    A path from an ot-run command line with --hosts is written host-scoped ("@h1,h2 /srv/..."): the guard applies it only on those hosts and the hub."""
    for c in glob.glob(os.path.join(proc, "[0-9]*", "cmdline")):
        try:
            raw = open(c, "rb").read()
            t = raw.replace(b"\0", b" ").decode("latin1")
        except OSError:
            continue
        hs = otrun_hosts(t)
        sh = ssh_host(raw.decode("latin1").split("\0"))
        if hs is None and sh:
            hs = sorted({sh, HUB_ALIAS})
        for m in RX.finditer(t):
            x = m.group().rstrip("/.-")
            if x.count("/") >= 5:
                out.add(canon(x) if hs is None else "@%s %s" % (",".join(hs), canon(x)))
    for d in unit_dirs:
        for f in glob.glob(os.path.join(os.path.expanduser(d), "**", "*.service"), recursive=True) + glob.glob(os.path.join(os.path.expanduser(d), "*.timer")):
            try:
                for m in RX.finditer(open(f, errors="replace").read()):
                    x = m.group().rstrip("/.-")
                    if x.count("/") >= 5:
                        out.add(canon(x))
            except OSError:
                pass


LIVE_ROW_STATES = ("RUNNING", "LAUNCHING", "ENQUEUED", "RETRY-INFRA", "PASS", "ROUTE-HELD", "SIGNED", "DEDUP", "WAITING", "HELD")


def live_attempt_paths(coord, out, canon, state_file=None):
    """FLOW-OPS-1300 item 13: the guard no longer protects old attempt_N dirs through the die work_root, so the attempts a live or queued wave row may still read are listed
    exactly: items/<item> (its running dir) and attempt_<n>, attempt_<n-1> (resume checkpoint) of every row whose status is live / queued.  -> number added"""
    n = 0
    try:
        st = json.load(open(state_file or os.path.join(coord, "autopilot/kit_wave_state.json")))
    except (OSError, ValueError):
        return 0
    for r in (st.get("items") or {}).values():
        if not isinstance(r, dict) or str(r.get("status") or "") not in LIVE_ROW_STATES:
            continue
        w = str(r.get("work") or "")
        if not w.startswith("/srv/"):
            kit = str(r.get("kit") or "").split(":", 1)[-1]
            m = re.match(r"(.*/items/[^/]+)(?:/|$)", kit)
            w = m.group(1) if m else ""
        if not w.startswith("/srv/"):
            continue
        w = w.rstrip("/")
        w = re.sub(r"/attempt_\d+$", "", w)
        a = int(r.get("attempt") or 0)
        for p in [w] + [f"{w}/attempt_{k}" for k in (a, a - 1) if k > 0]:
            out.add(canon(p)); n += 1
    return n


PROV_CACHE = os.path.expanduser("~/.local/state/prov_paths.json")
POST_SKIP_LANES = ("FLEET-OPS-R", "DISK-RATE", "FLEET", "HUB-SYNC", "FLEET-OPS", "MERGE-QUEUE", "OT-TOOLS-SYNC", "KIT-WAVE")
TREE_TOKEN = re.compile(r"\b(src_[A-Za-z0-9_]+)")
POST_ITEM = re.compile(r"\(\d+\)")                                       # a ruling's numbered items "(1) ... (2) ..." are judged one by one
DELETE_APPROVED = re.compile(r"may be deleted|delete APPROVED", re.I)
DIE_PREFIX = (("src_kv_", "qwen_kvsys"), ("src_qc_", "qwen_compute"), ("src_head_", "s81_head"), ("src_s81_", "s81"), ("src_hbm_", "hbm"))
POST_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2}|\dx)\b[^\[]*\[([^\]\s>]+)")


def post_trees(queue_file, out, canon, now=None, max_age_h=24.0, root="/srv/opentallas-scratch2/claude/kw45"):
    """COORD 11-17: any source tree NAMED in a hub post of the last 24 h (not a fleet / retirement post: those would renew their own protection) is protected,
    whatever the key (QC M5T was published at 13:0x and posted; the retire path did not see a name that was only in the queue).  Posts carry 'YYYY-MM-DD HH:MM'."""
    import datetime
    now = now or time.time()
    try:
        lines = open(queue_file, errors="replace").read().splitlines()[-4000:]
    except OSError:
        return
    for ln in lines:
        m = POST_LINE.match(ln)
        if not m or m.group(4).upper() in POST_SKIP_LANES:
            continue
        try:
            t = datetime.datetime.strptime(m.group(1) + " " + m.group(2) + ":" + ("00" if "x" in m.group(3) else m.group(3)), "%Y-%m-%d %H:%M").timestamp()
        except ValueError:
            continue
        if now - t > max_age_h * 3600 or t > now + 7200:
            continue
        for clause in POST_ITEM.split(ln):
            if DELETE_APPROVED.search(clause):
                continue        # COORD 11-22: a ruling that approves deleting a tree must not protect it (stripbody _r2 was kept by its own RULING)
            for tok in TREE_TOKEN.findall(clause):
                out.add(canon(os.path.join(root, tok)))


def current_trees(coord, now=None):
    """-> {src_<prefix>_: {"tree": basename of the die's current source, "adopted_at": mtime of its tree_switch marker}} for the guard's newer-than-current rule"""
    res = {}
    try:
        cfg = json.load(open(os.path.join(coord, "autopilot/kit_wave.json")))
    except (OSError, ValueError):
        return res
    for prefix, die in DIE_PREFIX:
        d = (cfg.get("dies") or {}).get(die) or {}
        src = d.get("src")
        if not src:
            continue
        try:
            at = os.stat(os.path.join(coord, "lanes/handoff/tree_switch_%s.json" % die)).st_mtime
        except OSError:
            continue
        res[prefix] = {"tree": os.path.basename(src.rstrip("/")), "adopted_at": at}
        if os.path.basename(src.rstrip("/")).startswith(die + "_"):
            res[die + "_"] = dict(res[prefix])      # CLEAN-AGGR-1121: snap trees are named <die>_<rev>; src_qc_ / src_head_ never matched them
    return res


def prov_cache_paths(cache, out, canon, max_age_h=72.0, now=None):
    """provenance.json paths of every view in each die's CURRENT tree and rollback tree (prov_paths.py audit): never deleted.  A stale cache still protects (72 h);
    a missing cache protects nothing (the first audit run builds it)."""
    now = now or time.time()
    try:
        d = json.load(open(cache))
        if now - float(d.get("time") or os.path.getmtime(cache)) > max_age_h * 3600:
            return                                  # CLEAN-AGGR-1121: the 11-17 cache (4 days, trees no longer current) kept 706 old attempt / kit paths protected
        for p in d.get("paths") or {}:
            out.add(canon(p))
    except (OSError, ValueError, TypeError):
        pass


PLAN_RX = re.compile(r"(?:/srv/opentallas-scratch[0-9]*|/home/ubuntu)/[A-Za-z0-9._+/@=~,:%-]+")
PLAN_KEYS = ("plan", "gen_args", "type_args", "preflight_args")


def _strs(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from _strs(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strs(v)
    elif isinstance(o, str):
        yield o


def plan_ref_paths(cfg, out, canon, maxbytes=64 << 20, prefix="/srv/", coord=None, spec_age_h=48, depth=2, now=None):
    """CLEAN-AGGR-R3 (COORD 11-21/22 class bug: snap tree s81_head_r4_s0 retired while live HEAD r16/r17 plans named its sink_bins files; hd_ctl kit3 broke):
    every absolute /srv/ or /home/ubuntu/ path written inside a live plan json is protected.  Plan json = an enabled die's plan / gen_args / type_args /
    preflight_args, plus the json files of every private spec (spec.json) newer than spec_age_h; die_plan json files they name are followed `depth` levels
    (signoff* / result* files are records, not inputs).  -> number added"""
    seeds = []
    for die, d in ((cfg or {}).get("dies") or {}).items():
        if not isinstance(d, dict) or d.get("enabled") is False:
            continue
        for k in PLAN_KEYS:
            seeds += [x for x in _strs(d.get(k)) if x.endswith(".json")]
    if coord:
        now = time.time() if now is None else now
        for root in (os.path.join(coord, "autopilot/private_specs"), "/srv/opentallas-scratch2/claude/hub-coord/autopilot/private_specs"):
            for f in glob.glob(os.path.join(root, "**", "spec.json"), recursive=True):
                try:
                    if now - os.path.getmtime(f) <= spec_age_h * 3600:
                        seeds.append(f)
                except OSError:
                    pass
    rx = PLAN_RX if prefix == "/srv/" else re.compile(r"(?:%s|/srv/opentallas-scratch[0-9]*|/home/ubuntu)/[A-Za-z0-9._+/@=~,:%%-]+" % re.escape(prefix.rstrip("/")))
    n, seen = 0, set()
    todo = [(f, 0) for f in seeds if isinstance(f, str) and (f.startswith(prefix) or f.startswith("/home/"))]
    while todo:
        f, lvl = todo.pop()
        if f in seen:
            continue
        seen.add(f)
        try:
            if os.path.getsize(f) > maxbytes:
                continue
            txt = open(f, errors="replace").read()
        except OSError:
            continue
        for m in rx.finditer(txt):
            x = m.group().rstrip("/.-,:")
            if x.count("/") < 5:
                continue
            out.add(canon(x)); n += 1
            if lvl < depth and x.endswith(".json") and "die_plan" in x and not os.path.basename(x).startswith(("signoff", "result")):
                todo.append((x, lvl + 1))
    return n


def hub_lease_paths(out, canon, d=None):
    """CLEAN-AGGR-R3: live leases taken on the hub reach every host through the list (host-scoped when the lease names a --host)  -> number added"""
    try:
        here = os.path.dirname(os.path.realpath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import ot_lease
    except ImportError:
        return 0
    n = 0
    for r in ot_lease.leases(d):
        p = canon(r["path"])
        if ot_lease.CONTAINER.fullmatch(p):
            # CLEAN-AGGR-R3 11-22: a container lease (kw45, ot-jobs, ...) protects only the container itself (ot_lease.covering); as a list row it
            # protected every tree below it (intel2 at 150 GB: 220 GB of ruled-superseded kw45 trees refused).  A target that holds a protected row still refuses.
            continue
        out.add("@%s,%s %s" % (r["host"], HUB_ALIAS, p) if r.get("host") else p); n += 1
    return n


def main(argv):
    coord, outp, markers = argv[1], argv[2], argv[3:] or [os.path.join(argv[1], "lanes/handoff"), os.path.join(argv[1], "state")]
    here = os.path.dirname(os.path.realpath(__file__))
    sp = importlib.util.spec_from_file_location("ot_delete_guard", os.path.join(here, "ot_delete_guard.py"))
    g = importlib.util.module_from_spec(sp); sp.loader.exec_module(g)
    live = set()
    live_attempt_paths(coord, live, g.canon)
    try:
        cfg = json.load(open(os.path.join(coord, "autopilot/kit_wave.json")))
    except (OSError, ValueError):
        cfg = None
    scope = RecordScope(coord, cfg, g.canon, live) if cfg else None
    s = build(coord, markers, g.canon, scope)
    event_paths(coord, s, g.canon, scope=scope)
    # COORD 11-18: NO protection from handoff prose (a lane's handoff note kept a dead 17 GB kit protected, sd9h_gen); prose_paths() stays as a library function, main() does not call it.
    live_cmd_paths(s, g.canon)
    plan_ref_paths(cfg, s, g.canon, coord=coord)
    hub_lease_paths(s, g.canon)
    s |= live                                          # FLOW-OPS-1300 item 13: attempts of live / queued rows, listed exactly
    prov_cache_paths(os.environ.get("OT_PROV_PATHS_CACHE", PROV_CACHE), s, g.canon)
    post_trees(os.path.join(coord, "lanes/COORD-REVIEW-QUEUE.md"), s, g.canon)
    try:                                           # the guard's newer-than-current input, next to the list (refresh_guard_live.sh pushes both)
        with open(outp + ".current_trees.json", "w") as f:
            json.dump(current_trees(coord), f)
    except OSError:
        pass
    g.write_list(s, outp)
    print(len(s), "live protected roots ->", outp, "| record paths dropped (superseded tree / dead attempt):", scope.dropped if scope else {})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
