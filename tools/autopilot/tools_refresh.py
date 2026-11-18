#!/usr/bin/env python3 -I
"""tools_refresh.py -- WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1500 A): automatic tools refresh instead of holds.

When TOOLS-LAG (tools/tools_lag.py) names an approved die-tool ruling that a die's current tree lacks, compose a TOOLS-ONLY delta tree: the current
tree plus main's tools/ and physical/common_flow (src_manifest delta-make --paths, delta-apply --link, publish, replicate --link-from), so plan and RTL
stay byte-identical.  Then:
  guard  src_manifest hosts --expect <manifest_hash> on every gen host + the shared-inode check;
  bind   the strict bind run with the NEW tree's tools reproduces the die's bind of record (native_topology.json hash);
  apply  (only when bind is unchanged) kit_wave_edit patch: dies.<die>.src / src_manifest_hash / paths into the old tree repointed, old tree queued in
         superseded_trees;  bind changed -> NEEDS-LANE to the die owner, nothing is applied.
A die opts in with dies.<die>.tools_refresh: true (apply), "dry" (compose + guard + bind, report only); absent / false = off.

    tools_refresh.py --die D [--cfg kit_wave.json] [--repo GIT_DIR] [--main main] [--dry]
"""
import argparse
import json
import re
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))              # python3 -I does not put the script dir on sys.path: overlay_classify lives here
import tools_lag as TL  # noqa: E402
import overlay_classify as OC  # noqa: E402
import flow_guard as FG  # noqa: E402

TOOL_PATHS = ("tools", "physical/common_flow")
SM = str(HERE / "src_manifest.py")
STATE_REL = "tools_refresh_state.json"


MAX_CRASHES = 3
STRUCTURAL = ("COMPOSE-FAIL", "GUARD-FAIL", "BIND-FAIL", "BIND-CHANGED", "OVERLAY-PRIVATE", "APPLY-FAIL")


def stop_fp(d):
    """what must change before a die that stopped on a structural exit may try again: its tree and its bind recipe settings (a new apply, or a recipe from the owner)"""
    import hashlib
    keys = ("src", "tools_refresh", "tools_refresh_bind_cmd", "tools_refresh_bind_sub", "tools_refresh_bind_pass")
    return hashlib.sha1(json.dumps({k: d.get(k) for k in keys}, sort_keys=True, default=str).encode()).hexdigest()[:16]


def wave_key(die, lag):
    """the wave's own dedupe key (no main sha): die | pin | rulings.  kit_wave.tools_refresh_tick builds the same string"""
    return f"{die}|{lag.get('pin')}|{','.join(lag.get('missing') or [])}"


def refresh_key(die, lag, main_sha):
    return f"{die}|{lag.get('pin')}|{main_sha[:12]}|{','.join(lag.get('missing') or [])}"


def mode_of(d):
    v = d.get("tools_refresh")
    return "apply" if v is True else ("dry" if v == "dry" else "")


def should_refresh(d, lag, state, key):
    """-> (bool, why): the die opted in, TOOLS-LAG names at least one ruling, and this exact (pin, main, rulings) was not tried yet"""
    if not mode_of(d):
        return False, "tools_refresh off"
    if not d.get("src"):
        return False, "no tree"
    if lag.get("n_commits") is None or not lag.get("missing"):
        return False, "no die-tool ruling missing"
    stopped = (state.get("stopped") or {}).get(d.get("_die", ""))
    if stopped and stopped.get("fp") == stop_fp(d):
        return False, f"stopped on {stopped.get('status')} ({str(stopped.get('why'))[:120]}): NEEDS-LANE was posted; a new tree or a changed bind recipe resumes it"
    n = int((state.get("crashes") or {}).get(wave_key(d.get("_die", ""), lag), 0))
    if n >= MAX_CRASHES:
        return False, f"crash stop: {n} crashed passes for this pin and rulings, a lane must look"
    if key in (state.get("done") or {}) and state["done"][key].get("status") != "CRASH":
        return False, "already handled: " + str(state["done"][key].get("status"))
    return True, ""


