#!/usr/bin/env python3
"""ot-lifecycle (AUTOCLEAN-11, COORD 2026-11-08 18:4x, OWNER direction: job lifecycle rule).

HOST dry-run classifier + apply over a reviewed manifest.  Imports the landed ot-autoclean.py for its guards.
  plan:  python3 -I ot_lifecycle.py plan  --tool T --host H --lifesnap J --out DIR [--roots ...]
  apply: python3 -I ot_lifecycle.py apply --tool T --host H --lifesnap J --manifest M --out DIR --i-have-a-coord-reply REF

Categories (first holder wins):  KEEP-* never removed by this tool; DEL-* candidates.
  never list: counted/signed-stub, protected, live (proc/docker), <6 h, tok/kv-fn/tool trees, git-locked,
  git HEAD not on a remote-tracking ref, kit-wave keep/resume, named by a live lane in the last 24 h.
  holds with expiry: .keep, queue mention, local keep line, protect.d line: only while owner lane LIVE or renewed <48 h.
  self-fed protect.d/protected-dbs.txt is NOT a source (DISK-URGENT-2 union fix logic).
  DEL-L1-SIGNED-TRIM  signed unit, intermediates only (archive verified or pending, see reason)
  DEL-L2-ATTEMPT      kit-wave attempt finished and not the latest attempt
  DEL-L2-LATEST-TRIM  latest attempt kept as resume checkpoint: only 2_x/3_x/4_1/5_3/5_route/6_1 intermediates
  DEL-L4-KIT / DEL-L4-GIT / DEL-L4-LOOSE   dead-lane orphans (member level)
"""
import argparse
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import time

CAT_ORDER = []


