"""Flow / version state of every element (owner 2026-10-12): which physical flow its closure came from, so the explorer
can show how many die-used elements are on the CURRENT flow (tools/ref_tile at the M5 tile layer cap).

  closed_m5   closed . ref_tile M5 (current)   closed record is a ref_tile job whose kit routes at the M5 cap
  closed_m6   closed . ref_tile (M6)            ref_tile kit generated before the cap (legacy_layer_kits.json / RLAYERS M6)
  closed_legacy closed . legacy flow            closed record is a hand-rolled (non ref_tile) route
  inflight    re-route in flight (M5)           a live ref_tile M5 job of the block, or a submitted, unfinished
                                                tools/ref_tile/reroute_batch.py re-route (reroute_m5_state.json)
  open        open                              not closed
  superseded  superseded                        superseded_elements.json / registry category
  fallback    fallback (not used)               HBM central-VM fallback track (hfd_vm_*, vm_cp_*, ot_hgi_vm_unit, hfd_hgi_vm)

Die-used = the element (or a variant / job block of it) is a cell of a die contract (results/arch/hier_contract_1011/
*.json slots) or a Qwen die-master cfg --macro-view; read from origin/main (the shared checkout can lag).  Same rules as
tools/ref_tile/reroute_batch.py.  Everything here is cached: kit layers per (commit, kit), contracts per origin/main sha.
"""
import glob
import json
import os
import pathlib
import re
import subprocess
import time

VM_FALLBACK = re.compile(r"^(hfd_vm_|hfd_vm$|vm_cp_|ot_hgi_vm_unit|ot_vm_cp|hfd_hgi_vm$)")
KIT_RE = re.compile(r"ref_route\.sh\s+physical/ref_tile/([a-z0-9_]+)/kit\.env")
LABELS = {"closed_m5": "closed · ref_tile M5 (current)", "closed_m6": "closed · ref_tile (M6)",
          "closed_legacy": "closed · legacy flow", "inflight": "re-route in flight (M5)", "open": "open",
          "superseded": "superseded", "fallback": "fallback (not used)"}
ORDER = ["closed_m5", "inflight", "closed_m6", "closed_legacy", "open", "superseded", "fallback"]
HIDDEN = {"superseded", "fallback"}
LIVE = {"QUEUED", "SYNC", "READY", "RUNNING", "ECO", "MIGRATING", "SMOKE_OK"}
STATE_REL = "results/arch/hier_contract_1011/reroute_m5_state.json"


def kit_of(route_cmd):
    m = KIT_RE.search(route_cmd or "")
    return m.group(1) if m else None