def new_tree_path(old_tree, main_sha):
    return f"{str(old_tree).rstrip('/')}_t{main_sha[:7]}"


def repoint(obj, old, new):
    """deep copy of a config value with every string that starts with / contains the old tree path repointed to the new tree"""
    if isinstance(obj, str):
        return obj.replace(old, new) if old in obj else obj
    if isinstance(obj, list):
        return [repoint(x, old, new) for x in obj]
    if isinstance(obj, dict):
        return {k: repoint(v, old, new) for k, v in obj.items()}
    return obj


def rekey_holds(die, recs, old_tree, new_tree, old_hash, new_hash):
    """r647 follow-up (HEAD-PLAN-R4): plan and RTL are byte-identical, so a pilot / tree-manifest hold stays valid for the new tree.  Re-key, in one record list:
    the 12-hex manifest in the record id, release terms (gen_pilot:<die>:<sha12>) and reason, and the old tree path in tree_ready / tree_has terms.  Proof fields
    (published_gen_proof) and every other record stay verbatim.  -> (new list, number of records changed)"""
    o12, n12 = str(old_hash or "")[:12].lower(), str(new_hash or "")[:12].lower()
    out, n = [], 0
    for r in recs or []:
        s = json.dumps(r, sort_keys=True)
        keep = {k: r[k] for k in ("published_gen_proof",) if k in r}
        nr = dict(r)
        for k in ("id", "reason"):
            if isinstance(nr.get(k), str) and o12 and n12 and o12 in nr[k]:
                nr[k] = nr[k].replace(o12, n12)
        if isinstance(nr.get("release"), list):
            nr["release"] = [t.replace(o12, n12) if isinstance(t, str) and t.startswith("gen_pilot:") and o12 and n12 else
                             (t.replace(old_tree, new_tree) if isinstance(t, str) and t.startswith(("tree_ready:", "tree_has")) else t) for t in nr["release"]]
        nr.update(keep)
        if json.dumps(nr, sort_keys=True) != s:
            n += 1
        out.append(nr)
    return out, n


def patch_ops(die, d, old_tree, new_tree, manifest_hash, main_sha=None, hosts=None):
    """the kit_wave_edit JSON patch that switches the die to the new tree: src, src_manifest_hash, every die key naming the old tree repointed, old tree queued.
    hosts (LATENCY-R 11-18): the gen hosts that hold the new tree when replication left some out; gen_hosts (and gen_host) narrow to them"""
    ops = [{"op": "replace", "path": f"/dies/{die}/src", "value": new_tree}]
    if hosts and list(hosts) != list(d.get("gen_hosts") or []):
        ops.append({"op": "replace" if d.get("gen_hosts") is not None else "add", "path": f"/dies/{die}/gen_hosts", "value": list(hosts)})
        if d.get("gen_host") and d.get("gen_host") not in hosts:
            ops.append({"op": "replace", "path": f"/dies/{die}/gen_host", "value": hosts[0]})
    if d.get("src_manifest_hash") is not None:
        ops.append({"op": "replace", "path": f"/dies/{die}/src_manifest_hash", "value": manifest_hash})
    else:
        ops.append({"op": "add", "path": f"/dies/{die}/src_manifest_hash", "value": manifest_hash})
    if main_sha:                          # COORD 11-17: the tools-lag check and the tool-skew pin read dies.<die>.tools_sha first; left at the old pin, every tick saw the same lag and started another refresh
        ops.append({"op": "replace" if d.get("tools_sha") is not None else "add", "path": f"/dies/{die}/tools_sha", "value": main_sha})
    for k, v in d.items():
        if k in ("src", "src_manifest_hash", "superseded_trees", "hold_records", "tools_sha") or (hosts and k in ("gen_hosts", "gen_host")):
            continue
        nv = repoint(v, old_tree, new_tree)
        if nv != v:
            ops.append({"op": "replace", "path": f"/dies/{die}/{k}", "value": nv})
    recs, n = rekey_holds(die, d.get("hold_records"), old_tree, new_tree, d.get("src_manifest_hash"), manifest_hash)
    if n:
        ops.append({"op": "replace", "path": f"/dies/{die}/hold_records", "value": recs})          # one patch = one atomic kit_wave_edit commit with the src switch
    ops.append({"op": "add", "path": f"/dies/{die}/superseded_trees" + ("/-" if d.get("superseded_trees") else ""),
                "value": old_tree if d.get("superseded_trees") else [old_tree]})
    return ops