def load_tool(path):
    spec = importlib.util.spec_from_file_location("otac", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------ lane ownership / liveness
TRANS = [(r"^dkv(\d+)", r"DIEKV\1"), (r"^dq(\d+)", r"DIEQC\1"), (r"^dh(\d+)", r"DIEHEAD\1"), (r"^qct(\d+)", r"QCTYPES\1"),
         (r"^rm(\d+)", r"ROOTMERGE\1"), (r"^ss(\d+)", r"SIGNOFFSPRINT\1"), (r"^kvt(\d+)", r"KVTYPES\1"), (r"^s81t(\d+)", r"S81TYPES\1")]
WRAPPERS = {"wt", "moved", "relocated-1106", "relocated-1106b"}
EXCL_PRE = ("tok-", "kv-fn-")
RENAMED = re.compile(r"[.](old|bak|orig|moved|aside)([-._]|$)")   # COORD 19:2x: holds are keyed by path, so a renamed tree is skipped whole


def norm(n):
    return re.sub(r"[^A-Z0-9]", "", n.upper())


def lane_norm(name):
    for pat, rep in TRANS:
        m = re.match(pat, name)
        if m:
            return re.sub(pat, rep, name, count=1).upper().replace("-", "")
    return norm(name)


def family_num(n):
    m = re.match(r"^(.*?)(\d+)$", n)
    return (m.group(1), int(m.group(2))) if m else (n, -1)


class Owners:
    def __init__(self, life):
        self.life = life
        self.live = {norm(x) for x in life["live"]}
        self.fam = {}
        for x in self.live:
            f, n = family_num(x)
            if n >= 0:
                self.fam[f] = max(self.fam.get(f, -1), n)

    def live_owner(self, tree):
        n = lane_norm(tree)
        if len(n) < 4:
            return None
        for L in self.live:
            if len(L) >= 6 and (n.startswith(L) or L.startswith(n)):
                return L
        f, k = family_num(n)
        if k >= 0 and self.fam.get(f, -2) - 1 == k:   # immediate predecessor of a live lane
            return f"{f}{k + 1}(successor)"
        return None


# ------------------------------------------------------------------ git
class Git:
    def __init__(self):
        self.cache = {}

    def g(self, wt, *args):
        return subprocess.run(["git", "--no-optional-locks", "-C", wt, *args], capture_output=True, text=True, timeout=600)

    def check(self, wt):
        if wt in self.cache:
            return self.cache[wt]
        self.cache[wt] = r = self._check(wt)
        return r

    def _check(self, wt):
        gf = os.path.join(wt, ".git")
        gd = gf
        if os.path.isfile(gf):
            try:
                gd = open(gf).read().split("gitdir:", 1)[1].strip()
            except (OSError, IndexError):
                return "git-unreadable"
            if os.path.exists(os.path.join(gd, "locked")):
                return "git-locked"
        else:
            wtd = os.path.join(gf, "worktrees")
            if os.path.isdir(wtd):
                for w in os.listdir(wtd):
                    try:
                        gp = open(os.path.join(wtd, w, "gitdir")).read().strip()
                    except OSError:
                        continue
                    if os.path.exists(gp):
                        rp = os.path.realpath(gp)
                        if not rp.startswith(os.path.realpath(wt) + "/"):
                            return f"git-outside-worktree {gp}"
        try:
            ls = self.g(wt, "rev-list", "-n1", "HEAD", "--not", "--remotes")
            if ls.returncode != 0:
                return "git-error " + ls.stderr.strip()[:60]
            if ls.stdout.strip():
                return "git-head-unpushed " + ls.stdout.strip()[:12]
            st = self.g(wt, "status", "--porcelain", "--untracked-files=no")
            if st.returncode != 0:
                return "git-error"
            if st.stdout.strip():
                return "git-dirty"
        except subprocess.TimeoutExpired:
            return "git-timeout"
        return None


# ------------------------------------------------------------------ classifier
class Plan:
    def __init__(self, a, m, J):
        self.a, self.m, self.J = a, m, J
        self.life = json.load(open(a.lifesnap))
        if time.time() - self.life["created"] > 6 * 3600:
            raise SystemExit("lifesnap older than 6 h")
        self.own = Owners(self.life)
        pf = self.life.get("protected_full")
        if not a.__dict__.get("allow_no_protected_full") and not pf:
            raise SystemExit("lifesnap has no protected_full rows")
        for h, path, why in (pf or []):
            J.protected.add(path, f"strict row {h}: {why}")
        self.now = time.time()
        self.rows = []         # path, cat, action, reason, bytes, exclusive bytes, files
        self.git = Git()
        self.links = self.scan_symlinks()
        self.qpaths = m.PathSet([(p, "queue 48h") for p in self.life["paths48"]], deep=J.deep, canon=J.paths.canon)
        self.qwords = set(self.life["words48"])
        self.keepdirs = {}
        self.inode_seen = {}      # inode -> [nlink, seen-in-delete-set]
        self.lane_live_cache = {}
        self.recent_cache = {}
        self.cited = self.cited_units()
        self.press = []           # (tier, newest mtime, path, why) pressure-stage candidates
        self.holds = self.load_holds()

    def cited_units(self):
        """attempt dirs and kit roots any signed record cites: the keep set comes from records, not from 'latest attempt'
        (DU4 18:46: 130 of 186 epyc4 attempts cited by counted rows are older attempts)."""
        out = set()
        for p in self.J.counted.m:
            m = self.m.ATTEMPT_RE.match(p)
            if m:
                out.add(m.group(0))
            for cut in ("/run/", "/results/", "/signoff/", "/signoff", "/gen/"):
                if cut in p:
                    q = p.split(cut, 1)[0]
                    if q.count("/") >= 5:
                        out.add(q)
        return out

    def load_holds(self):
        """.ot-hold files (COORD 18:5x): JSON {"expires": epoch, "lane": ..., "why": ..., "created": epoch}.  An expired or
        unparsable hold is ignored (unparsable counts as held for 48 h after its mtime, fail safe)."""
        out = {}
        for r in self.J.roots:
            try:
                p = subprocess.run(["nice", "-n", "15", "find", r, "-xdev", "-name", ".ot-hold", "-type", "f"], capture_output=True, text=True,
                                   timeout=3600, errors="replace")
            except subprocess.TimeoutExpired:
                raise SystemExit("hold scan timeout")
            if p.returncode not in (0, 1):
                raise SystemExit("hold scan failed")
            for f in p.stdout.splitlines():
                d = os.path.dirname(f)
                try:
                    with open(f) as fh:
                        h = json.load(fh)
                    exp = float(h["expires"])
                except (OSError, ValueError, KeyError, TypeError):
                    exp = os.path.getmtime(f) + 48 * 3600
                if exp > self.now:
                    out[d] = (f, exp)
        return self.m.PathSet([(d, f"ot-hold until {time.strftime('%F %H:%M', time.localtime(e))} {f}") for d, (f, e) in out.items()],
                              canon=self.J.paths.canon)

    def scan_symlinks(self):
        """(target real, link path) for symlinks under the roots whose target leaves the link's own subtree"""
        out = []
        for r in self.J.roots:
            try:
                p = subprocess.run(["nice", "-n", "15", "find", r, "-xdev", "-type", "l", "-printf", "%p\n"], capture_output=True,
                                   text=True, timeout=3600, errors="replace")
            except subprocess.TimeoutExpired:
                raise SystemExit("symlink scan timeout")
            for l in p.stdout.splitlines():
                t = os.path.realpath(l)
                if t != l and not l.startswith(t + "/"):
                    out.append((t, l))
        return out

    def build_refs(self, lanes):
        """paths named by text files of LIVE lane trees, excluded trees, ~/.local/state and home scripts"""
        J = self.J
        import tempfile
        tf = tempfile.NamedTemporaryFile("w", delete=False, dir=self.a.out, prefix="reflist.")
        n = 0
        for d in lanes:
            lane = self.lane_of(d + "/x")
            if self.excluded_tree(d) or self.owner_live(lane):
                tf.write(d + "\0")
                n += 1
        tf.write(os.path.expanduser("~/.local/state") + "\0")
        tf.close()
        names = ["*.sh", "*.mk", "*.tcl", "*.json", "*.f", "*.otrun", "*.env", "*.txt"]
        expr = " -o ".join(f"-name '{n}'" for n in names)
        alts = [r"/srv/opentallas-scratch[0-9]*", os.path.expanduser("~/scratch-root")]
        alts += [r[:-len("/claude")].replace(".", "[.]") for r in J.roots if r.endswith("/claude")]
        pat = "(" + "|".join(sorted(set(alts))) + r")/claude/[A-Za-z0-9_./+-]+"
        cmd = (f"xargs -0 -a {tf.name} -I{{}} find {{}} -xdev -type f \\( {expr} \\) -size -5M -print0 2>/dev/null "
               f"| nice -n 15 xargs -0 -r -P 32 -n 200 grep -aohE '{pat}' 2>/dev/null | sort -u")
        print("refs: scanning", n, "lane trees", flush=True)
        out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, errors="replace", timeout=2400)
        rows = [(p.rstrip("."), "referenced by live lane/tool file") for p in out.stdout.splitlines() if p.count("/") >= 4]
        print("refs: paths", len(rows), flush=True)
        # positive control (11-07 class: a retention filter that matches nothing fails silently)
        if n and not rows and not getattr(self.a, "allow_empty_refs", False):
            raise SystemExit("reference scan matched nothing over %d lane trees; refusing to plan" % n)
        os.unlink(tf.name)
        self.refset = self.m.PathSet(rows, deep=J.deep, canon=J.paths.canon)

    def load_refs(self):
        """optional reference file: 'target_path\treferrer_file' rows; keep only those whose referrer survives"""
        rows = []
        f = self.a.refs
        if f and os.path.exists(f):
            for ln in open(f, errors="replace"):
                p, _, ref = ln.rstrip("\n").partition("\t")
                if p.startswith("/"):
                    rows.append((p, ref))
        return rows

    # --- tree ownership
    def lane_of(self, p):
        rest = p.split("/claude/", 1)[1].split("/")
        lane = rest[0]
        if lane in WRAPPERS or lane.startswith(("moved-", "from-", "relocated")):
            if len(rest) > 1:
                lane = rest[1]
        return lane

    def owner_live(self, lane):
        if lane not in self.lane_live_cache:
            self.lane_live_cache[lane] = self.own.live_owner(lane)
        return self.lane_live_cache[lane]

    def excluded_tree(self, p):
        rest = p.split("/claude/", 1)[1].split("/")
        for c in rest:
            if c.startswith(EXCL_PRE) or c.startswith("from-") or "tool" in c or RENAMED.search(c):
                return True
        return False

    # --- holds with expiry
    def hold(self, d, lane_is_live):
        """returns (cat, reason, partial) or None.  partial: a member below d is held (descend)."""
        J = self.J
        # counted/protected/kit-wave keep (never removed).  A 'holds X' hit means a member below d: descend.
        for name, ps in (("counted", J.counted), ("protected", J.protected), ("kitwave-keep", J.kwkeep)):
            for f in J.paths.forms(d):
                h = ps.hit(f)
                if h:
                    return ("KEEP-" + name, h, h.startswith("holds "))
        oh = self.holds.hit(d)
        if oh:
            return ("KEEP-ot-hold", oh, oh.startswith("holds "))
        # local keep lines (protect.d except self-fed protected-dbs.txt, ot-run spill, alternates) with expiry by file mtime
        h = self.localkeep_hit(d)
        if h:
            return h
        # live process / docker
        w = J.live.why(J.paths.forms(d))
        if w:
            return ("KEEP-live", w, False)
        rh = self.refset.hit(d)
        if rh:
            return ("KEEP-referenced", rh, rh.startswith("holds "))
        # queue mention < 48 h (any lane; includes rows named by live lanes)
        qh = self.qpaths.hit(d)
        if qh:
            return ("KEEP-queue48", qh, qh.startswith("holds "))
        return None

    def localkeep_hit(self, d):
        J = self.J
        h = J.localkeep.hit(d)
        if not h:
            return None
        m = re.search(r"\(([^)]*)\)$", h)
        src = m.group(1) if m else ""
        partial = h.startswith("holds ")
        if "protected-dbs.txt" in src:          # self-fed union: released (DISK-URGENT-2 fix logic)
            return None
        if "protect.d/" in src:
            fn = os.path.expanduser("~/.local/state/wt-reaper/protect.d/" + src.rsplit("protect.d/", 1)[1])
            try:
                age = self.now - os.path.getmtime(fn)
            except OSError:
                age = 1e9
            if age >= 48 * 3600 and "kit_wave.txt" not in src:
                return None                     # dead-owner line older than 48 h: released (rule 3)
            if "kit_wave.txt" in src:
                return ("KEEP-kw-protect", h, partial)
            return ("KEEP-protectd-48h", h, partial)
        return ("KEEP-localkeep", h, partial)

    def queue_word_hit(self, p):
        rest = p.split("/claude/", 1)[1].split("/")
        for i, n in enumerate(rest):
            if i >= 2 and rest[i - 2] == "kit-wave":
                continue
            if not self.m.generic_name(n) and n in self.qwords:
                return n
        return None

    def dotkeep_hit(self, p, lane_live):
        """.keep at or above p, or below p.  Expired unless owner lane live or .keep younger than 48 h"""
        J = self.J
        found = []
        for a in [p] + self.m.ancestors(p):
            if a.count("/") < 3:
                break
            k = os.path.join(a, ".keep")
            if os.path.exists(k):
                found.append((k, False))
        if p in self.keep_below:
            found += [(k, True) for k in self.keep_below[p]]
        best = None
        for k, below in found:
            if self.git_tracked_placeholder(k):
                continue
            try:
                age = self.now - os.lstat(k).st_mtime
            except OSError:
                continue
            if lane_live or age < 48 * 3600:
                return ("KEEP-dotkeep", f"{k} age {age / 3600:.0f}h lane_live={bool(lane_live)}", below)
            best = k
        return None

    def git_tracked_placeholder(self, k):
        return "/dsrom_recovery_" in k or "/levers/.keep" in k

    def walk_stats(self, d, track=False):
        """recursive stats: bytes, exclusive-eligible bytes, files, newest mtime, has_hardlink, gitdirs, first young file"""
        total = files = 0
        newest = 0.0
        young = None
        notmine = None
        me = os.getuid()
        stack = [d]
        while stack:
            x = stack.pop()
            try:
                it = list(os.scandir(x))
            except OSError:
                continue
            for e in it:
                try:
                    st = e.stat(follow_symlinks=False)
                except OSError:
                    continue
                if e.is_symlink():
                    continue
                if st.st_uid != me and notmine is None:
                    notmine = e.path
                if stat.S_ISDIR(st.st_mode):
                    if not st.st_mode & 0o200 and notmine is None:      # shared src trees are chmod a-w (08:12 rule); rm -rf would stop half way
                        notmine = e.path + " (read-only dir)"
                    stack.append(e.path)
                    continue
                if st.st_mtime > newest:
                    newest = st.st_mtime
                b = st.st_blocks * 512
                if st.st_nlink > 1:
                    if track:
                        key = (st.st_dev, st.st_ino)
                        v = self.inode_seen.setdefault(key, [st.st_nlink, 0, b])
                        v[1] += 1
                else:
                    total += b
                files += 1
                if self.now - st.st_mtime < 6 * 3600:
                    young = e.path
        return dict(bytes=total, files=files, newest=newest, young=young, notmine=notmine)

    # --- units
    def is_git(self, d):
        return os.path.lexists(os.path.join(d, ".git"))

    def kit_like(self, d):
        return os.path.isdir(os.path.join(d, "run/results")) or (os.path.isdir(os.path.join(d, "results")) and os.path.isdir(os.path.join(d, "logs")))

    def attempt_verdict(self, d):
        """kit-wave attempt dir: 'latest-open', 'finished-old', 'unknown', 'signed', 'active'"""
        J = self.J
        c = J.paths.canon(d)
        mm = self.m.ATTEMPT_RE.match(c)
        if not mm or mm.group(0) != c:
            return None
        st = J.kw_attempts.get(c)
        if st and st["signed"]:
            return "signed"
        if st and st["active"]:
            return "active"
        item, n = mm.group(1), int(mm.group(2))
        xm = self.m.XPATH_RE.search(c)
        cur = J.kw_current_di.get(f"{xm.group(1)}|{xm.group(2)}", -1) if xm else -1
        latest = max(J.kw_latest.get(item, -1), cur)
        if latest < 0:
            return "unknown"
        return "latest-open" if n >= latest else "finished-old"

    def record(self, path, cat, action, reason, st):
        self.rows.append((path, cat, action, " ".join(str(reason).split())[:300], st["bytes"], st["files"]))

    # --- traversal
    def visit_lane(self, lane_dir):
        J = self.J
        lane = self.lane_of(lane_dir + "/x")
        if self.excluded_tree(lane_dir):
            self.record(lane_dir, "KEEP-excluded", "KEEP", "tok/kv-fn/tool or renamed tree", self.walk_stats(lane_dir))
            return
        live = self.owner_live(lane)
        self.visit(lane_dir, lane, live, top=True)

    def visit(self, d, lane, live, top=False):
        """decide d; recursion only into dirs that hold a protected/kept member, or into non-unit dirs"""
        J = self.J
        if os.path.islink(d):
            self.record(d, "KEEP-symlink", "KEEP", "symlink not followed", dict(bytes=0, files=1))
            return
        h = self.hold(d, bool(live))
        if h and not h[2]:
            st = self.walk_stats(d)
            self.record(d, h[0], "KEEP", h[1], st)
            if h[0] == "KEEP-kw-protect" and self.attempt_verdict(d) == "finished-old" and st["newest"] and self.now - st["newest"] > 24 * 3600:
                self.press.append((2, st["newest"], d, "superseded attempt behind a whole-wave kit_wave.txt root line"))
            return
        dk = self.dotkeep_hit(d, bool(live))
        if dk and not dk[2]:
            self.record(d, dk[0], "KEEP", dk[1], self.walk_stats(d))
            return
        partial = bool(h and h[2]) or bool(dk and dk[2])
        partial = partial or self.link_into(d)
        # unit policy
        if self.J.paths.canon(d) in self.cited:
            self.record(d, "KEEP-cited-unit", "KEEP", "cited by a counted/signed record (whole unit stays until the stub is proven)", self.walk_stats(d))
            return
        v = self.attempt_verdict(d)
        # a live reference or queue path into a unit keeps the whole unit: readers open siblings of the named path
        if h and h[2] and h[0] in ("KEEP-referenced", "KEEP-queue48") and d.count("/") >= 5 and (v or self.is_git(d) or self.kit_like(d)):
            self.record(d, h[0], "KEEP", h[1] + " (whole unit)", self.walk_stats(d))
            return
        if v in ("signed", "active"):
            self.record(d, "KEEP-kitwave-" + v, "KEEP", v, self.walk_stats(d))
            return
        if v == "finished-old":
            self.unit_delete(d, lane, live, "DEL-L2-ATTEMPT", "finished, not latest attempt", partial)
            return
        if v in ("latest-open", "unknown"):
            if v == "unknown" and not live:
                self.unit_delete(d, lane, live, "DEL-L4-ATTEMPT-UNKNOWN", "attempt unknown to kit-wave state, dead lane", partial)
                return
            self.trim_latest(d, lane, live, partial)
            return
        # git tree
        if self.is_git(d) and d.count("/") >= 4:
            if live or self.recent(d):
                self.record(d, "KEEP-git-livelane", "KEEP", f"owner {live or 'recent'}", self.walk_stats(d))
                return
            g = self.git.check(d)
            if g:
                self.record(d, "KEEP-" + g.split(" ")[0], "KEEP", g, self.walk_stats(d))
                return
            self.unit_delete(d, lane, live, "DEL-L4-GIT", "clean git tree, HEAD on remote, dead lane", partial)
            return
        # kit (private ORFS run)
        if self.kit_like(d) and d.count("/") >= 5:
            signed = self.signed_inside(d)
            if signed:
                self.signed_trim(d, lane, live, signed, partial)
                return
            if not live and not self.recent(d):
                self.unit_delete(d, lane, live, "DEL-L4-KIT", "finished private kit, dead lane", partial)
                return
            st = self.walk_stats(d)
            self.record(d, "KEEP-kit-livelane", "KEEP", f"owner {live or 'recent'}", st)
            if st["newest"] and self.now - st["newest"] > 72 * 3600:
                self.press.append((1, st["newest"], d, "live-lane kit idle > 72 h: intermediates only"))
            return
        if top and live:
            self.record(d, "KEEP-livelane-tree", "KEEP", f"owner {live}", self.walk_stats(d))
            return
        # descend
        try:
            ents = list(os.scandir(d))
        except OSError as e:
            self.record(d, "KEEP-unreadable", "KEEP", str(e)[:100], dict(bytes=0, files=0))
            return
        # plain dead-lane directory without guards: one row at dir level
        if not partial and not live and not top and not self.subtree_has_units(d):
            self.unit_delete(d, lane, live, "DEL-L4-LOOSE", "dead-lane orphan dir", False)
            return
        for e in ents:
            p = e.path
            if e.is_symlink():
                continue
            if e.is_dir(follow_symlinks=False):
                self.visit(p, lane, live)
            elif e.is_file(follow_symlinks=False):
                self.file_row(p, lane, live, top)

    def link_into(self, d):
        for l in self.link_tgt.get(d, []):
            if not (l == d or l.startswith(d + "/")):
                return True
        return False

    def recent(self, d):
        if d not in self.recent_cache:
            st = self.walk_stats(d)
            self.recent_cache[d] = (self.now - st["newest"] < 24 * 3600) if st["newest"] else False
        return self.recent_cache[d]

    def subtree_has_units(self, d):
        """true if d contains any attempt, git, kit_like, keep, signed record, or held member below (forces descend)"""
        return d in self.unit_anc

    def file_row(self, p, lane, live, top):
        J = self.J
        try:
            st = os.lstat(p)
        except OSError:
            return
        info = dict(bytes=st.st_blocks * 512 if st.st_nlink == 1 else 0, files=1)
        name = os.path.basename(p)
        if name in ("signoff.json", "PROVENANCE.json", "ARCHIVED.json", ".keep", "6_final.odb") or name.endswith(".signoff.json"):
            self.record(p, "KEEP-name", "KEEP", name, info)
            return
        h = self.hold(p, bool(live))
        if h:
            self.record(p, h[0], "KEEP", h[1], info)
            return
        if live or top and self.recent_parent(p):
            self.record(p, "KEEP-livelane-file", "KEEP", "live lane or recent dir", info)
            return
        if self.now - st.st_mtime < 6 * 3600:
            self.record(p, "KEEP-lt6h", "KEEP", "young", info)
            return
        if self.queue_word_hit(p):
            self.record(p, "KEEP-queue48-word", "KEEP", self.queue_word_hit(p), info)
            return
        self.record(p, "DEL-L4-FILE", "DELETE", "dead-lane loose file", info)

    def recent_parent(self, p):
        return self.recent(os.path.dirname(p))

    def signed_inside(self, d):
        return self.signed_below.get(self.J.paths.canon(d), [])

    # --- actions on units
    def unit_delete(self, d, lane, live, cat, why, partial):
        J = self.J
        qw = self.queue_word_hit(d)
        st = self.walk_stats(d, track=True)
        if qw:
            self.record(d, "KEEP-queue48-word", "KEEP", qw, st)
            return
        if st["young"]:
            self.record(d, "KEEP-lt6h", "KEEP", st["young"], st)
            return
        if partial or self.signed_inside(d):
            # member-level: descend, files individually
            self.descend_members(d, lane, live, cat, why)
            return
        if st["notmine"]:                        # COORD 19:2x: a folder that cannot be fully deleted is not started
            self.record(d, "KEEP-not-deletable", "KEEP", "not owned by this user: " + st["notmine"], st)
            return
        self.record(d, cat, "DELETE", why, st)

    def descend_members(self, d, lane, live, cat, why):
        try:
            ents = list(os.scandir(d))
        except OSError:
            return
        for e in ents:
            if e.is_symlink():
                continue
            p = e.path
            if e.is_dir(follow_symlinks=False):
                self.visit_member(p, lane, live, cat, why)
            elif e.is_file(follow_symlinks=False):
                self.file_member(p, cat, why)

    def visit_member(self, d, lane, live, cat, why):
        J = self.J
        h = self.hold(d, bool(live))
        if h and not h[2]:
            self.record(d, h[0], "KEEP", h[1], self.walk_stats(d))
            return
        dk = self.dotkeep_hit(d, bool(live))
        if dk and not dk[2]:
            self.record(d, dk[0], "KEEP", dk[1], self.walk_stats(d))
            return
        if self.J.paths.canon(d) in self.cited:
            self.record(d, "KEEP-cited-unit", "KEEP", "cited by a counted/signed record", self.walk_stats(d))
            return
        if self.signed_inside(d) and self.is_signed_unit_root(d):
            self.signed_trim(d, lane, live, self.signed_inside(d), bool(h and h[2]))
            return
        partial = bool(h and h[2]) or bool(dk and dk[2])
        partial = partial or self.link_into(d)
        if partial or self.signed_inside(d):
            self.descend_members(d, lane, live, cat, why)
            return
        st = self.walk_stats(d, track=True)
        if st["young"]:
            self.descend_members(d, lane, live, cat, why)
            return
        if st["notmine"]:
            self.record(d, "KEEP-not-deletable", "KEEP", "not owned by this user: " + st["notmine"], st)
            return
        self.record(d, cat, "DELETE", why + " (member)", st)

    def is_signed_unit_root(self, d):
        return os.path.isdir(os.path.join(d, "run", "results"))

    def file_member(self, p, cat, why):
        J = self.J
        try:
            st = os.lstat(p)
        except OSError:
            return
        info = dict(bytes=st.st_blocks * 512 if st.st_nlink == 1 else 0, files=1)
        n = os.path.basename(p)
        if n in ("signoff.json", "PROVENANCE.json", "ARCHIVED.json", ".keep", "6_final.odb", "config.mk") or n.endswith(".signoff.json"):
            self.record(p, "KEEP-name", "KEEP", n, info)
            return
        h = self.hold(p, False)                 # counted/protected/kit-wave, ot-hold, local keep, live, refs, queue
        if h:
            self.record(p, h[0], "KEEP", h[1], info)
            return
        dk = self.dotkeep_hit(p, False)
        if dk:
            self.record(p, dk[0], "KEEP", dk[1], info)
            return
        if self.now - st.st_mtime < 6 * 3600:
            self.record(p, "KEEP-lt6h", "KEEP", "young", info)
            return
        self.record(p, cat, "DELETE", why + " (member file)", info)

    def trim_latest(self, d, lane, live, partial):
        """latest attempt, open: only the intermediates class b/c names, per results dir; holds with expiry apply"""
        m, J = self.m, self.J
        names = set(m.TRIM_C) | set(m.TRIM_B) | {"4_1_cts.odb"}
        for dp, dn, fn in os.walk(d):
            dn[:] = [x for x in dn if not os.path.islink(os.path.join(dp, x))]
            for f in fn:
                if f not in names:
                    continue
                p = os.path.join(dp, f)
                if f in ("4_1_cts.odb",) and not os.path.isfile(os.path.join(dp, "4_cts.odb")):
                    continue
                if f in m.TRIM_B and not (os.path.isfile(os.path.join(dp, "6_final.odb")) and os.path.isfile(os.path.join(dp, "6_final.spef"))):
                    continue
                if f in m.TRIM_C and not os.path.isfile(os.path.join(dp, "3_place.odb")):
                    continue
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                info = dict(bytes=st.st_blocks * 512 if st.st_nlink == 1 else 0, files=1)
                if self.now - st.st_mtime < 6 * 3600:
                    self.record(p, "KEEP-lt6h", "KEEP", "young", info)
                    continue
                h = self.hold(p, bool(live)) or self.dotkeep_hit(p, bool(live))
                if h:
                    self.record(p, h[0], "KEEP", h[1], info)
                    continue
                r = J.resume_hold(dp)                # COORD 11-08 04:4x: a FAIL row < 24 h resumes from its last valid stage
                if r:
                    self.record(p, "KEEP-resume-pending", "KEEP", r, info)
                    continue
                self.record(p, "DEL-L2-LATEST-TRIM", "DELETE", "intermediate of latest attempt", info)

    def signed_trim(self, d, lane, live, signed, partial):
        """signed kit: delete only intermediates and run/objects after ARCHIVED.json check; stub stays"""
        m = self.m
        archived = self.archive_verified(d)
        arch_note = "archive verified" if archived else "archive PENDING"
        if not archived:
            self.record(d, "KEEP-signed-archive-pending", "KEEP", "no verified ARCHIVED.json yet (trim waits for the archive timer)",
                        self.walk_stats(d))
            return
        KEEP_NAMES = set(m.NEVER) | {"config.mk", "ARCHIVED.json", ".keep"}
        for dp, dn, fn in os.walk(d):
            dn[:] = [x for x in dn if not os.path.islink(os.path.join(dp, x))]
            rel = os.path.relpath(dp, d)
            parts = rel.split("/")
            in_results = "results" in parts
            for f in fn:
                p = os.path.join(dp, f)
                if f in KEEP_NAMES or f.endswith((".lef", ".lib", ".lib.gz", ".signoff.json")) or f.startswith("6_final"):
                    continue
                if f == "5_route.odb" and "6_final.odb" not in fn:      # signoff.py ROUTED_DBS: the routed DB of a GOAL=route kit
                    continue
                victim = False
                if in_results and re.match(r"(1_\d|2_\d|3_\d|4_\d|5_\d|6_1|route\.guide)", f) and not f.startswith(("2_floorplan", "3_place", "4_cts")):
                    victim = f.endswith(".odb") or f == "route.guide" or f == "5_2_route_rcx.spef"
                # COORD input 3: the stub keeps kit RTL, scripts, objects and logs; only stage ODBs are reclaimed
                if not victim:
                    continue
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                info = dict(bytes=st.st_blocks * 512 if st.st_nlink == 1 else 0, files=1)
                if self.now - st.st_mtime < 6 * 3600:
                    continue
                self.file_member_sg(p, "DEL-L1-SIGNED-TRIM", arch_note + (" unit " + d), info)

    def archive_verified(self, d):
        """ARCHIVED.json exists at the unit root, parses, names an archive path, and records a sha or file+byte verify"""
        try:
            with open(os.path.join(d, "ARCHIVED.json")) as fh:
                r = json.load(fh)
        except (OSError, ValueError):
            return False
        if not isinstance(r, dict) or not str(r.get("archive", "")).startswith("/archive/"):
            return False
        v = r.get("verify")
        if not v:
            return False
        if isinstance(v, dict):
            return "sha256" in str(v.get("match", ""))
        return "sha256" in str(v)

    def file_member_sg(self, p, cat, why, info):
        J = self.J
        for name, ps in (("counted", J.counted), ("protected", J.protected), ("kitwave-keep", J.kwkeep)):
            for f in J.paths.forms(p):
                h = ps.hit(f)
                if h:
                    self.record(p, "KEEP-" + name, "KEEP", h, info)
                    return
        self.record(p, "INFO-L1-SIGNED-TRIM-CANDIDATE", "KEEP", why + " (off until stub tested)", info)

    # --- positive control: known retained paths must classify KEEP in this same run
    def control(self):
        """>=1 existing signed record and >=1 existing PROTECTED path on this host must each be held; fail -> abort (no delete)"""
        J = self.J
        got = {"counted": 0, "protected": 0}
        for r in J.signed_records[:400]:
            if os.path.exists(r):
                h = self.hold(os.path.dirname(r), False)
                if not (h and h[0] in ("KEEP-counted", "KEEP-protected", "KEEP-kitwave-keep")):
                    return f"control: signed record dir {r} not held ({h})"
                got["counted"] += 1
                if got["counted"] >= 25:
                    break
        for path in list(J.protected.m)[:4000]:
            if os.path.exists(path):
                h = self.hold(path, False)
                if not (h and h[0].startswith("KEEP-")):
                    return f"control: protected path {path} not held ({h})"
                got["protected"] += 1
                if got["protected"] >= 25:
                    break
        if got["counted"] == 0 and got["protected"] == 0:
            return "control: no existing counted or protected path found on this host"
        print(f"controls: positive PASS (counted {got['counted']} protected {got['protected']})", flush=True)
        return None

    def verify_rows(self):
        """independent re-check of the final DELETE rows: realpath both sides, against protected+counted+kit-wave keep; any hit = abort"""
        J = self.J
        bad = []
        for path, cat, action, reason, b, n in self.rows:
            if action != "DELETE":
                continue
            ih = J.indep_hit(path, [])
            if ih:
                bad.append((path, ih))
            if os.path.isdir(path) and self.signed_inside(path):
                bad.append((path, "signed record inside"))
        return bad

    # --- main
    def lane_dirs(self):
        out = []
        for r in self.J.roots:
            try:
                for e in os.scandir(r):
                    if e.is_symlink():
                        continue
                    if e.is_dir(follow_symlinks=False):
                        name = e.name
                        if name in WRAPPERS or name.startswith(("moved-", "from-", "relocated")):
                            for s in os.scandir(e.path):
                                if s.is_dir(follow_symlinks=False) and not s.is_symlink():
                                    out.append(s.path)
                        else:
                            out.append(e.path)
            except OSError:
                pass
        return out

    def run(self):
        J = self.J
        self.keep_below = {}
        for k in J.found["keep"]:
            for a in self.m.ancestors(k):
                if a.count("/") < 4:
                    break
                self.keep_below.setdefault(a, []).append(k)
        self.unit_anc = set()
        for lst in (J.found["git"], J.found["record"], J.found["attempt"]):
            for r in lst:
                for a in self.m.ancestors(r):
                    if a.count("/") < 3:
                        break
                    self.unit_anc.add(a)
        self.signed_below = {}
        for r in J.signed_records:
            for a in self.m.ancestors(r):
                if a.count("/") < 3:
                    break
                self.signed_below.setdefault(a, []).append(r)
        self.link_tgt = {}
        for t, l in self.links:
            for a in [t] + self.m.ancestors(t):
                if a.count("/") < 3:
                    break
                self.link_tgt.setdefault(a, []).append(l)
        lanes = self.lane_dirs()
        os.makedirs(self.a.out, exist_ok=True)
        self.build_refs(lanes)
        msg = self.control()
        if msg:
            raise SystemExit("positive control FAILED: " + msg)
        t0 = time.time()
        for i, d in enumerate(sorted(lanes)):
            if os.path.basename(d) in ("kw-fix-8",):      # DISK-URGENT-4 scope
                self.record(d, "KEEP-DU4-scope", "KEEP", "kw-fix-8 owned by DISK-URGENT-4", self.walk_stats(d))
                continue
            self.visit_lane(d)
            if i % 25 == 0:
                print(f"{i}/{len(lanes)} lanes {time.time() - t0:.0f}s rows {len(self.rows)} {d}", flush=True)
        bad = self.verify_rows()
        if bad:
            for x in bad[:20]:
                print("VERIFY-FAIL", x, flush=True)
            raise SystemExit(f"verify_rows: {len(bad)} DELETE rows hit protected/counted/kit-wave keep; no manifest written")
        self.write()

    def write(self):
        mf = os.path.join(self.a.out, f"PLAN-{self.a.host}-{time.strftime('%Y%m%d-%H%M%S')}.tsv")
        cats = {}
        with open(mf, "w") as fh:
            fh.write("path\tcategory\taction\treason\tbytes\tfiles\n")
            for path, cat, action, reason, b, n in self.rows:
                fh.write(f"{path}\t{cat}\t{action}\t{reason}\t{b}\t{n}\n")
                c = cats.setdefault(cat, [0, 0, action])
                c[0] += b
                c[1] += 1
        # hard-linked inodes: count once toward KEEP share if any link kept (approximate: report separately)
        hl = sum(v[2] for v in self.inode_seen.values() if v[1] >= v[0])
        print("MANIFEST", mf)
        print(f"{'category':32s} {'GB':>10s} {'rows':>8s}  action")
        for cat, (b, n, act) in sorted(cats.items(), key=lambda kv: (kv[1][2], -kv[1][0])):
            print(f"{cat:32s} {b / 1e9:10.1f} {n:8d}  {act}")
        print(f"hard-linked inodes fully inside walked sets: {hl / 1e9:.1f} GB (counted once)")
        print("DELETE total GB:", round(sum(c[0] for c in cats.values() if c[2] == "DELETE") / 1e9, 1))