class FlowState:
    def __init__(self, repo, log=None):
        self.repo = pathlib.Path(repo)
        self.log = log or (lambda *_: None)
        self.kits = {}          # (commit, kit) -> "M5" | "M6"
        self.used_key = None
        self.used = set()
        self.legacy = {}
        self.state_key = None
        self.state = {}

    def git(self, *a, timeout=30):
        try:
            r = subprocess.run(["git", "-C", str(self.repo), *a], capture_output=True, text=True, timeout=timeout)
            return r.stdout if r.returncode == 0 else None
        except Exception:  # noqa: BLE001
            return None

    # ---- die-used cells (origin/main)
    def refresh_used(self):
        sha = (self.git("rev-parse", "origin/main") or "").strip()
        if not sha or sha == self.used_key:
            return
        used = set()
        names = (self.git("ls-tree", "--name-only", sha, "results/arch/hier_contract_1011/") or "").split()
        for p in names:
            if not p.endswith(".json"):
                continue
            t = self.git("show", f"{sha}:{p}", timeout=60)
            try:
                d = json.loads(t or "")
            except ValueError:
                continue
            if not (isinstance(d, dict) and str(d.get("schema", "")).startswith("opentallas.hier_contract")
                    and isinstance(d.get("slots"), list)):
                continue
            used |= {s.get("cell") for s in d["slots"] if isinstance(s, dict) and s.get("kind") != "die" and s.get("cell")}
        for p in (self.git("ls-tree", "--name-only", sha, "physical/qwen_die_masters/cfg/") or "").split():
            if p.endswith(".env"):
                used |= set(re.findall(r"--macro-view\s+'?([A-Za-z0-9_]+)=", self.git("show", f"{sha}:{p}") or ""))
        try:
            self.legacy = json.loads(self.git("show", f"{sha}:tools/ref_tile/legacy_layer_kits.json") or "{}").get("kits", {})
        except ValueError:
            pass
        self.used, self.used_key = used, sha

    def kit_cap(self, commit, kit):
        k = (commit or "", kit)
        if k not in self.kits:
            env = self.git("show", f"{commit}:physical/ref_tile/{kit}/kit.env") if commit else None
            m = re.search(r"^RLAYERS='?M\d+\s+(M\d+)", env or "", re.M)
            self.kits[k] = m.group(1) if m else ("M6" if kit in self.legacy else "M5")
        return self.kits[k]

    # ---- reroute_batch.py state (newest of: env, the batch worktree, the repo checkout, origin/main)
    def refresh_state(self):
        cands = [os.environ.get("FLEET_VIZ_REROUTE_STATE"), "/home/ubuntu/wt/el1011-reroute-m5/" + STATE_REL,
                 str(self.repo / STATE_REL)]
        best = None
        for c in cands:
            if c and os.path.exists(c):
                mt = os.path.getmtime(c)
                if not best or mt > best[1]:
                    best = (c, mt)
        if best:
            if best != self.state_key:
                try:
                    self.state = json.loads(pathlib.Path(best[0]).read_text()).get("tiles", {})
                    self.state_key = best
                except Exception as e:  # noqa: BLE001
                    self.log("flow: reroute state %s: %s" % (best[0], e))
            return
        key = ("git", self.used_key)
        if key != self.state_key:
            try:
                self.state = json.loads(self.git("show", f"origin/main:{STATE_REL}") or "{}").get("tiles", {})
            except ValueError:
                self.state = {}
            self.state_key = key

    # ---- per element
    def classify(self, r, g):
        """r: elements row, g: its reduced jobs.  Sets r['flow'], r['flow_label'], r['flow_detail'], r['die_used'],
        r['m5_reroute']."""
        names = [r["element"]] + list(r.get("variants") or [])
        blocks = set(names) | {j["block"] for j in g}
        r["die_used"] = bool(blocks & self.used)
        # an element can own several re-routed tiles (variants / job blocks): keep each tile's own M5 state
        # (r['m5_by_block']) and use the element's own tile, else its first variant's, for the element badge
        order = names + sorted(blocks - set(names))
        tiles = [(b, self.state[b]) for b in order if b in self.state]
        keys = ("state", "job", "kit", "closed_job", "gate", "priority", "reason", "compare", "submitted_at")
        r["m5_by_block"] = {b: {k: t.get(k) for k in keys} for b, t in tiles}
        tile = tiles[0][1] if tiles else None
        r["m5_reroute"] = r["m5_by_block"][tiles[0][0]] if tiles else None
        live_m5 = [j for j in g if j["status"] in LIVE and j.get("ref_tile") and j.get("kit")
                   and self.kit_cap(j.get("source_commit"), j["kit"]) == "M5"]
        byname = {j["name"]: j for j in g}
        live_tiles = [t for _, t in tiles if t.get("state") == "submitted" and
                      (byname.get(t.get("job")) or {}).get("status", "QUEUED") in LIVE | {None, "QUEUED"}
                      and not (t.get("compare") or {}).get("final")]
        sub_live = bool(live_tiles)
        if live_tiles:
            tile = live_tiles[0]
        closed_flow, detail = None, ""
        if str(r.get("category", "")).startswith("closed"):
            bj = byname.get((r.get("best") or {}).get("job") or "")
            if not bj:
                cl = sorted((j for j in g if j["status"] == "CLOSED"), key=lambda j: j.get("closed_t") or 0)
                bj = cl[-1] if cl else None
            if bj and bj.get("ref_tile") and bj.get("kit"):
                cap = self.kit_cap(bj.get("source_commit"), bj["kit"])
                closed_flow = "closed_m5" if cap == "M5" else "closed_m6"
                detail = "%s kit %s (%s)" % (bj["name"], bj["kit"], cap)
            else:
                closed_flow = "closed_legacy"
                detail = (bj or {}).get("name") or "closed outside the loop"
        if r.get("category") == "superseded":
            f = "superseded"
        elif any(VM_FALLBACK.search(b) for b in names):
            f = "fallback"
        elif live_m5 or sub_live:
            f = "inflight"
            detail = ", ".join(j["name"] for j in live_m5) or tile.get("job") or ""
            if closed_flow:
                detail += " (was %s)" % LABELS[closed_flow]
        elif closed_flow:
            f = closed_flow
        else:
            f = "open"
        r["flow"], r["flow_label"], r["flow_detail"] = f, LABELS[f], detail
        return f

    def summary(self, rows, targets):
        out = {}
        for t in targets:
            die = {k: 0 for k in ORDER}
            allc = {k: 0 for k in ORDER}
            for r in rows:
                if r.get("target") != t:
                    continue
                allc[r["flow"]] += 1
                if r.get("die_used"):
                    die[r["flow"]] += 1
            if sum(allc.values()):
                out[t] = {"die_used": die, "all": allc}
        return out

    def annotate(self, rows, groups, targets):
        t0 = time.time()
        try:
            self.refresh_used()
            self.refresh_state()
        except Exception as e:  # noqa: BLE001
            self.log("flow: refresh: %s" % e)
        for r in rows:
            try:
                self.classify(r, groups.get(r["element"], []))
            except Exception as e:  # noqa: BLE001
                r["flow"], r["flow_label"], r["flow_detail"] = "open", LABELS["open"], "flow error: %s" % e
                r.setdefault("die_used", False)
        s = self.summary(rows, targets)
        return dict(summary=s, labels=LABELS, order=ORDER, hidden=sorted(HIDDEN), current="closed_m5",
                    used_from=self.used_key, n_used_cells=len(self.used), secs=round(time.time() - t0, 2))