DEFAULT_BIND_CMD = ("mkdir -p {out}/o && OT_HEAVY_PRIO=die ot-heavy --mem 96 -- bash -c '"
                    "python3 -I -B tools/die_plan/bind.py elab {plan} --asbuilt {asbuilt} --out {out}/o --strict --mem 96 > {out}/elab.log 2>&1 && "
                    "python3 -I -B tools/die_plan/bind.py bind {plan} --asbuilt {asbuilt} --out {out}/o --strict > {out}/bind.log 2>&1'")


def live_owner(die, d, activity=None, now=None, hours=12.0):
    """11-18 (COORD r700): the lane a NEEDS-LANE goes to = the first of dies.<die>.refresh_owner, the die's owner_lane, the known die owners that posted to the review queue in the
    last `hours` h (a dead lane id such as DIE-S81-92 gets nothing); else COORD.  activity = {lane: epoch of its latest post}"""
    now = time.time() if now is None else now
    if activity is None:
        try:
            import hold_records as HR
            activity = HR.lane_activity(open(os.path.expanduser("~/coord/lanes/COORD-REVIEW-QUEUE.md"), errors="replace").read().splitlines()[-6000:])
        except Exception:
            activity = {}
    if not activity:                                     # no queue readable (a gate host): keep the configured owner, never invent one
        return d.get("refresh_owner") or d.get("owner_lane") or die
    for lane in [d.get("refresh_owner"), d.get("owner_lane")] + list(LIVE_OWNER_FALLBACK.get(die, ())):
        if lane and now - float(activity.get(lane) or 0) <= hours * 3600:
            return lane
    return "COORD"


LIVE_OWNER_FALLBACK = {"s81": ("S81-DIE-R3", "S81-TYPES-R3", "FIX-S81-OPUS"), "qwen_kvsys": ("FABLE-FIX-KV-HG", "KV-HG-OPUS", "KV-R3"),
                       "s81_head": ("HEAD-PLAN-R4", "HEAD-TYPES-R4"), "qwen_compute": ("QC-PLAN-R3", "QC-TYPES-R3"), "hbm": ("HBM-CORES-B", "HBM-PLAN")}