# ------------------------------------------------------------------ apply over a reviewed manifest
class Apply:
    """recheck every DELETE row right before rm, realpath both sides; ALERT on a counted/protected/kit-wave hit"""

    def __init__(self, a, m, J, plan=None):
        self.freed_by_cat = {}
        self.a, self.m, self.J = a, m, J
        if plan is not None:
            self.P = plan
            return
        self.P = Plan(a, m, J)
        self.P.keep_below = {}
        for k in J.found["keep"]:
            for x in m.ancestors(k):
                if x.count("/") < 4:
                    break
                self.P.keep_below.setdefault(x, []).append(k)
        self.a, self.m, self.J = a, m, J
        self.P.build_refs(self.P.lane_dirs())
        self.P.signed_below = {}
        for r in J.signed_records:
            for x in m.ancestors(r):
                if x.count("/") < 3:
                    break
                self.P.signed_below.setdefault(x, []).append(r)

    def rows(self):
        cats = set(self.a.cats.split(",")) if self.a.cats else None
        out = []
        with open(self.a.manifest) as fh:
            next(fh)
            for ln in fh:
                c = ln.rstrip("\n").split("\t")
                if len(c) < 6 or c[2] != "DELETE":
                    continue
                if cats and c[1] not in cats:
                    continue
                out.append(c)
        return out

    def recheck(self, path, cat):
        J, P = self.J, self.P
        real = os.path.realpath(path)
        if real != path:
            return "SKIP", f"not realpath ({real})"
        if not os.path.lexists(path):
            return "GONE", "gone"
        if P.excluded_tree(path):
            return "ALERT", "excluded tree"
        for name, ps in (("counted", J.counted), ("protected", J.protected), ("kitwave-keep", J.kwkeep)):
            for f in J.paths.forms(path):
                h = ps.hit(f)
                if h:
                    return "ALERT", f"{name}: {h}"
        ih = J.indep_hit(path, [])
        if ih:
            return "ALERT", ih
        if path in P.signed_below or (P.signed_inside(path) if os.path.isdir(path) else False):
            return "ALERT", "signed record inside"
        h = P.localkeep_hit(path)
        if h:
            return "SKIP", h[1]
        oh = P.holds.hit(path)
        if oh:
            return "SKIP", "ot-hold " + oh
        lane = P.lane_of(path + "/x" if os.path.isdir(path) else path)
        live_now = P.owner_live(lane)
        if live_now and cat.startswith("DEL-L4"):               # dead-lane classes only: a successor may have picked the tree up since the plan
            return "SKIP", f"lane live now: {live_now}"
        dk = P.dotkeep_hit(path, bool(live_now))
        if dk:
            return "SKIP", dk[1]
        if cat == "DEL-L4-GIT":
            g = self.git_now(path)
            if g:
                return "SKIP", g
        if cat == "DEL-L2-LATEST-TRIM":
            r = J.resume_hold(os.path.dirname(path))
            if r:
                return "SKIP", r
        w = J.live.why(J.paths.forms(path))
        if w:
            return "SKIP", w
        if P.qpaths.hit(path):
            return "SKIP", "queue path 48h"
        qw = P.queue_word_hit(path)
        if qw:
            return "SKIP", "queue word " + qw
        rh = P.refset.hit(path)
        if rh:
            return "SKIP", "referenced: " + rh
        if P.link_into(path):
            return "SKIP", "symlink into"
        return None, None

    def git_now(self, path):
        """git state of the tree holding path, as of apply time (member rows too).  Cached per tree: once a member row has removed .git
        the tree no longer resolves, and the check made before that first removal stands."""
        P = self.P
        for x in [path] + self.m.ancestors(path):
            if x.count("/") < 4:
                return None
            if x.endswith("/.git"):
                continue
            if P.is_git(x):
                return P.git.check(x)
        return None

    def watch_set(self):
        """counted and protected paths that exist now: the count check of this run (the release-tree cache can be 50 min stale)"""
        return {p for ps in (self.J.counted, self.J.protected) for p in ps.m if os.path.lexists(p)}

    def lost(self, watch, deleted):
        """watched paths gone AND at or under a path this run removed (a lane removing its own file is not this tool's loss)"""
        out = []
        for p in watch:
            if not os.path.lexists(p) and (p in deleted or any(x in deleted for x in self.m.ancestors(p))):
                out.append(p)
        return out

    def run(self):
        J, a = self.J, self.a
        rows = self.rows()
        P = self.P
        P.link_tgt = {}
        for t, l in P.links:
            for x in [t] + self.m.ancestors(t):
                if x.count("/") < 3:
                    break
                P.link_tgt.setdefault(x, []).append(l)
        os.makedirs(a.out, exist_ok=True)
        outp = os.path.join(a.out, f"APPLY-{a.host}-{time.strftime('%Y%m%d-%H%M%S')}.tsv")
        print("apply rows", len(rows), "cats", a.cats, "manifest", a.manifest, "log", outp, flush=True)
        watch = self.watch_set()
        if not watch:                       # a guard matching zero paths must refuse
            print("ALERT count check matches zero existing paths; refusing to delete", flush=True)
            return 3
        print("count check: watching", len(watch), "existing counted/protected paths", flush=True)
        deleted = set()
        freed = 0
        n_del = 0
        with open(outp, "w") as fh:
            fh.write("time\tpath\tcategory\tresult\tdetail\tbytes\n")
            for i, c in enumerate(rows):
                path, cat, b = c[0], c[1], int(c[4])
                if i % 40 == 0:
                    J.live.refresh()
                if i % 200 == 0 and deleted:
                    gone = self.lost(watch, deleted)
                    if gone:
                        fh.write(f"{time.strftime('%F %T')}\t{gone[0]}\tCOUNT-CHECK\tALERT\t{len(gone)} watched paths lost\t0\n")
                        fh.flush()
                        print("ALERT count check lost", len(gone), gone[:5], flush=True)
                        return 3
                v, why = self.recheck(path, cat)
                if v == "ALERT":
                    fh.write(f"{time.strftime('%F %T')}\t{path}\t{cat}\tALERT\t{why}\t{b}\n")
                    fh.flush()
                    print("ALERT", path, why, flush=True)
                    return 3
                if v:
                    fh.write(f"{time.strftime('%F %T')}\t{path}\t{cat}\t{v}\t{why}\t{b}\n")
                    continue
                try:
                    st = os.lstat(path)
                    if stat.S_ISDIR(st.st_mode):
                        p = subprocess.run(["find", path, "-xdev", "-type", "f", "-mmin", "-360", "-not", "-name", "index", "-print", "-quit"],
                                           capture_output=True, text=True, timeout=1800)
                        if p.stdout.strip():
                            fh.write(f"{time.strftime('%F %T')}\t{path}\t{cat}\tSKIP\tyoung {p.stdout.strip()}\t{b}\n")
                            continue
                        p = subprocess.run(["find", path, "-xdev", "(", "!", "-user", str(os.getuid()), "-o", "-type", "d", "!", "-writable", ")", "-print", "-quit"],
                                           capture_output=True, text=True, timeout=1800)
                        if p.returncode not in (0, 1) or p.stdout.strip():
                            fh.write(f"{time.strftime('%F %T')}\t{path}\t{cat}\tSKIP\tnot fully deletable {p.stdout.strip()[:150]}\t{b}\n")
                            continue
                        if a.dry:
                            res = "WOULD"
                        else:
                            r = subprocess.run(["rm", "-rf", "--one-file-system", "--", path], capture_output=True, text=True, timeout=7200)
                            res = "DELETED" if r.returncode == 0 and not os.path.exists(path) else "ERROR " + r.stderr.strip()[:150]
                    else:
                        if time.time() - st.st_mtime < 6 * 3600:
                            fh.write(f"{time.strftime('%F %T')}\t{path}\t{cat}\tSKIP\tyoung\t{b}\n")
                            continue
                        if a.dry:
                            res = "WOULD"
                        else:
                            os.unlink(path)
                            res = "DELETED"
                except OSError as e:
                    res = "ERROR " + str(e)[:150]
                if res.startswith("DELETED"):
                    deleted.add(path)
                if res.startswith(("DELETED", "WOULD")):
                    freed += b
                    n_del += 1
                    self.freed_by_cat[cat] = self.freed_by_cat.get(cat, 0) + b
                fh.write(f"{time.strftime('%F %T')}\t{path}\t{cat}\t{res}\t\t{b}\n")
                if i % 20 == 0:
                    fh.flush()
                    print(f"{i}/{len(rows)} freed {freed / 1e9:.1f} GB", flush=True)
            gone = self.lost(watch, deleted)
            if gone:
                fh.write(f"{time.strftime('%F %T')}\t{gone[0]}\tCOUNT-CHECK\tALERT\t{len(gone)} watched paths lost\t0\n")
                print("ALERT count check lost", len(gone), gone[:5], flush=True)
                return 3
            print("count check: PASS, watched paths lost 0 of", len(watch), flush=True)
        print("FINISHED rows", n_del, "bytes freed (non-hardlink)", round(freed / 1e9, 1), "GB; log", outp, flush=True)
        return 0


