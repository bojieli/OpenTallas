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

TOOL_PATHS = ("tools", "physical/common_flow")
SM = str(HERE / "src_manifest.py")
STATE_REL = "tools_refresh_state.json"


MAX_CRASHES = 3


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


def patch_ops(die, d, old_tree, new_tree, manifest_hash):
    """the kit_wave_edit JSON patch that switches the die to the new tree: src, src_manifest_hash, every die key naming the old tree repointed, old tree queued"""
    ops = [{"op": "replace", "path": f"/dies/{die}/src", "value": new_tree}]
    if d.get("src_manifest_hash") is not None:
        ops.append({"op": "replace", "path": f"/dies/{die}/src_manifest_hash", "value": manifest_hash})
    else:
        ops.append({"op": "add", "path": f"/dies/{die}/src_manifest_hash", "value": manifest_hash})
    for k, v in d.items():
        if k in ("src", "src_manifest_hash", "superseded_trees", "hold_records"):
            continue
        nv = repoint(v, old_tree, new_tree)
        if nv != v:
            ops.append({"op": "replace", "path": f"/dies/{die}/{k}", "value": nv})
    ops.append({"op": "add", "path": f"/dies/{die}/superseded_trees" + ("/-" if d.get("superseded_trees") else ""),
                "value": old_tree if d.get("superseded_trees") else [old_tree]})
    return ops


class Ops:
    """the real steps: ssh to the die's gen host, run src_manifest there; each returns (ok, detail)"""

    def __init__(self, d, repo, main_sha, run=None):
        self.d, self.repo, self.sha = d, repo, main_sha
        self.overlay_report = {}
        self.run = run or self._run
        self.host = d.get("gen_host") or (d.get("gen_hosts") or [None])[0]

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
        rc, out = self.run(None, self.pack_cmd(old, new, drop))
        if rc:
            return False, f"delta-make (hub): rc {rc}: {out[-400:]}", ""
        for c in self.compose_cmds(old, new):
            rc, out = self.run(self.host, c)
            if rc:
                return False, f"{c.split()[3] if len(c.split()) > 3 else c}: rc {rc}: {out[-400:]}", ""
        self.run(self.host, f"rm -rf {shlex.quote(new + '.pack')}")
        rc, h = self.run(self.host, f"cat {shlex.quote(new)}/.src-manifest.sha256")
        return rc == 0, "composed", h.strip()

    def guard(self, new, manifest_hash):
        hosts = ",".join(self.d.get("gen_hosts") or [self.host])
        rc, out = self.run(None, f"python3 -I {shlex.quote(SM)} hosts {shlex.quote(new)} --hosts {shlex.quote(hosts)} --expect {shlex.quote(manifest_hash)}")
        if rc:
            return False, "guard hosts verify: " + out[-300:]
        rc, out = self.run(self.host, f"python3 -I {shlex.quote(SM)} links {shlex.quote(new)}")
        return rc == 0, "guard ok" if rc == 0 else "guard links: " + out[-300:]

    def bind_cmd(self, new, out):
        kr = self.d.get("kit_rtl") or {}
        tpl = self.d.get("tools_refresh_bind_cmd") or kr.get("prep_cmd") or \
            "python3 tools/die_plan/bind.py bind {plan} --out {out} --asbuilt {asbuilt} --strict"
        return f"cd {shlex.quote(new)} && " + tpl.format(plan=self.d.get("plan", "").replace(self.d.get("src", ""), new), out=out,
                                                        bind=out, asbuilt=(kr.get("asbuilt") or "").replace(self.d.get("src", ""), new), tree=new)

    def bind(self, new):
        """strict bind with the new tree's tools into a scratch dir; unchanged = native_topology.json equals the bind of record"""
        kr = self.d.get("kit_rtl") or {}
        record = (kr.get("bind_out") or "").rstrip("/")
        if not record:
            return False, False, "no kit_rtl.bind_out of record: cannot compare"
        out = f"{new}.bindcheck"
        rc, txt = self.run(self.host, self.bind_cmd(new, out))
        if rc:
            return False, False, "strict bind failed: " + txt[-300:]
        rc, got = self.run(self.host, f"sha256sum {shlex.quote(out)}/native_topology.json {shlex.quote(record)}/native_topology.json | awk '{{print $1}}'")
        shas = got.split()
        self.run(self.host, f"rm -rf {shlex.quote(out)}")
        if rc or len(shas) != 2:
            return False, False, "native_topology.json hash unreadable: " + got[-200:]
        return True, shas[0] == shas[1], "bind native_topology unchanged" if shas[0] == shas[1] else "bind native_topology CHANGED"


def refresh(die, d, lag, main_sha, ops, state, post, edit, dry=False, now=time.time):
    """one refresh pass -> record dict (status: SKIP | GUARD-FAIL | BIND-FAIL | BIND-CHANGED | COMPOSE-FAIL | DRY-OK | APPLIED | APPLY-FAIL); stored in state['done'][key]"""
    key = refresh_key(die, lag, main_sha)
    d = dict(d, _die=die)
    ok, why = should_refresh(d, lag, state, key)
    if not ok:
        return dict(status="SKIP", why=why)
    old = d["src"]
    new = new_tree_path(old, main_sha)
    rec = dict(key=key, old=old, new=new, missing=lag["missing"], ts=int(now()), owner=d.get("owner_lane", ""))
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
        edit(die, patch_ops(die, d, old, new, h), f"TOOLS-REFRESH {die}: tools-only tree {os.path.basename(new)} (rulings {', '.join(lag['missing'][:12])}); guard + strict bind unchanged")
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
        post(f"NEEDS-LANE [TOOLS-REFRESH -> {d.get('owner_lane') or die}] {die}: tools_refresh crashed {n} times for these rulings ({why}); "
             f"stopped, no more automatic passes for this pin and rulings")
    return dict(status="CRASH", why=why, crashes=n)


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
    return 0 if rec.get("status") in ("SKIP", "APPLIED", "DRY-OK") else 1


if __name__ == "__main__":
    sys.exit(main())