class Ops:
    """the real steps: ssh to the die's gen host, run src_manifest there; each returns (ok, detail)"""

    def __init__(self, d, repo, main_sha, run=None):
        self.d, self.repo, self.sha = d, repo, main_sha
        self.overlay_report = {}
        self.delta_paths = None            # the files the tools-only pack changes (read from delta.json before the pack is removed)
        self.run = run or self._run
        self.host = d.get("gen_host") or (d.get("gen_hosts") or [None])[0]
        self.hosts = [self.host] + [h for h in (d.get("gen_hosts") or []) if h != self.host]    # the hosts that hold the new tree (narrowed by compose)
        self.dropped = {}                                                                     # host -> why replication left it out

    @staticmethod
    def _run(host, cmd, timeout=3600):
        argv = ["bash", "-c", cmd] if host in (None, "", "localhost", "hub") else ["ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", host, cmd]
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.TimeoutExpired) as e:
            return 255, f"{type(e).__name__}: {e}"
        return r.returncode, (r.stdout + r.stderr).strip()

    def pack_cmd(self, old, new, drop=()):
        """hub side: the gen host has no git store of main, so the pack is built on the hub from the tree's manifest alone (delta-make reads only
        OLD/.src-manifest.json) and rsynced to the gen host"""
        q = shlex.quote
        work = os.path.expanduser("~/.cache/tools-refresh/" + os.path.basename(new))
        paths = " ".join(q(p) for p in TOOL_PATHS)
        dropping = (" --drop-overlay " + " ".join(q(p) for p in drop)) if drop else ""
        sm = f"python3 -I {q(SM)}"
        ssh = "ssh -n -o ControlPath=none -o BatchMode=yes"
        cmd = (f"rm -rf {q(work)} && mkdir -p {q(work)}/stub && {ssh} {q(self.host)} {q('cat ' + old + '/.src-manifest.json')} > {q(work)}/stub/.src-manifest.json "
               f"&& {sm} delta-make {q(work)}/stub --repo {q(self.repo)} --sha {q(self.sha)} --paths {paths}{dropping} --out {q(work)}/pack "
               f"&& rsync -a -e 'ssh -o ControlPath=none -o BatchMode=yes' {q(work)}/pack/ {q(self.host)}:{q(new + '.pack')}/ ; rc=$?; rm -rf {q(work)}/stub; exit $rc")
        return cmd

    def compose_cmds(self, old, new):
        """gen-host side commands after the pack arrived"""
        q = shlex.quote
        pack = f"{new}.pack"
        sm = f"python3 -I {q(SM)}"
        others = [h for h in (self.d.get("gen_hosts") or []) if h != self.host]
        cmds = [f"{sm} delta-apply {q(pack)} --old {q(old)} --out {q(new)} --link",
                f"{sm} verify {q(new)}", f"{sm} publish {q(new)}"]
        if others:
            cmds.append(f"{sm} replicate {q(new)} --hosts {q(','.join(others))} --link-from {q(os.path.basename(old))}")
        return cmds

    def classify_overlay(self):
        """r610: overlay paths of the tree that main also changed, classified against the hub repo: (a) main has the blob, (b) the change is contained in main ->
        main wins (dropped from the overlay, logged); (c) a private patch -> stop.  -> (drop paths, {path: result of the private ones})"""
        res = OC.classify_die(self.repo, dict(self.d, src=self.d["src"]), self.sha)
        self.overlay_report = {p: v["cls"] for p, v in res.items()}
        return sorted(p for p, v in res.items() if v["cls"] in "ab"), {p: v for p, v in res.items() if v["cls"] == "c"}

    def compose(self, old, new):
        try:
            drop, private = self.classify_overlay()
        except (ValueError, OSError, KeyError, subprocess.SubprocessError) as e:
            return False, f"overlay classification failed: {type(e).__name__}: {e}"[:400], ""
        if private:
            return False, "OVERLAY-PRIVATE: " + "; ".join(f"{p}: {v['why']}\n{v.get('diff', '')[:700]}" for p, v in list(private.items())[:6]), ""
        # 11-18 (COORD, S81/QC refreshes built the tree, BIND-FAIL / COMPOSE-FAIL 'exists', then re-ran from nothing): a verified tree of this name that is already on the gen host
        # is reused: no pack, no delta-apply, no publish; verify + replicate only.
        rcx, _ = self.run(self.host, f"REUSE_PROBE=1; test -f {shlex.quote(new + '/.src-manifest.sha256')} && test ! -e {shlex.quote(new + '.part')}")
        reuse = rcx == 0
        if not reuse:
            rc, out = self.run(None, self.pack_cmd(old, new, drop))
            if rc:
                return False, f"delta-make (hub): rc {rc}: {out[-400:]}", ""
        steps = [c for c in self.compose_cmds(old, new) if not (reuse and (" delta-apply " in c or " publish " in c))]
        # per-host replicate in PARALLEL (FABLE-FLOW-0010 C): one command per host, each --link-from the old tree (deltas only)
        rep = [c for c in steps if " replicate " in c]
        if rep:
            q = shlex.quote
            others = [h for h in (self.d.get("gen_hosts") or []) if h != self.host]
            sm = f"python3 -I {q(SM)}"
            per = [f"{sm} replicate {q(new)} --hosts {q(h)} --link-from {q(os.path.basename(old))}" for h in others]
            steps = [c for c in steps if " replicate " not in c] + ["__PARALLEL_REPLICATE__"]
        for c in steps:
            if c == "__PARALLEL_REPLICATE__":
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=max(1, len(per))) as ex:
                    results = list(ex.map(lambda x: self.run(self.host, x), per))
                rc = max(r[0] for r in results)
                out = "\n".join(r[1] for r in results)
                c = per[0] + " replicate "
            else:
                rc, out = self.run(self.host, c)
            if rc and " replicate " in c:
                # LATENCY-R 11-18: one gen host short of disk (epyc8/epyc10/intel1, 19:36-22:19) stopped KV and HEAD refreshes for hours (COMPOSE-FAIL is a
                # structural stop).  The hosts that took the tree keep it; the others are dropped from the die's gen_hosts by the apply patch.
                ok = [h for h in self.hosts[1:] if re.search(rf"^{re.escape(h)}: OK\s*$", out or "", re.M)]
                self.dropped = {h: next((ln for ln in (out or "").splitlines() if ln.startswith(h + ":") and not ln.endswith("OK")), "no OK line")[:200]
                                for h in self.hosts[1:] if h not in ok}
                self.hosts = [self.host] + ok
                continue
            if rc:
                return False, f"{c.split()[3] if len(c.split()) > 3 else c}: rc {rc}: {out[-400:]}", ""
        rc, dj = self.run(self.host, f"cat {shlex.quote(new + '.pack')}/delta.json")
        try:
            dd = json.loads(dj)
            self.delta_paths = sorted(set(dd.get("add") or {}) | set(dd.get("delete") or []))
        except (ValueError, TypeError):
            self.delta_paths = None
        self.run(self.host, f"rm -rf {shlex.quote(new + '.pack')}")
        rc, h = self.run(self.host, f"cat {shlex.quote(new)}/.src-manifest.sha256")
        return rc == 0, "composed", h.strip()

    def guard(self, new, manifest_hash):
        hosts = ",".join(getattr(self, "hosts", None) or self.d.get("gen_hosts") or [self.host])
        rc, out = self.run(None, f"python3 -I {shlex.quote(SM)} hosts {shlex.quote(new)} --hosts {shlex.quote(hosts)} --expect {shlex.quote(manifest_hash)}")
        if rc:
            return False, "guard hosts verify: " + out[-300:]
        rc, out = self.run(self.host, f"python3 -I {shlex.quote(SM)} links {shlex.quote(new)}")
        return rc == 0, "guard ok" if rc == 0 else "guard links: " + out[-300:]

    def bind_cmd(self, new, out):
        kr = self.d.get("kit_rtl") or {}
        tpl = self.d.get("tools_refresh_bind_cmd") or ""
        # {out} = the empty scratch dir next to the tree, {out_rel} = the same dir relative to the tree root (HEAD head_die_portbind wants --out repo-relative)
        return f"cd {shlex.quote(new)} && " + tpl.format(plan=self.d.get("plan", "").replace(self.d.get("src", ""), new), out=out, out_rel="../" + os.path.basename(out),
                                                        bind=out, asbuilt=(kr.get("asbuilt") or "").replace(self.d.get("src", ""), new), tree=new)

    def bind_closure_touched(self):
        """-> sorted delta files inside the import closure of tools/die_plan/bind.py (main's), None when the delta is unknown"""
        if self.delta_paths is None:
            return None
        root = Path(__file__).resolve().parents[2]

        def read(rel):
            try:
                return (root / rel).read_text()
            except (OSError, UnicodeDecodeError):
                return None
        closure = set(FG.closure_files(read, entry=("tools/die_plan/bind.py",)))
        return sorted(p for p in self.delta_paths if p in closure)

    def bind(self, new):
        """strict bind with the new tree's tools into a scratch dir; unchanged = native_topology.json equals the bind of record"""
        kr = self.d.get("kit_rtl") or {}
        if not self.d.get("tools_refresh_bind_cmd"):
            # 11-18 (COORD r700): a delta that touches bind.py's closure (or an unknown delta, a reused tree) used to stop with NEEDS-LANE to a dead lane.  The refresh now runs the
            # strict bind itself with DEFAULT_BIND_CMD (elab + bind --strict into {out}/o, compared by native_topology.json); a bind that cannot run is an optimistic switch with a
            # warning (r693); only a bind that ran and DIFFERS is a real change (NEEDS-LANE to the live owner).
            touched = self.bind_closure_touched()
            if touched == []:
                return True, True, f"bind closure untouched: none of the {len(self.delta_paths)} delta files is in bind.py's import closure"
            self.d = dict(self.d, tools_refresh_bind_cmd=DEFAULT_BIND_CMD, tools_refresh_bind_sub="o", _default_bind=True)
            self._why_default = ("delta unknown (reused tree)" if touched is None else f"delta touches bind.py's import closure ({len(touched)}: {', '.join(touched[:6])})")
        if False:
            # no bind recipe named for this die: the bind of record is unchanged by construction when the delta touches nothing bind.py imports
            touched = self.bind_closure_touched()
            if touched is None:
                return False, False, "the tools delta is unknown (delta.json unreadable): cannot show the bind closure is untouched"
            if not touched:
                return True, True, f"bind closure untouched: none of the {len(self.delta_paths)} delta files is in bind.py's import closure"
            return False, False, (f"the delta touches bind.py's import closure ({len(touched)}: {', '.join(touched[:8])}) and dies.{self.d.get('_die', '<die>')}.tools_refresh_bind_cmd "
                                  f"names no strict-bind recipe to re-run (a bind recipe is per die: env such as OT_HCPARAM_ALL, packaged elaboration): the die owner gives it")
        out = f"{new}.bindcheck"
        pass_re = self.d.get("tools_refresh_bind_pass")
        if pass_re:
            # a recipe with a PASS line and no comparable bind output (HEAD head_die_portbind: HEAD_DIE_PORTBIND PASS ...): rc 0 + the line = bind holds, same as the record
            rc, txt = self.run(self.host, self.bind_cmd(new, out))
            self.run(self.host, f"rm -rf {shlex.quote(out)}")
            if rc or not re.search(pass_re, txt or ""):
                return False, False, f"strict bind did not pass (rc {rc}, wanted /{pass_re}/): " + (txt or "")[-300:]
            return True, True, "strict bind PASS (no bind output to compare; PASS line matched)"
        record = (kr.get("bind_out") or "").rstrip("/")
        if not record:
            return False, False, "no kit_rtl.bind_out of record: cannot compare"
        sub = str(self.d.get("tools_refresh_bind_sub") or "").strip("/")        # where native_topology.json lands under {out} (KV: bind)
        outdir = f"{out}/{sub}" if sub else out
        rc, txt = self.run(self.host, self.bind_cmd(new, out))
        if rc:
            self.run(self.host, f"rm -rf {shlex.quote(out)}")
            if self.d.get("_default_bind"):
                return True, True, f"WARNING optimistic switch: the default strict bind did not complete ({getattr(self, '_why_default', '')}; rc {rc}: {txt[-160:]})"
            return False, False, "strict bind failed: " + txt[-300:]
        rc, got = self.run(self.host, f"sha256sum {shlex.quote(outdir)}/native_topology.json {shlex.quote(record)}/native_topology.json | awk '{{print $1}}'")
        shas = got.split()
        self.run(self.host, f"rm -rf {shlex.quote(out)}")
        if rc or len(shas) != 2:
            return False, False, "native_topology.json hash unreadable: " + got[-200:]
        return True, shas[0] == shas[1], "bind native_topology unchanged" if shas[0] == shas[1] else "bind native_topology CHANGED"