# ------------------------------------------------------------------ standing tick (no agent in the loop, COORD 18:5x)
STATE_DIR = os.path.expanduser("~/.local/state/ot-lifecycle")
OFF = (os.path.expanduser("~/.config/ot-lifecycle/OFF"), os.path.expanduser("~/.config/ot-autoclean-auto/OFF"),
       os.path.expanduser("~/.config/ot-autoclean/OFF"))
# GB free: below trigger the pressure tiers run; they stop at target.  Root floor 150 (owner); ot-run admits above it.
ROOT_TRIGGER, ROOT_TARGET = 200, 250
SCRATCH_TRIGGER, SCRATCH_TARGET = 150, 300


def df_free(path):
    v = os.statvfs(path)
    return v.f_bavail * v.f_frsize / 1e9


def fs_table(roots):
    """{dev: (root path, trigger, target)}"""
    rootdev = os.stat("/").st_dev
    out = {}
    for r in roots:
        try:
            dev = os.stat(r).st_dev
        except OSError:
            continue
        if dev == rootdev:
            out.setdefault(dev, (r, ROOT_TRIGGER, ROOT_TARGET))
        else:
            out.setdefault(dev, (r, SCRATCH_TRIGGER, SCRATCH_TARGET))
    return out


def tick_main(a):
    os.makedirs(STATE_DIR, exist_ok=True)
    def line(msg, alert=""):
        ln = f"{time.strftime('%F %T %Z')} ot-lifecycle {a.host} {msg}" + (f" alert={alert}" if alert else "")
        with open(os.path.join(STATE_DIR, "ticks.log"), "a") as fh:
            fh.write(ln + "\n")
        print(ln, flush=True)
    import fcntl
    lf = open(os.path.join(STATE_DIR, "lock"), "w")
    try:
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another tick holds the lock")
        return 0
    off = [f for f in OFF if os.path.exists(f)]
    if off:
        line("OFF switch; nothing done")
        return 0
    halt = os.path.join(STATE_DIR, "HALT")
    if os.path.exists(halt):
        line("HALT present (pushed by localhost on a count drop); nothing done", alert=open(halt, errors="replace").read()[:200].strip())
        return 3
    alert_f = os.path.join(STATE_DIR, "ALERT")
    if os.path.exists(alert_f):
        line("sticky ALERT; no deletes until a human removes it", alert=open(alert_f, errors="replace").read()[:200].strip())
        return 3
    stampf = os.path.join(STATE_DIR, "last-tick")
    if a.reason == "jobend":
        try:
            if time.time() - os.path.getmtime(stampf) < 600:
                print("job-end tick debounced")
                return 0
        except OSError:
            pass
    open(stampf, "w").close()
    def _fail(msg):
        line("NO DELETE this tick: " + msg, alert=msg)
        return 2
    try:
        life = a.lifesnap
        if not os.path.exists(life):
            return _fail("lifesnap missing")
        if time.time() - os.path.getmtime(life) > 6 * 3600:
            return _fail("lifesnap older than 6 h")
        m = load_tool(a.tool)
        J = setup_job(a, m)
        P = Plan(a, m, J)
        P.run()
    except SystemExit as e:
        return _fail(str(e))
    except Exception as e:
        return _fail("exception " + repr(e)[:200])
    mf = sorted(f for f in os.listdir(a.out) if f.startswith("PLAN-"))[-1]
    a.manifest = os.path.join(a.out, mf)
    a.cats = ""
    a.dry = not a.apply
    ap = Apply(a, m, J, plan=P)
    if not a.apply:
        a.dry = True
    rc = ap.run()
    if rc == 3:
        with open(alert_f, "w") as fh:
            fh.write("recheck hit a counted/protected/kit-wave path; see last APPLY log\n")
        return _fail("ALERT at recheck")
    # pressure stage: tiers only when a filesystem is under its trigger, oldest first, until back at its target
    freed_press = {}
    if a.apply and P.press:
        tbl = fs_table(J.roots)
        for dev, (root, trig, target) in tbl.items():
            free = df_free(root)
            if free >= trig:
                continue
            # tier 2 stays report-only: superseded attempts behind kit_wave.txt root lines belong to the landed class a pass (DISK-URGENT-4)
            todo = sorted([x for x in P.press if x[0] == 1 and os.path.exists(x[2]) and os.stat(x[2]).st_dev == dev], key=lambda x: (x[0], x[1]))
            for tier, newest, path, why in todo:
                if df_free(root) >= target:
                    break
                v, whyr = ap.recheck(path, "PRESS")
                if v:
                    continue
                if tier == 1:
                    n, b = press_trim_kit(path, m)
                else:
                    r = subprocess.run(["rm", "-rf", "--one-file-system", "--", path], capture_output=True, text=True, timeout=7200)
                    n, b = (1, 0) if r.returncode == 0 else (0, 0)
                freed_press[tier] = freed_press.get(tier, 0) + 1
                with open(a.manifest + ".press", "a") as fh:
                    fh.write(f"{time.strftime('%F %T')}\t{tier}\t{path}\t{why}\t{n} files\t{b}\n")
    # summary line
    by = " ".join(f"{k.replace('DEL-', '')}={v / 1e9:.1f}" for k, v in sorted(ap.freed_by_cat.items()))
    frees = " ".join(f"{root}={df_free(root):.0f}G" for root, _, _ in fs_table(J.roots).values())
    tot = sum(ap.freed_by_cat.values()) / 1e9
    press = (" pressure=" + ",".join(f"T{k}:{v}" for k, v in sorted(freed_press.items()))) if freed_press else ""
    lows = [f"{r}<{tg}G" for r, tg, _ in fs_table(J.roots).values() if df_free(r) < tg]
    line(f"reason={a.reason} {'apply' if a.apply else 'dry'} freed={tot:.1f}GB [{by}]{press} free {frees}"
         + (f" LOW {','.join(lows)}" if lows else "") + f" manifest={a.manifest}",
         alert=("pressure exhausted: " + ",".join(lows)) if (lows and a.apply) else "")
    return 0