def _refresh(die, d, lag, main_sha, ops, state, post, edit, dry=False, now=time.time):
    """one refresh pass -> record dict (status: SKIP | GUARD-FAIL | BIND-FAIL | BIND-CHANGED | COMPOSE-FAIL | DRY-OK | APPLIED | APPLY-FAIL); stored in state['done'][key]"""
    key = refresh_key(die, lag, main_sha)
    d = dict(d, _die=die)
    ok, why = should_refresh(d, lag, state, key)
    if not ok:
        return dict(status="SKIP", why=why)
    old = d["src"]
    new = new_tree_path(old, main_sha)
    rec = dict(key=key, old=old, new=new, missing=lag["missing"], ts=int(now()), owner=live_owner(die, d))
    state.setdefault("done", {})[key] = rec          # the attempt is recorded only now: compose is about to start (a crash before this point is not an attempt)
    state.setdefault("attempts", {})[wave_key(die, lag)] = dict(key=key, status="STARTED", ts=int(now()))
    good, detail, h = ops.compose(old, new)
    rep = getattr(ops, "overlay_report", None) or {}
    if rep:
        rec["overlay_main_wins"] = sorted(p for p, c in rep.items() if c in "ab")       # logged: the fix is already in main (a: blob in history, b: contained)
    if not good and "OVERLAY-PRIVATE" in detail:
        # r610: only an overlay whose change is NOT in main stops the refresh; those paths go to the die owner with their diff
        rec.update(status="OVERLAY-PRIVATE", why=detail[:3000])
        post(f"NEEDS-LANE [TOOLS-REFRESH -> {rec['owner'] or die}] {die}: tools-only refresh of {old} is blocked by private tools patches in the tree overlay "
             f"(main wins on {len(rec.get('overlay_main_wins', []))} other overlay paths): {detail[len('OVERLAY-PRIVATE: '):][:1800]}")
        return rec
    if not good:
        rec.update(status="COMPOSE-FAIL", why=detail)
        return rec
    good, detail = ops.guard(new, h)
    if not good:
        rec.update(status="GUARD-FAIL", why=detail)
        post(f"NEEDS-LANE [TOOLS-REFRESH -> {rec['owner'] or die}] {die}: tools-only tree {new} failed the guard: {detail}")
        return rec
    ran, unchanged, detail = ops.bind(new)
    if not ran:
        rec.update(status="BIND-FAIL", why=detail)
        post(f"NEEDS-LANE [TOOLS-REFRESH -> {rec['owner'] or die}] {die}: strict bind on {new} did not run: {detail}")
        return rec
    if not unchanged:
        rec.update(status="BIND-CHANGED", why=detail)
        post(f"NEEDS-LANE [TOOLS-REFRESH -> {rec['owner'] or die}] {die}: main tools ({', '.join(lag['missing'][:12])}) change the bind of record on {new}: {detail}; "
             f"not applied, die owner decides")
        return rec
    if dry or mode_of(d) == "dry":
        rec.update(status="DRY-OK", why="guard ok, bind unchanged; dry mode: not applied")
        return rec
    try:
        dropped = getattr(ops, "dropped", None) or {}
        if dropped:
            rec["dropped_hosts"] = dropped
        edit(die, patch_ops(die, d, old, new, h, main_sha, hosts=(list(ops.hosts) if dropped else None)), f"TOOLS-REFRESH {die}: tools-only tree {os.path.basename(new)} (rulings {', '.join(lag['missing'][:12])}); guard + strict bind unchanged")
    except Exception as e:                       # the edit tool refused: nothing changed
        rec.update(status="APPLY-FAIL", why=f"{type(e).__name__}: {e}"[:300])
        post(f"NEEDS-LANE [TOOLS-REFRESH -> {rec['owner'] or die}] {die}: tree {new} is verified but the config edit failed: {rec['why']}")
        return rec
    rec.update(status="APPLIED", why="guard ok, bind unchanged, config switched")
    post(f"TOOLS-REFRESH {die}: switched to {new} (rulings {', '.join(lag['missing'][:12])}); plan and RTL byte-identical, strict bind unchanged")
    return rec


def record_crash(state, die, d, lag, main_sha, exc, post):
    """r615: a crashed pass is counted per (die, pin, rulings); stop at MAX_CRASHES with one NEEDS-LANE.  After compose started the record says CRASH and the key may be
    retried; a crash before that is no attempt at all (nothing marks the key)"""
    wk = wave_key(die, lag)
    state.setdefault("crashes", {})[wk] = int(state.get("crashes", {}).get(wk, 0)) + 1
    key = refresh_key(die, lag, main_sha)
    why = f"{type(exc).__name__}: {exc}"[:300]
    if key in state.get("done", {}):
        state["done"][key].update(status="CRASH", why=why)
        state.get("attempts", {}).get(wk, {}).update(status="CRASH")
    n = state["crashes"][wk]
    if n >= MAX_CRASHES:
        post(f"NEEDS-LANE [TOOLS-REFRESH -> {live_owner(die, d)}] {die}: tools_refresh crashed {n} times for these rulings ({why}); "
             f"stopped, no more automatic passes for this pin and rulings")
    return dict(status="CRASH", why=why, crashes=n)


def refresh(die, d, lag, main_sha, ops, state, post, edit, dry=False, now=time.time):
    """one pass (see _refresh).  r-FABLE-FLOW-1900 B: the first STRUCTURAL exit (compose / guard / bind / overlay / apply) stops the die: NEEDS-LANE once, recorded in
    state['stopped'][die] with a fingerprint of its tree and bind recipe; nothing retries until that fingerprint changes"""
    rec = _refresh(die, d, lag, main_sha, ops, state, post, edit, dry=dry, now=now)
    if rec.get("status") in STRUCTURAL:
        d2 = dict(d, _die=die)
        state.setdefault("stopped", {})[die] = dict(status=rec["status"], why=str(rec.get("why"))[:400], fp=stop_fp(d2), ts=int(now()))
        if rec["status"] == "COMPOSE-FAIL":            # the other structural statuses post their own NEEDS-LANE
            post(f"NEEDS-LANE [TOOLS-REFRESH -> {rec.get('owner') or die}] {die}: tools-only tree {rec.get('new')} could not be composed or replicated: {str(rec.get('why'))[:500]}; "
                 f"stopped (no retry); free the host named or exclude it, then change the die tree or recipe settings to resume")
    return rec