def press_trim_kit(d, m):
    """pressure tier 1: intermediates only (class b/c names), never finals, logs or objects"""
    names = set(m.TRIM_C) | set(m.TRIM_B) | {"4_1_cts.odb"}
    n, b = 0, 0
    for dp, dn, fn in os.walk(d):
        dn[:] = [x for x in dn if not os.path.islink(os.path.join(dp, x))]
        if "3_place.odb" not in fn and "6_final.odb" not in fn:
            continue
        for f in fn:
            if f not in names or f in m.NEVER:
                continue
            if f in m.TRIM_B and not ("6_final.odb" in fn and "6_final.spef" in fn):
                continue
            if f == "4_1_cts.odb" and "4_cts.odb" not in fn:
                continue
            p = os.path.join(dp, f)
            st = os.lstat(p)
            if time.time() - st.st_mtime < 6 * 3600 or not stat.S_ISREG(st.st_mode):
                continue
            os.unlink(p)
            n += 1
            b += st.st_blocks * 512
    return n, b


def hold_main(a):
    """one-line helper: ot_lifecycle.py hold <dir> [--hours 48] [--lane X] [--why ...]; re-run to renew (hours capped at 168)"""
    d = os.path.realpath(a.path)
    if not os.path.isdir(d):
        raise SystemExit("not a directory: " + d)
    h = min(float(a.hours), 168.0)
    rec = {"schema": "opentallas.ot_hold.v1", "path": d, "lane": a.lane or os.environ.get("OT_LANE", ""), "why": a.why,
           "created": int(time.time()), "created_h": time.strftime("%F %T %Z"), "expires": int(time.time() + h * 3600),
           "expires_h": time.strftime("%F %T %Z", time.localtime(time.time() + h * 3600))}
    t = os.path.join(d, ".ot-hold.tmp")
    with open(t, "w") as fh:
        json.dump(rec, fh, indent=1)
    os.replace(t, os.path.join(d, ".ot-hold"))
    print(f"held {d} until {rec['expires_h']} (renew by re-running)")
    return 0