def load_state(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return {}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--die", required=True)
    ap.add_argument("--cfg", default=os.path.expanduser("~/coord/autopilot/kit_wave.json"))
    ap.add_argument("--repo", default=TL.DEFAULT_REPO)
    ap.add_argument("--main", default="main")
    ap.add_argument("--state", default=os.path.expanduser("~/coord/autopilot/" + STATE_REL))
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    import fcntl
    lock = open(str(Path(a.state).with_name(f"tools_refresh_{a.die}.lock")), "a")      # single flight per die: a second pass exits at once, touching nothing
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print(json.dumps({"status": "BUSY", "why": "another tools_refresh pass of this die holds the lock"}))
        return 0
    cfg = json.loads(Path(a.cfg).read_text())
    d = (cfg.get("dies") or {}).get(a.die) or {}
    lag = TL.lag(a.repo, TL.pin_of(d), a.main)
    main_sha = TL.run_git(a.repo, "rev-parse", a.main).strip()
    state = load_state(a.state)

    def post(text):
        subprocess.run(["bash", os.path.expanduser("~/coord/bin/post.sh"), "TOOLS-REFRESH", text], capture_output=True, text=True)

    def edit(die, ops, msg):
        r = subprocess.run([sys.executable, "-I", str(HERE / "kit_wave_edit.py"), "--message", msg, "--patch", json.dumps(ops)], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError((r.stdout + r.stderr)[-300:])

    try:
        rec = refresh(a.die, d, lag, main_sha, Ops(d, a.repo, main_sha), state, post, edit, dry=a.dry)
    except Exception as e:
        rec = record_crash(state, a.die, d, lag, main_sha, e, post)
    else:
        wk = wave_key(a.die, lag)
        if wk in state.get("attempts", {}) and rec.get("status") not in ("SKIP",):
            state["attempts"][wk]["status"] = rec.get("status")
    Path(a.state).write_text(json.dumps(state, indent=1, sort_keys=True))
    print(json.dumps({k: v for k, v in rec.items() if k != "key"}))
    return 0 if rec.get("status") in ("SKIP", "APPLIED", "DRY-OK") or rec.get("status") in STRUCTURAL else 1       # a structural stop is handled (NEEDS-LANE posted): exit 0; 1 = a crash


if __name__ == "__main__":
    sys.exit(main())