# ------------------------------------------------------------------ localhost driver (lifesnap + collect + count guard), COORD 18:5x
HOSTS = ["intel1", "intel2", "epyc2", "epyc4", "epyc5", "epyc6"]
SSH = ["ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]
LOG_TXT = os.path.expanduser("~/coord/autopilot/log.txt")


def strict_protected():
    """full-row parse of both coord lists (COORD input 4).  Accepted rows: 'host|any<TAB or SPACE>/abs/path ...' or free text holding
    host:/abs/path tokens.  Every whole path token is kept; a row with no absolute path, or a file that shrank, aborts."""
    hosts = {"intel1", "intel2", "epyc2", "epyc4", "epyc5", "epyc6", "localhost", "any"}
    rows = []
    for f in (os.path.expanduser("~/coord/lanes/PROTECTED-DBS.txt"), os.path.expanduser("~/coord/PROTECTED-DBS.txt")):
        with open(f, errors="strict") as fh:
            for i, ln in enumerate(fh, 1):
                ln = ln.rstrip("\n")
                if not ln.strip() or ln.lstrip().startswith("#"):
                    continue
                t = re.split(r"[\t ]+", ln.strip())
                if t[0] in hosts and len(t) >= 2 and t[1].startswith("/"):
                    rows.append([t[0], os.path.normpath(t[1]), f"{os.path.basename(f)}:{i}"])
                    continue
                toks = [m for x in t for m in re.findall(r"(?:^|:)(/(?:srv|home)/[^\s,;()]+)$", x)]
                if not toks:
                    raise ValueError(f"malformed protected row {f}:{i}: {ln[:120]!r}")
                rows += [["any", os.path.normpath(q), f"{os.path.basename(f)}:{i}"] for q in toks]
    if len(rows) < 500:
        raise ValueError(f"protected rows too few: {len(rows)}")
    return rows


def build_lifesnap(out):

    Q = os.path.expanduser("~/coord/lanes/COORD-REVIEW-QUEUE.md")
    AGENTS = os.path.expanduser("~/.claude/jobs/b7f906df/tmp/agent_ids.tsv")
    ABS = re.compile(r"(?<![\w.~/])/(?:srv|home)/[^\s'\"<>|;,()\[\]{}`*?$\\]+")
    REL = re.compile(r"(?<![\w./-])(scratch\d*/claude/[^\s'\"<>|;,()\[\]{}`*?$\\]+)")
    WORD = re.compile(r"[A-Za-z0-9_.+-]{8,}")
    HDR = re.compile(r"^- (20\d\d-\d\d-\d\d \d\d:\d\d) PST\s+(.*)$")
    AUTH = re.compile(r"\[([A-Z0-9][A-Z0-9-]{2,})(?:\s*->|\])")
    now = time.time()
    lines = open(Q, errors="replace").read().splitlines()
    posts, cur = [], None
    for ln in lines:
        m = HDR.match(ln)
        if m:
            t = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M"))
            rest = m.group(2)
            auth = None
            if not rest.startswith(("KIT-WAVE", "AUTOPILOT", "ROUTE-FAIL", "FAIL-")):
                a = AUTH.search(rest[:200])
                if a:
                    auth = a.group(1)
            verb = rest[:40]
            cur = {"t": t, "auth": auth, "verb": verb, "text": ln}
            posts.append(cur)
        elif cur is not None:
            cur["text"] += "\n" + ln
    lane_last, parked = {}, {}
    for p in posts:
        if p["auth"]:
            if p["t"] >= lane_last.get(p["auth"], 0):
                lane_last[p["auth"]] = p["t"]
                parked[p["auth"]] = "PARKED" in p["verb"]
    # COORD 18:5x: liveness must decay by itself (a limit stop leaves LIVE rows stale in agent_ids): a registry LIVE row counts only
    # while its launch stamp is under 24 h old; otherwise a lane is live only by a queue post under 6 h old with no later PARKED
    # (the 24-h file-age rule and holds protect work of lanes stopped by a short limit).
    agents_live, agents_all = [], []
    for ln in open(AGENTS, errors="replace").read().splitlines():
        c = ln.split("\t")
        if len(c) >= 2 and re.fullmatch(r"[A-Z0-9-]+", c[0]):
            agents_all.append(c[0])
            if len(c) > 3 and c[2] == "LIVE":
                try:
                    if now - time.mktime(time.strptime(c[3].strip(), "%Y-%m-%d %H:%M")) < 24 * 3600:
                        agents_live.append(c[0])
                except ValueError:
                    pass
    live = set(agents_live)
    for l, t in lane_last.items():
        if now - t < 6 * 3600 and not parked.get(l) and l != "COORD":
            live.add(l)
        elif parked.get(l):
            live.discard(l)
    live.discard("COORD")
    paths48, words48 = {}, {}
    for p in posts:
        if now - p["t"] > 48 * 3600 or not p["auth"]:
            continue
        for m in ABS.findall(p["text"]):
            paths48.setdefault(os.path.normpath(m.rstrip(".:,;'\")]}")), p["t"])
        for m in REL.findall(p["text"]):
            paths48.setdefault(os.path.normpath("/srv/opentallas-" + m.rstrip(".:,;'\")]}")), p["t"])
        for w in WORD.findall(p["text"]):
            words48.setdefault(w.rstrip("."), p["t"])
    json.dump({"created": now, "created_h": time.strftime("%F %T %Z"), "live": sorted(live),
               "lane_last": {k: int(v) for k, v in lane_last.items()},
               "paths48": sorted(paths48), "words48": sorted(words48), "protected_full": strict_protected()}, open(out, "w"))
    print("live lanes", len(live), sorted(live)[:80])
    print("posts", len(posts), "paths48", len(paths48), "words48", len(words48), "agents", len(agents_all))



def _log(msg):
    ln = f"{time.strftime('%F %T %Z')} OT-LIFECYCLE: {msg}"
    with open(LOG_TXT, "a") as fh:
        fh.write(ln + "\n")
    print(ln, flush=True)


def count_total():
    """(total signed designs+types) from the release tree summary; None when unreadable"""
    r = subprocess.run([sys.executable, "-I", "tools/release_tree_render.py", "--summary"], cwd=os.path.expanduser("~/coord"),
                       capture_output=True, text=True, timeout=600)
    if r.returncode:
        return None
    t = 0
    seen = 0
    for m in re.finditer(r"SIGNED (?:types|hard-core designs) (\d+)/\d+", r.stdout):
        t += int(m.group(1))
        seen += 1
    return t if seen else None


def drive_main(a):
    os.makedirs(STATE_DIR, exist_ok=True)
    # 1. lifesnap to every host (atomic); a host that misses it stops itself when the snapshot ages out
    snap = os.path.join(STATE_DIR, "lifesnap.json")
    try:
        build_lifesnap(snap)
    except Exception as e:
        _log(f"alert lifesnap build failed: {e!r}")
        return 2
    ok = []
    data = open(snap, "rb").read()
    me = open(os.path.abspath(__file__), "rb").read()
    for h in a.hosts:
        r = subprocess.run(["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", h,
                            "cd / && mkdir -p ~/.local/share/ot-lifecycle && cat > ~/.local/share/ot-lifecycle/.ot-lifecycle.tmp "
                            "&& mv ~/.local/share/ot-lifecycle/.ot-lifecycle.tmp ~/.local/share/ot-lifecycle/ot-lifecycle.py"],
                           input=me, capture_output=True, timeout=120)
        if r.returncode:
            _log(f"alert {h}: tool push failed rc {r.returncode}")
        r = subprocess.run(["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", h,
                            "cd / && mkdir -p ~/.local/state/ot-lifecycle && cat > ~/.local/state/ot-lifecycle/.lifesnap.tmp "
                            "&& mv ~/.local/state/ot-lifecycle/.lifesnap.tmp ~/.local/state/ot-lifecycle/lifesnap.json"],
                           input=data, capture_output=True, timeout=120)
        if r.returncode:
            _log(f"alert {h}: lifesnap push failed rc {r.returncode}")
        else:
            ok.append(h)
    # 2. collect host tick lines into the autopilot log (every line that names an alert; summaries too, one line per tick)
    seenf = os.path.join(STATE_DIR, "seen.json")
    seen = json.load(open(seenf)) if os.path.exists(seenf) else {}
    deleted_now = 0.0
    for h in ok:
        r = subprocess.run(SSH + [h, "tail -n 400 ~/.local/state/ot-lifecycle/ticks.log 2>/dev/null"], capture_output=True, text=True, timeout=120)
        if r.returncode not in (0, 1):
            _log(f"alert {h}: cannot read ticks.log (rc {r.returncode})")
            continue
        for ln in r.stdout.splitlines():
            key = f"{h}|{ln}"
            if key in seen:
                continue
            seen[key] = time.time()
            with open(LOG_TXT, "a") as fh:
                fh.write(ln + "\n")
            m = re.search(r"freed=([0-9.]+)GB", ln)
            if m and " apply " in ln:
                deleted_now += float(m.group(1))
    cut = time.time() - 14 * 24 * 3600
    seen = {k: v for k, v in seen.items() if v > cut}
    with open(seenf + ".tmp", "w") as fh:
        json.dump(seen, fh)
    os.replace(seenf + ".tmp", seenf)
    # 3. count guard: a drop while this system deleted halts every host for 6 h and raises a visible alert
    statef = os.path.join(STATE_DIR, "count.json")
    st = json.load(open(statef)) if os.path.exists(statef) else {}
    n = count_total()
    if n is None:
        _log("alert count unreadable; hosts continue on their own controls this hour")
    else:
        prev = st.get("n")
        if prev is not None and n < prev and (deleted_now > 0 or st.get("recent_del", 0) > 0):
            msg = f"sign-off count dropped {prev} -> {n} with {deleted_now:.0f} GB deleted this cycle; hosts halted 6 h, check lanes/prune manifests"
            _log("alert " + msg)
            for h in ok:
                subprocess.run(SSH + [h, f"echo {shlex_q(msg)} > ~/.local/state/ot-lifecycle/HALT"], capture_output=True, timeout=60)
            st["halted"] = time.time()
        st["n"] = max(n, prev if prev is not None and n >= prev else n)
        st["n"] = n
        st["recent_del"] = deleted_now
        st["t"] = time.time()
    if st.get("halted") and time.time() - st["halted"] > 6 * 3600:
        for h in ok:
            subprocess.run(SSH + [h, "rm -f ~/.local/state/ot-lifecycle/HALT"], capture_output=True, timeout=60)
        st.pop("halted", None)
        _log("HALT released after 6 h (no agent in the loop); hosts resume")
    with open(statef, "w") as fh:
        json.dump(st, fh)
    print("drive done: hosts", ok, "deleted this cycle GB", round(deleted_now, 1), flush=True)
    return 0


def shlex_q(s):
    import shlex
    return shlex.quote(s)

def setup_job(a, m):
    argv = ["run", "--host", a.host, "--state", a.state, "--snapshot", a.snapshot,
            "--classes", "c", "--max-snapshot-age-h", "6"]
    if a.roots:
        argv += ["--roots"] + a.roots
    if getattr(a, "docker", None) is not None:
        argv += ["--docker", a.docker]
    J_box = {}

    def setup(self):
        J_box["J"] = self
        self.roots = m.dedupe_roots(self.a.roots)
        self.load_snapshot()
        self.live = m.Live(self.a.docker, self.deep)
        self.found = m.scan_roots(self.roots, self.a.find_timeout)
        self.load_counted()
        # local keep WITHOUT the self-fed union file, per DISK-URGENT-2 logic; computed in load_local_keeps then filtered by Plan.localkeep_hit
        self.load_local_keeps()
        return 0
    m.Job._run = setup
    m.main(argv)
    J = J_box.get("J")
    if J is None:
        raise SystemExit("guard setup failed")
    if J.found is None:
        raise SystemExit("guard scan failed")
    return J


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tick", help="standing job: guards, plan, apply, pressure stage, one summary line; dry unless --apply")
    t.add_argument("--apply", action="store_true")
    t.add_argument("--reason", default="timer", choices=("timer", "jobend", "manual"))
    t.add_argument("--tool", default=os.path.expanduser("~/.local/share/ot-autoclean-auto/ot-autoclean.py"))
    t.add_argument("--host", default="")
    t.add_argument("--lifesnap", default=os.path.join(STATE_DIR, "lifesnap.json"))
    t.add_argument("--out", default=os.path.join(STATE_DIR, "manifests"))
    t.add_argument("--state", default=os.path.join(STATE_DIR, "guards"))
    t.add_argument("--snapshot", default=os.path.expanduser("~/.local/state/ot-autoclean-auto/snapshot"))
    t.add_argument("--roots", nargs="*", default=None)
    t.add_argument("--refs", default="")
    t.add_argument("--docker", default=None)
    dv = sub.add_parser("drive", help="localhost: lifesnap push, tick-line collection into autopilot/log.txt, count guard")
    dv.add_argument("--hosts", default=",".join(HOSTS))
    hp = sub.add_parser("hold", help="create or renew an expiring hold on a directory")
    hp.add_argument("path")
    hp.add_argument("--hours", default="48")
    hp.add_argument("--lane", default="")
    hp.add_argument("--why", default="")
    for name in ("plan", "apply"):
        p = sub.add_parser(name)
        p.add_argument("--tool", required=True)
        p.add_argument("--host", required=True)
        p.add_argument("--lifesnap", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--state", default=os.path.expanduser("~/autoclean-12/state"))
        p.add_argument("--roots", nargs="*", default=None)
        p.add_argument("--refs", default="")
        p.add_argument("--snapshot", default=os.path.expanduser("~/.local/state/ot-autoclean-auto/snapshot"))
        p.add_argument("--docker", default=None)
        if name == "apply":
            p.add_argument("--manifest", required=True)
            p.add_argument("--cats", default="")
            p.add_argument("--dry", action="store_true")
            p.add_argument("--coord-ref", required=True, help="queue post time of the COORD reply")
    a = ap.parse_args()
    if a.cmd == "hold":
        sys.exit(hold_main(a))
    if a.cmd == "drive":
        a.hosts = [h for h in a.hosts.split(",") if h]
        sys.exit(drive_main(a))
    if a.cmd == "tick":
        a.host = a.host or {"key-cardinal": "intel1", "tolerant-swine": "intel2", "dear-crayfish": "epyc2", "aware-parakeet": "epyc4",
                            "devoted-wren": "epyc5", "eager-sunfish": "epyc6"}.get(os.uname().nodename, os.uname().nodename)
        os.makedirs(a.out, exist_ok=True)
        os.makedirs(a.state, exist_ok=True)
        sys.exit(tick_main(a))
    m = load_tool(a.tool)
    J = setup_job(a, m)
    if a.cmd == "apply":
        sys.exit(Apply(a, m, J).run())
    Plan(a, m, J).run()


if __name__ == "__main__":
    main()
