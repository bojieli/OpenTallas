#!/usr/bin/env python3
"""M5 re-route batch (owner 2026-10-12): re-route every die-used closed tile through tools/ref_tile at the M5 layer cap.

  plan     (default, dry-run) inventory + classification, writes nothing but the state file's "plan" section
  run      generate kits for the selected tiles, local + remote pre-route gate (spread over the fleet via ot-heavy),
           commit + push the kits, generate job specs at that commit, commit + push, drop them into the loop intake
  status   counts from the state file
  compare  for every submitted tile whose M5 job finished: GRT overflow, DRT iterations / final violations, TT / FF
           slack and route runtime next to the previous closure's; flags a worse M5 route (GRT overflow > 0, DRT not
           converging, TT or FF slack down > 20 ps, or not CLOSED); a flagged pin-dense edge tile gets an M6
           layer_cap_grant proposal in its die lead's log (no M5 iteration)

Selection (one pass, deterministic):
  used cells   = every cell placed by a die contract (results/arch/hier_contract_1011/{qwen_rom,qwen_kv,s81,r25gq}.json
                 and any newer *.json contract with "slots"), plus hard children of placed clusters (contract slots whose
                 parent is a cluster slot), plus Qwen die-master cfg --macro-view children (blocked_pin_sweep.parent_index)
  excluded     superseded/withdrawn (claude-takeover superseded_elements.json); HBM central-VM fallback track (hfd_vm_*,
               vm_cp_* / make_vm_cp.py specs, ot_hgi_vm_unit); B2-changed HBM units (results/arch/hbm_b2_1012/SPEC.md
               section 6); Qwen TP8 PARAMETER CHANGE / REDESIGN / REMOVED elements (results/arch/qwen_tp8_1012/
               element_impact.json); clusters / hard IP / die-layer slots (contract layer_rule != tile_m5: clusters are
               re-assembled after their children); any cell with a live loop job or a pending intake spec
  record       the latest CLOSED closure-loop record of the cell (daemon job state or the closed archive); already a
               ref_tile M5 closure (ref_tile kit not frozen in legacy_layer_kits.json) -> skipped
  spec         from the closed record, flow-agnostic: ORFS config.mk (DESIGN_NAME, VERILOG_FILES, VERILOG_TOP_PARAMS,
               VERILOG_DEFINES, VERILOG_INCLUDE_DIRS, ADDITIONAL_LEFS -> macro views, DIE_AREA), the exported view LEF
               (outline, every signal pin's face = its pin plan), the SDC clock port, the record's benches (same
               PASS/FAIL regexes); RTL / bench files that changed on HEAD since the closed commit are snapshotted into
               the kit (src/) and every bench runs on an overlay of that snapshot.  No pg_layer, no host list: the kit
               gets the ref_tile default layer cap M5 (pins M4/M5) and the loop places the job.
  contract     the cell's slots get their pins / clock entry moved off M6+ (M6 -> M4, M7 -> M5, same face/offset)
Priority: (1) tier 1 of m5_reroute_priority.json (congested die regions), (2) high instance count (>= 4 die slots),
          (3) child_lint (c)/(f) failure of the closed view (blocked_pin_sweep_all.json), (4) the rest.
State: results/arch/hier_contract_1011/reroute_m5_state.json (idempotent, resumable; a submitted cell is never
re-submitted).  Log: one line per tile in its owner's /home/ubuntu/claude-takeover-20261007/el1011-<tag>.log
(el1011-reroute-m5.log when the owner has no el1011 log).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/ref_tile"))
sys.path.insert(0, str(ROOT / "tools/hier_contract"))
import child_lint  # noqa: E402

HC = ROOT / "results/arch/hier_contract_1011"
STATE = HC / "reroute_m5_state.json"
TAKE = Path("/home/ubuntu/claude-takeover-20261007")
JOBS = Path.home() / ".local/state/closure_loop/jobs"
ARCHIVE = Path("/home/ubuntu/closed_archive")
INTAKE = Path("/tmp/claude-review-20261003/closure_jobs")
SPECS = ROOT / "tools/ref_tile/specs_m5rr"
CACHE = Path(os.environ.get("TMPDIR", "/tmp")) / "reroute_m5_cache"
LEGACY = json.loads((ROOT / "tools/ref_tile/legacy_layer_kits.json").read_text())["kits"]
HOSTS = ["ot-epyc1tb", "ot-epyc4", "ot-agidock128", "ot-pve1"]
HEADROOM = {"ot-epyc1tb": 128, "ot-epyc4": 48, "ot-agidock128": 24, "ot-pve1": 32}
TERMINAL = {"CLOSED", "CANCELLED", "NEEDS_RTL", "NEEDS_HUMAN", "REFUSED", "INVALID", "FLOORPLAN_MARGIN",
            "PREROUTE_MARGIN"}
OWNER = "Claude:el1011-reroute-m5"
BRANCH = "claude/el1011-reroute-m5"
SSH = ["ssh", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes"]
VM_FALLBACK = re.compile(r"^(hfd_vm_|hfd_vm$|vm_cp_|ot_hgi_vm_unit|ot_vm_cp|hfd_hgi_vm$)")
# B2 contract v9 delta (SPEC.md section 6): VM slices/banks/ring/star/lane groups new; lgE/lgW stations removed;
# cmdproc / quant / hc_eng / coll / idx / DMA re-faced or re-terminated; vmw/vmr2 DMA paths removed
B2_CHANGED = re.compile(r"^(hfd_hgi_vms?|ot_vms_|ot_hgi_vm_|hfd_stn_lg[EW]|hb_stn_lg|hfd_cmdproc|ot_hgi_cp|ot_hgi_cmdproc|"
                        r"hfd_quant|ot_hgi_quant|hfd_hc_eng|ot_hgi_hc_eng|hfd_coll$|ot_hgi_coll$|hfd_hgi_idx|"
                        r"ot_hgi_idx_(unit|index)|hfd_dma|ot_hgi_dma|hgi_vmw|hgi_vmr2|ot_hgi_lane(chain|station|arb))")
MEMORY = re.compile(r"^ot_(sram|rom)_\d")
LOCK = threading.Lock()


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def git(*a, check=True) -> str:
    r = subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()[-400:]}")
    return r.stdout


def jload(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except Exception:  # noqa: BLE001
        return default


# ------------------------------------------------------------------------------------------------------ inventory
def contracts() -> list[dict]:
    out = []
    for f in sorted(HC.glob("*.json")):
        d = jload(f, {})
        if isinstance(d, dict) and isinstance(d.get("slots"), list) and d.get("schema", "").startswith(
                "opentallas.hier_contract"):
            out.append((f, d))
    return out


def used_cells() -> dict:
    """cell -> {slots: [(file, slot)], dies, rule (contract layer_rule), count}"""
    cells: dict[str, dict] = {}
    for f, d in contracts():
        names = {s.get("name"): s for s in d["slots"]}
        for s in d["slots"]:
            if s.get("kind") == "die" or not s.get("cell"):
                continue
            c = cells.setdefault(s["cell"], {"slots": [], "dies": set(), "rules": set(), "count": 0, "cluster": False})
            c["slots"].append((f.name, s["name"]))
            c["dies"].add(d.get("die"))
            c["rules"].add(s.get("layer_rule") or "")
            c["count"] += 1
            if re.search(r"hardened_cluster|two_level", str(s.get("notes", ""))) or \
                    any(x.get("parent") == s["name"] for x in d["slots"]):
                c["cluster"] = True
            par = names.get(s.get("parent"))
            if par is not None and par.get("kind") != "die":
                c["dies"].add(f"child of {par.get('cell')}")
    for f in glob.glob(str(ROOT / "physical/qwen_die_masters/cfg/*.env")):
        t = Path(f).read_text(errors="replace")
        for cell in re.findall(r"--macro-view\s+'?([A-Za-z0-9_]+)=", t):
            c = cells.setdefault(cell, {"slots": [], "dies": set(), "rules": set(), "count": 0, "cluster": False})
            c["dies"].add("cfg:" + Path(f).stem)
            c["count"] += 1
    return cells


def tp8_excluded() -> list[str]:
    d = jload(ROOT / "results/arch/qwen_tp8_1012/element_impact.json", {})
    pats = []
    for e in d.get("elements", []):
        if not re.search(r"PARAMETER|REDESIGN|REMOVED", e.get("cls", "")) or e.get("cls", "").startswith("REMOVED (B), REUSE"):
            continue
        for tok in re.split(r"[\s/(),]+", e["element"]):
            if re.fullmatch(r"[A-Za-z0-9_*]+", tok) and ("_" in tok):
                pats.append(tok)
    return pats


def exclusions() -> dict:
    sup = jload(TAKE / "superseded_elements.json", {}) or {}
    return {"superseded": set(sup) if isinstance(sup, dict) else set(sup), "tp8": tp8_excluded()}


def records() -> tuple[dict, dict, set]:
    """closed records by block (latest last), live job names by block, pending intake blocks"""
    closed, live, names = {}, {}, set()
    for f in JOBS.glob("*.json"):
        j = jload(f)
        if not isinstance(j, dict) or not isinstance(j.get("spec"), dict):
            continue
        names.add(j.get("name"))
        b = j["spec"].get("block")
        if j.get("status") == "CLOSED":
            closed.setdefault(b, []).append({"job": j["name"], "when": j.get("updated") or "", "spec": j["spec"],
                                             "host": j.get("host"), "run": j.get("run"), "archive": None,
                                             "commit": j.get("commit_full") or j["spec"].get("source", {}).get("commit")})
        elif j.get("status") not in TERMINAL and not str(j.get("status", "")).startswith("EARLY_FAIL"):
            live.setdefault(b, []).append(j["name"])
    by_job = {}
    for d in ARCHIVE.glob("*/*"):
        by_job[d.name] = d
        man = jload(d / "manifest.json")
        if not man or not str((man.get("metrics") or {}).get("reason", "")).startswith("CLOSED"):
            continue
        spec = jload(d / "spec.json", {})
        b = man.get("block") or spec.get("block")
        job = man.get("job") or d.name
        lst = closed.setdefault(b, [])
        hit = next((r for r in lst if r["job"] == job), None)
        if hit:
            hit["archive"] = str(d)
        else:
            lst.append({"job": job, "when": man.get("closed_at") or "", "spec": spec, "host": None, "run": None,
                        "archive": str(d), "commit": man.get("commit") or (spec.get("source") or {}).get("commit")})
    for v in closed.values():
        for r in v:
            if not r["archive"] and r["job"] in by_job:
                r["archive"] = str(by_job[r["job"]])
        v.sort(key=lambda r: r["when"])
    pending = set()
    if INTAKE.is_dir():
        for f in INTAKE.glob("*.json"):
            if f.stem in names:
                continue
            s = jload(f)
            if isinstance(s, dict) and s.get("block"):
                pending.add(s["block"])
    return closed, live, pending


def kit_of(spec: dict) -> str | None:
    m = re.search(r"ref_route\.sh\s+physical/ref_tile/([a-z0-9_]+)/kit\.env", json.dumps(spec.get("stages", {})))
    return m.group(1) if m else None


def lint_fails() -> set:
    d = jload(HC / "blocked_pin_sweep_all.json", {}) or {}
    return {r["job"] for r in d.get("records", []) if r.get("c_fail") or r.get("f_fail")}


def plan() -> dict:
    cells = used_cells()
    ex = exclusions()
    closed, live, pending = records()
    pri = {b["block"]: b for b in (jload(HC / "m5_reroute_priority.json", {}) or {}).get("blocks", [])}
    lf = lint_fails()
    rows = []
    for cell, c in sorted(cells.items()):
        row = {"cell": cell, "slots": c["count"], "dies": sorted(x for x in c["dies"] if x)}
        recs = closed.get(cell, [])
        rec = recs[-1] if recs else None
        spec = rec["spec"] if rec else {}
        purpose = json.dumps(spec)[:20000] if spec else ""
        reason = None
        if cell in ex["superseded"]:
            reason = "superseded"
        elif VM_FALLBACK.search(cell) or "make_vm_cp" in purpose:
            reason = "fallback (central VM, not used)"
        elif B2_CHANGED.search(cell):
            reason = "B2-changed HBM unit (redesigned)"
        elif any(fnmatch.fnmatch(cell, p) for p in ex["tp8"]):
            reason = "Qwen TP8 parameter change / redesign"
        elif MEMORY.search(cell):
            reason = "memory macro (hard IP)"
        elif c["cluster"]:
            reason = "cluster (re-assembled after its children)"
        elif c["rules"] & {"hard_ip", "die_layer"}:
            reason = f"contract rule {'/'.join(sorted(c['rules'] & {'hard_ip', 'die_layer'}))} (not a M5 tile)"
        elif cell in live or cell in pending:
            reason = "live job"
            row["live"] = live.get(cell, ["(intake)"])
        elif not rec:
            reason = "no closed record"
        elif spec.get("ref_tile") and kit_of(spec) and kit_of(spec) not in LEGACY:
            reason = "already ref_tile M5"
        if rec:
            row.update(job=rec["job"], closed_at=rec["when"], commit=(rec["commit"] or "")[:12],
                       owner=spec.get("owner"), ref_tile=bool(spec.get("ref_tile")))
        p = pri.get(cell)
        row["priority"] = 1 if p and p.get("tier") == 1 else 2 if c["count"] >= 4 else \
            3 if rec and rec["job"] in lf else 4
        if p:
            row["rank"] = p.get("rank")
        row["state"] = "skip" if reason else "eligible"
        if reason:
            row["reason"] = reason
        rows.append(row)
    for b, p in pri.items():
        if b not in cells:
            rows.append({"cell": b, "slots": 0, "dies": [], "priority": 9, "rank": p.get("rank"), "state": "skip",
                         "reason": "not placed by a die contract (priority list by name prefix)"})
    rows.sort(key=lambda r: (r["priority"], r.get("rank") or 9999, -r["slots"], r["cell"]))
    return {"rows": rows, "closed": closed}


# ------------------------------------------------------------------------------------------------------ fetch
def ssh(host: str, cmd: str, timeout=180) -> str:
    r = subprocess.run(SSH + [host, cmd], capture_output=True, text=True, timeout=timeout)
    return r.stdout if r.returncode == 0 else ""


def fetch(rec: dict, block: str) -> dict:
    """config.mk text, view LEF text, macro instance counts from the closed record (archive first, then the run host)"""
    cdir = CACHE / rec["job"]
    cdir.mkdir(parents=True, exist_ok=True)
    out = {}
    if (cdir / "fetched.json").exists():
        return json.loads((cdir / "fetched.json").read_text())
    cfg = lef = net = ""
    if rec.get("archive"):
        a = Path(rec["archive"])
        cfgs = [p for p in a.glob("run/routes/*/work/orfs/config.mk") if not p.parent.parent.parent.name.endswith("_cal")]
        cfgs += list(a.glob("run/routes/*/physical_artifacts/config.mk"))
        cfg = cfgs[0].read_text(errors="replace") if cfgs else ""
        lefs = [p for p in [a / "final" / f"{block}.lef", a / "final" / f"{block}.lef.zst",
                            *sorted((a / "final").glob("*.lef")), *sorted((a / "final").glob("*.lef.zst")),
                            *sorted(a.glob("run/routes/*/view/*.lef")), *sorted(a.glob("run/record/**/*.lef"))]
                if p.exists() and "_bloat" not in p.name and "/macros/" not in str(p)]
        lef = (subprocess.run(["zstd", "-dcf", str(lefs[0])], capture_output=True).stdout.decode(errors="replace")
               if lefs and lefs[0].name.endswith(".zst") else lefs[0].read_text(errors="replace") if lefs else "")
        net = next((str(x) for x in (a / "final/6_final.v", a / "final/6_final.v.zst") if x.exists()), "")
    if (not cfg or not lef) and rec.get("host") and rec.get("run"):
        run = rec["run"]
        if not cfg:
            cfg = ssh(rec["host"], f"for f in {run}/routes/*/work/orfs/config.mk {run}/routes/*/physical_artifacts/config.mk "
                                   f"{run}/route/*/work/orfs/config.mk; do case $f in *_cal/*) continue;; esac; "
                                   f"[ -f $f ] && cat $f && break; done")
        if not lef:
            p = ssh(rec["host"], f"find {run}/record -name '*.lef' 2>/dev/null | grep -v -e _bloat -e /macros/ | head -20").split()
            pick = next((x for x in p if Path(x).stem == block), p[0] if p else None)
            lef = ssh(rec["host"], f"cat {pick}") if pick else ""
    if not lef:
        for r in (rec["spec"].get("record") or []):
            to = r.get("to") if isinstance(r, dict) else None
            if to and (ROOT / to).is_dir():
                hits = [h for h in sorted((ROOT / to).rglob("*.lef")) if "_bloat" not in h.name and "/macros/" not in str(h)]
                pick = next((h for h in hits if h.stem == block), hits[0] if hits else None)
                if pick:
                    lef = pick.read_text(errors="replace")
                    break
    out["cfg"], out["lef"] = cfg, lef
    masters = [Path(x).stem for x in mk(cfg).get("ADDITIONAL_LEFS", "").split()]
    counts = {}
    if masters:
        pat = "|".join(re.escape(m) for m in masters)
        if net:
            t = (subprocess.run(["zstd", "-dcf", net], capture_output=True).stdout.decode(errors="replace")
                 if net.endswith(".zst") else Path(net).read_text(errors="replace"))
            for m in masters:
                counts[m] = len(re.findall(rf"(?m)^\s*{re.escape(m)}\s", t))
        elif rec.get("host") and rec.get("run"):
            o = ssh(rec["host"], f"f=$(ls {rec['run']}/routes/*/work/orfs/results/asap7/*/base/6_final.v "
                                 f"{rec['run']}/routes/*/physical_artifacts/6_final.v 2>/dev/null | grep -v _cal/ | head -1); "
                                 f"[ -n \"$f\" ] && grep -oE '^\\s*({pat})\\s' $f | sort | uniq -c")
            for line in o.splitlines():
                n, m = line.split()[:2]
                counts[m] = int(n)
    out["macro_counts"] = counts
    if cfg and lef and all(counts.get(m) for m in masters):
        (cdir / "fetched.json").write_text(json.dumps(out))
    return out


def mk(cfg: str) -> dict:
    v = {}
    for line in cfg.splitlines():
        m = re.match(r"\s*(?:override\s+)?export\s+([A-Z_0-9]+)\s*\??=\s*(.*)$", line)
        if m:
            v[m.group(1)] = m.group(2).strip()
    return v


# ------------------------------------------------------------------------------------------------------ spec
def kit_name(cell: str) -> str:
    n = re.sub(r"[^a-z0-9_]", "_", cell.lower()).strip("_")
    return (n[:40] + "_m5").strip("_")


def repo_path(p: str) -> str | None:
    p = p.strip()
    for pre in ("/src/", str(ROOT) + "/"):
        if p.startswith(pre):
            return p[len(pre):]
    return None if p.startswith("/") else p


def changed(commit: str, path: str) -> bool:
    a = subprocess.run(["git", "-C", str(ROOT), "rev-parse", f"{commit}:{path}"], capture_output=True, text=True)
    b = subprocess.run(["git", "-C", str(ROOT), "rev-parse", f"HEAD:{path}"], capture_output=True, text=True)
    if a.returncode:
        raise SpecSkip(f"{path} not in the closed commit {commit[:9]}")
    return b.returncode != 0 or a.stdout != b.stdout


class SpecSkip(Exception):
    pass


def build_spec(row: dict, rec: dict, f: dict) -> dict:
    cell, commit = row["cell"], rec["commit"]
    if not commit:
        raise SpecSkip("closed record has no source commit")
    if git("cat-file", "-t", commit, check=False).strip() != "commit":
        raise SpecSkip(f"closed commit {commit[:9]} not in the repo")
    v = mk(f["cfg"])
    if not v.get("DESIGN_NAME") or not v.get("VERILOG_FILES"):
        raise SpecSkip("no ORFS config.mk in the closed record (archive / run host)")
    if not f["lef"]:
        raise SpecSkip("no exported view LEF in the closed record")
    name = kit_name(cell)
    kd = f"physical/ref_tile/{name}"
    srcs, snap = [], []
    for p in v["VERILOG_FILES"].split():
        rp = repo_path(p)
        if rp is None or rp.startswith((".views/", "work/")):
            raise SpecSkip(f"generated source {p} (not in the repo)")
        srcs.append(rp)
    macros = []
    for lp in v.get("ADDITIONAL_LEFS", "").split():
        rp = repo_path(lp)
        if rp is None:
            raise SpecSkip(f"macro view {lp} outside the repo")
        view = str(Path(rp).parent)
        m = Path(rp).stem
        if not MEMORY.search(m):
            raise SpecSkip(f"has hard child {m} (a cluster: re-assembled after its children)")
        if not (ROOT / view / f"{m}.lef").exists():
            raise SpecSkip(f"macro view dir {view} lacks {m}.lef at HEAD")
        if not all((ROOT / view / f"{m}_{c}.lib").exists() for c in ("ss", "ff", "tt")):
            raise SpecSkip(f"macro view {view} lacks {m}_{{ss,ff,tt}}.lib")
        n = f["macro_counts"].get(m, 0)
        if n <= 0:
            raise SpecSkip(f"macro {m}: instance count unknown")
        macros.append({"view": view, "count": n})
    for s in srcs:
        if changed(commit, s):
            snap.append(s)
    lef = child_lint.parse_lef(f["lef"], v["DESIGN_NAME"])
    faces: dict[str, dict[str, int]] = {}
    for pn, p in lef["pins"].items():
        if child_lint.is_pg(pn, p):
            continue
        base = re.sub(r"\[\d+\]$", "", pn)
        for r in p["rects"]:
            fc = child_lint.face_of(r, lef["W"], lef["H"])
            if fc:
                faces.setdefault(base, {}).setdefault(fc, 0)
                faces[base][fc] += 1
                break
        else:
            faces.setdefault(base, {}).setdefault("ANY", 0)
    pins: dict[str, list] = {}
    for base, fc in sorted(faces.items()):
        pins.setdefault(max(fc, key=lambda k: (fc[k], k)), []).append(base)
    sdc = ""
    for p in [Path(rec["archive"] or "/nonexistent")]:
        hits = list(p.glob("final/6_final.sdc"))
        sdc = hits[0].read_text(errors="replace") if hits else ""
    m = re.search(r"create_clock[^\n]*get_ports\s+\{?\s*([A-Za-z0-9_]+)", sdc)
    clk = m.group(1) if m else next((c for c in ("clk", "ck", "clk_i", "i_clk", "core_clk") if c in faces), None)
    if not clk:
        raise SpecSkip("clock port not found (SDC / clk / ck)")
    rst = [b for b in faces if re.fullmatch(r"(rst|rst_n|rstn|reset|reset_n|arst_n|rst_ni|srst)", b)]
    params = {}
    tp = v.get("VERILOG_TOP_PARAMS", "").split()
    for i in range(0, len(tp) - 1, 2):
        params[tp[i]] = int(tp[i + 1]) if re.fullmatch(r"-?\d+", tp[i + 1]) else tp[i + 1]
    defines = [d[2:] for d in v.get("VERILOG_DEFINES", "").split() if d.startswith("-D") and d != "-DSYNTHESIS"]
    orfs_vars = {}
    if v.get("VERILOG_INCLUDE_DIRS"):
        inc = [repo_path(x) for x in v["VERILOG_INCLUDE_DIRS"].split()]
        if any(x is None for x in inc):
            raise SpecSkip("include dirs outside the repo")
        orfs_vars["VERILOG_INCLUDE_DIRS"] = " ".join(inc)
    # the closed die-view routes (route_view.sh) ran two things the ref_tile kit must carry: the POST_SYNTH inout retype
    # by default (an unbuffered inout stops the post-GRT repair with RSZ-0074 and breaks CTS latency: hfd_svc_SE_s1/s4/s7,
    # SW_s4 RSZ-0074 and SE_s3/SW_s3 "OT_LINK_BUDGET: no measured clock" at 4_1_cts, 2026-10-12), and the per-block
    # forwarded-clock SDC (--sdc-append *_fwd.sdc: the FIFO write domains' own clocks)
    top_txt = "\n".join((ROOT / s).read_text(errors="replace") for s in srcs[:1] if (ROOT / s).exists())
    post_synth = ("physical/hbm_accel_die_views/common/inout_retype_post_synth.tcl"
                  if re.search(r"^\s*inout\b", top_txt, re.M) else None)
    rcmd = json.dumps(rec["spec"])
    sdc_x = sorted({x for x in re.findall(r"(?:rtl|physical)/[\w./-]+_fwd\.sdc", rcmd) if (ROOT / x).exists()})
    # benches of the closed record, same regexes; on drifted files they run on a snapshot overlay
    benches = [dict(b) for b in ((rec["spec"].get("stages") or {}).get("bench") or []) if isinstance(b, dict)]
    for b in benches:
        for tok in re.findall(r"(?<![\w{/.-])((?:rtl|tools|physical|results|docs)/[\w./-]+\.\w+)", b.get("cmd", "")):
            try:
                if changed(commit, tok):
                    snap.append(tok)
            except SpecSkip:
                pass
    snap = sorted(set(snap))
    if snap:
        srcs = [f"{kd}/src/{s}" if s in snap else s for s in srcs]
        for i, b in enumerate(benches):
            ov = (f"B={{RUN}}/bsrc_m5_{i}; rm -rf $B && mkdir -p $B && for d in *; do ln -s $PWD/$d $B/$d; done && "
                  f"for d in $(cd {kd}/src && ls -d */ | tr -d /); do rm -f $B/$d; cp -a $PWD/$d $B/$d; done && "
                  f"cp -a {kd}/src/. $B/ && cd $B && ")
            b["cmd"] = ov + "{ " + b["cmd"] + "\n}"
            b["note"] = (b.get("note", "") + f" [m5rr: run on the {commit[:9]} snapshot overlay of {kd}/src]").strip()
    W, H = lef["W"], lef["H"]
    # vertical-face pin capacity at the M5 cap: PPL keeps PIN_MIN_TRACKS=2 on the vertical pin layer (M5, 48 nm pitch),
    # so a N/S face holds ~W/0.096 pins on M5 alone; a face fuller than 90% of that gets M3 too (M3 M5, both under the
    # cap; ot_pqc_t_ix: 1,024 xw pins on a 97.2-um N face, PPL-0111 with M5 only, its closed view had M3 + M5)
    ns = {fc: sum(faces[b].get(fc, 0) for b in faces) for fc in ("N", "S")}
    route_x = {"pin_v": "M3 M5"} if max(ns.values()) > 0.9 * W / 0.096 else {}
    contract = None
    for f_, d in contracts():
        for sl in d["slots"]:
            if sl.get("cell") == cell and sl.get("layer_cap") == "M5" and abs(float(sl["outline"]["w"]) - W) < 0.01 and \
                    abs(float(sl["outline"]["h"]) - H) < 0.01:
                contract = {"file": str(f_.relative_to(ROOT)), "slot": sl["name"]}
                break
        if contract:
            break
    spec = {
        "name": name, "top": v["DESIGN_NAME"], "kind": "tile", "sources": srcs, "params": params,
        "clock_port": clk, "reset_ports": rst, **({"contract": contract} if contract else {"outline": {"w": W, "h": H}}), "macros": macros, "pins": pins,
        **({"defines": defines} if defines else {}), **({"orfs_vars": orfs_vars} if orfs_vars else {}),
        **({"post_synth_tcl": post_synth} if post_synth else {}), **({"sdc_extra": sdc_x} if sdc_x else {}),
        "route": {"pd": float(v.get("PLACE_DENSITY", 0.55) or 0.55), "threads": 8, **route_x,
                  "peak_ram_gb": int((rec["spec"].get("stages") or {}).get("route", {}).get("peak_ram_gb") or 32)},
        "job": {"owner": OWNER, "branch": BRANCH, "tag": "m5",
                "purpose": (f"M5 re-route (reroute_batch.py) of closed {rec['job']} ({cell}, RTL {commit[:9]}"
                            f"{', snapshot of ' + str(len(snap)) + ' drifted files' if snap else ''}): same RTL, "
                            f"outline {W}x{H}, pin faces from the closed view; ref_tile layer cap M5 (signals + PG <= M5, "
                            f"pins M4/M5, parent strap M6). Orig owner {rec['spec'].get('owner')}"),
                "benches": benches,
                **({} if benches else {"no_bench_reason": f"closed record {rec['job']} had no benches"})},
        "m5rr": {"cell": cell, "closed_job": rec["job"], "closed_commit": commit, "snapshot": snap,
                 "orig_owner": rec["spec"].get("owner")},
    }
    return spec, snap


def write_snapshot(kd: str, commit: str, files: list):
    for s in files:
        dst = ROOT / kd / "src" / s
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(subprocess.run(["git", "-C", str(ROOT), "show", f"{commit}:{s}"], capture_output=True,
                                       check=True).stdout)
    if files:
        (ROOT / kd / "src/SNAPSHOT_COMMIT").write_text(commit + "\n")


# ------------------------------------------------------------------------------------------------------ gate
ASSIGNED: dict[str, int] = {}
AVAIL: dict[str, int] = {}


def pick_host(mem: int) -> str:
    """the host with the most free memory after this batch's own assignments (ot-heavy then admits by memory there);
    MemAvailable is read once per host per batch so concurrent picks spread instead of piling on one host"""
    with LOCK:
        for h in HOSTS:
            if h not in AVAIL:
                try:   # MemAvailable minus the growth ot-heavy still reserves for running jobs (its admission rule)
                    o = ssh(h, "awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo; "
                               "tail -1 /var/tmp/ot-heavy/admit.log 2>/dev/null", timeout=20)
                    g = re.search(r"grow (\d+)G", o)
                    AVAIL[h] = int(o.split()[0]) - (int(g.group(1)) if g else 0)
                except Exception:  # noqa: BLE001
                    AVAIL[h] = -10 ** 6
        fits = [h for h in HOSTS if AVAIL[h] - HEADROOM[h] - ASSIGNED.get(h, 0) >= mem] or \
            [h for h in HOSTS if h in ("ot-epyc1tb", "ot-epyc4")]          # big hosts queue in ot-heavy
        best = max(fits, key=lambda h: AVAIL[h] - HEADROOM[h] - ASSIGNED.get(h, 0))
        ASSIGNED[best] = ASSIGNED.get(best, 0) + mem
        return best


def gate(kd: str, mem: int, remote=True) -> tuple[str, str, str]:
    cmd = [sys.executable, str(ROOT / "tools/ref_tile/pre_route_gate.py"), kd]
    host = ""
    if remote:
        host = pick_host(mem)
        cmd += ["--remote", host, "--mem", str(mem)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=4 * 3600)
    m = re.search(r"PRE_ROUTE_GATE:\s*(\w+)", r.stdout)
    fails = [l for l in r.stdout.splitlines() if l.startswith("GATE FAIL")]
    return (m.group(1) if m else "ERROR"), host, "; ".join(fails)[:600] or r.stdout[-300:]


# ------------------------------------------------------------------------------------------------------ contract
def bump_contract_pins(cell: str) -> int:
    """move the cell's contract pins / clock entry off M6+ (M6 -> M4, M7 -> M5; same face and offset)"""
    n = 0
    for f, d in contracts():
        hit = False
        for s in d["slots"]:
            if s.get("cell") != cell:
                continue
            for p in (s.get("pins") or []) + ([s["clock_entry"]] if isinstance(s.get("clock_entry"), dict) else []):
                mm = child_lint.metal(p.get("layer"))
                if mm and mm >= 6:
                    p["layer"] = "M4" if mm % 2 == 0 else "M5"
                    n += 1
                    hit = True
            if hit:
                s.pop("pin_replan", None)
                s["m5_reroute"] = "pins moved to M4/M5 for the M5 re-route (reroute_batch.py)"
        if hit:
            raw = f.read_text()
            f.write_text(json.dumps(d, indent=1, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
    return n


# ------------------------------------------------------------------------------------------------------ state / log
def load_state() -> dict:
    return jload(STATE, {}) or {"schema": "opentallas.hier_contract.reroute_m5_state.v1", "tiles": {}}


def save_state(st: dict):
    with LOCK:
        st["updated"] = now()
        tmp = STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")
        tmp.replace(STATE)


def owner_log(owner: str | None) -> Path:
    tag = (owner or "").split(":")[-1]
    for cand in (f"{tag}.log", f"el1011-{tag}.log", f"el1011-{tag.replace('el1011-', '')}.log"):
        p = TAKE / cand
        if tag and cand.startswith("el1011-") and p.exists():
            return p
    return TAKE / "el1011-reroute-m5.log"


def log(owner: str | None, line: str):
    with LOCK:
        with open(owner_log(owner), "a") as fh:
            fh.write(f"{dt.datetime.now().strftime('%m-%d %H:%M')} [reroute_m5] {line}\n")


# ------------------------------------------------------------------------------------------------------ run
def check_rlayers(kd: str, spec: dict):
    """lesson 10-12: a kit whose kit.env lacks RLAYERS routes on the flow default (signals up to M7+) and breaks the
    M5 contract silently.  Tiles must cap at M5 (M6 only with a layer_cap_grant); cluster kits keep their M7 signal
    cap (the batch never re-generates a cluster, but a cluster spec passed through must not be clipped)."""
    env = (ROOT / kd / "kit.env").read_text()
    m = re.search(r"^RLAYERS=['\"]?(M\d+)\s+(M\d+)", env, re.M)
    if not m:
        raise SpecSkip(f"kit {kd}/kit.env has no RLAYERS (ref_tile gen did not apply the layer contract)")
    top = int(m.group(2)[1:])
    if spec.get("kind") == "cluster":
        if top < 7:
            raise SpecSkip(f"cluster kit {kd} RLAYERS top {m.group(2)} < M7 (cluster kits keep M7)")
    elif top > 5 and not (spec.get("layer_cap") == "M6" and spec.get("layer_cap_grant")):
        raise SpecSkip(f"tile kit {kd} RLAYERS top {m.group(2)} above the M5 cap without a layer_cap_grant")


def job_name_free(name: str) -> str:
    """lesson 10-12: the loop keys jobs by name, so a name it already REFUSED (or saw in any state) is refused again
    at intake.  Return the first free name: name, name-r2, name-r3, ..."""
    n, cand = 1, name
    while (JOBS / f"{cand}.json").exists() or (INTAKE / f"{cand}.json").exists():
        n += 1
        cand = f"{name}-r{n}"
    return cand


def prepare(row, rec, st) -> dict | None:
    import ref_tile as RT
    t = st["tiles"].setdefault(row["cell"], {})
    try:
        f = fetch(rec, row["cell"])
        spec, snap = build_spec(row, rec, f)
        kd = f"physical/ref_tile/{spec['name']}"
        if git("ls-files", "--", kd).strip() and t.get("kit") != kd:
            raise SpecSkip(f"kit dir {kd} exists (not ours)")
        write_snapshot(kd, rec["commit"], snap)
        SPECS.mkdir(parents=True, exist_ok=True)
        sp = SPECS / f"{spec['name']}.json"
        sp.write_text(json.dumps(spec, indent=1) + "\n")
        RT.gen(str(sp))
        check_rlayers(kd, spec)
        if t.get("state_m5") == "failed":
            # --retry of a submitted M5 route that ended NEEDS_HUMAN / FAILED: keep its history, re-kit, new job name
            t.setdefault("history", []).append({k: t.get(k) for k in ("job", "commit", "compare")})
            for k in ("compare", "state_m5", "grant_proposed"):
                t.pop(k, None)
        t.update(state="kit", kit=kd, spec=str(sp.relative_to(ROOT)), closed_job=rec["job"], priority=row["priority"],
                 owner=rec["spec"].get("owner"), at=now())
        return {"cell": row["cell"], "kd": kd, "spec": sp, "mem": max(24, min(64, spec["route"]["peak_ram_gb"] // 2))}
    except (SpecSkip, Exception) as ex:  # noqa: BLE001
        kind = "skip" if isinstance(ex, SpecSkip) else "error"
        t.update(state=kind, reason=f"{type(ex).__name__}: {ex}"[:400], closed_job=rec["job"], at=now())
        log(rec["spec"].get("owner"), f"{row['cell']}: M5 re-route {kind}: {t['reason']}")
        return None


def run(a, rows, closed, st):
    sel = [r for r in rows if r["state"] == "eligible" and r["priority"] in a.priorities
           and (st["tiles"].get(r["cell"], {}).get("state") not in ("submitted", "skip", "gate_fail")
                or (a.retry and st["tiles"].get(r["cell"], {}).get("state") in ("gate_fail", "error"))
                or (a.retry and st["tiles"].get(r["cell"], {}).get("state_m5") == "failed"))]
    if a.only:
        sel = [r for r in sel if r["cell"] in a.only]
    sel = sel[: a.limit] if a.limit else sel
    print(f"run: {len(sel)} tiles (priorities {a.priorities})")
    preps = []
    for r in sel:
        p = prepare(r, closed[r["cell"]][-1], st)
        if p:
            preps.append(p)
    save_state(st)
    # gates: local + remote, spread over the fleet (ot-heavy admits by memory on each host)
    def g(p):
        v, host, why = gate(p["kd"], p["mem"], remote=not a.local_gate)
        return p, v, host, why
    ok = []
    with cf.ThreadPoolExecutor(max_workers=a.gates) as ex:
        for p, v, host, why in ex.map(g, preps):
            t = st["tiles"][p["cell"]]
            t.update(gate=v, gate_host=host, gate_at=now())
            if v in ("PASS", "WARN"):
                ok.append(p)
            else:
                t.update(state="gate_fail", reason=why)
                log(t.get("owner"), f"{p['cell']}: M5 re-route kit {p['kd']} pre-route gate {v} on {host}: {why[:300]}")
                if re.search(r"PPL-0111|slots for the pins|pin_capacity|pin density", why):
                    propose_grant(p["cell"], t, f"pin placement fails at M4/M5 ({why[:160]})")
            save_state(st)
    if not ok or a.no_submit:
        return
    # commit kits (+ contract pin moves), job specs at that commit, push, drop into the intake
    for p in ok:
        st["tiles"][p["cell"]]["contract_pins_moved"] = bump_contract_pins(p["cell"])
    paths = [p["kd"] for p in ok] + [str(p["spec"].relative_to(ROOT)) for p in ok] + \
        [str(f.relative_to(ROOT)) for f, _ in contracts()]
    git("add", "--", *paths)
    git("commit", "-q", "-m", f"m5rr: {len(ok)} M5 re-route kits via tools/ref_tile/reroute_batch.py "
        f"({', '.join(p['cell'] for p in ok[:12])}{' ...' if len(ok) > 12 else ''}); contract pins of these cells moved "
        f"off M6+ (M4/M5, same face/offset)\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    c1 = git("rev-parse", "--short=9", "HEAD").strip()
    for p in ok:
        subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "job", str(p["spec"]), "--commit", c1],
                       cwd=ROOT, check=True, capture_output=True)
    git("add", "--", *[f"{p['kd']}/job.json" for p in ok])
    git("commit", "-q", "-m", f"m5rr: job specs for {len(ok)} M5 re-route kits at {c1}\n\n"
        f"Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    git("push", "-q", "origin", f"HEAD:{BRANCH}")
    for p in ok:
        st["tiles"][p["cell"]].update(state="committed", commit=c1)
    save_state(st)
    submit(st)


def submit(st: dict):
    """drop every committed (gated, pushed) kit's job spec into the loop intake once; re-checks live jobs first"""
    _, live, pending = records()
    for cell, t in sorted(st["tiles"].items()):
        if t.get("state") != "committed":
            continue
        jp = ROOT / t["kit"] / "job.json"
        job = json.loads(jp.read_text())
        if job["block"] in live or job["block"] in pending:
            t.update(state="skip", reason="live job appeared before submit")
            continue
        sub = subprocess.run([sys.executable, str(ROOT / "tools/closure_loop/submit_lint.py"), "check", str(jp)],
                             cwd=ROOT, capture_output=True, text=True)
        if sub.returncode:
            t.update(state="gate_fail", reason="submit_lint: " + (sub.stdout + sub.stderr)[-300:])
            log(t.get("owner"), f"{cell}: M5 re-route submit_lint FAIL: {t['reason']}")
            continue
        name = job_name_free(job["name"])
        if name != job["name"]:
            prev = (jload(JOBS / f"{job['name']}.json") or {}).get("status") or "intake"
            log(t.get("owner"), f"{cell}: job name {job['name']} already used ({prev}); submitting as {name}")
            job["name"] = name
        (INTAKE / f"{name}.json").write_text(json.dumps(job, indent=1) + "\n")
        t.update(state="submitted", job=job["name"], submitted_at=now())
        log(t.get("owner"), f"{cell}: M5 re-route SUBMITTED {job['name']} (kit {t['kit']}, closed {t['closed_job']}, "
                            f"gate {t.get('gate')} on {t.get('gate_host')}, priority {t.get('priority')})")
        save_state(st)


# ------------------------------------------------------------------------------------------------------ compare
DIE_LOG = {"qwen_rom.json": "el1011-qwendie.log", "qwen_kv.json": "el1011-q-kvd.log", "s81.json": "el1011-s81die.log",
           "r25gq.json": "el1011-hbmdie.log"}
WORSE_SLACK_PS = 20.0
PIN_DENSE = 1.5          # signal pin rects per um of tile perimeter: an edge tile whose faces are pin-limited at M4/M5


def _ts(e: str):
    try:
        return dt.datetime.fromisoformat(e.split(" ", 1)[0])
    except Exception:  # noqa: BLE001
        return None


def route_numbers(job_name: str) -> dict:
    """TT / FF slack (verdict), DRC, route runtime (launched -> done), GRT overflow and DRT iterations (ORFS logs on the
    route host; None when the run was released)"""
    j = jload(JOBS / f"{job_name}.json") or {}
    m = j.get("metrics") or {}
    out = {"job": job_name, "status": j.get("status"), "tt_ps": None, "ff_ps": m.get("ff_ps"), "drc": m.get("drc"),
           "route_min": None, "grt_overflow": None, "drt_iters": None}
    t0 = t1 = None
    for e in j.get("events", []):
        if "launched route" in e:
            t0 = _ts(e)
        elif "route done" in e:
            t1 = _ts(e)
        mm = re.search(r"(?:CLOSED|verdict[^:]*):?.*?TT ([+-][\d.]+) / FF ([+-][\d.]+)", e)
        if mm:
            out["tt_ps"], out["ff_ps"] = float(mm.group(1)), float(mm.group(2))
    if t0 and t1:
        out["route_min"] = round((t1 - t0).total_seconds() / 60, 1)
    od, host = m.get("orfs_dir"), j.get("host")
    if od and host:
        o = ssh(host, f"cd {od}/logs/asap7/*/base 2>/dev/null && grep -E '^Total ' 5_1_grt.log | tail -1; "
                      f"python3 -c \"import json; d=json.load(open('5_2_route.json')); "
                      f"print('DRT', json.dumps({{k: v for k, v in d.items() if 'drc_errors' in k}}))\"", timeout=60)
        mo = re.search(r"(?m)^Total\s.*?(\d+)\s*/\s*(\d+)\s*/\s*(\d+)\s*$", o)
        if mo:
            out["grt_overflow"] = sum(int(x) for x in mo.groups())
        md = re.search(r"(?m)^DRT (.*)$", o)
        if md:
            d = json.loads(md.group(1))
            its = sorted(int(k.split(":")[1]) for k in d if ":" in k)
            out["drt_iters"] = (its[-1] + 1) if its else None
            out["drt_final_violations"] = d.get("detailedroute__route__drc_errors")
    return out


def pin_density(kd: str) -> float | None:
    fp = jload(ROOT / kd / "floorplan.json") or {}
    spec = jload(ROOT / kd / "spec.json") or {}
    if not fp:
        return None
    W, H = fp["die"][2], fp["die"][3]
    lef = None
    rec = (spec.get("m5rr") or {}).get("closed_job")
    f = jload(CACHE / str(rec) / "fetched.json") if rec else None
    if f and f.get("lef"):
        try:
            lef = child_lint.parse_lef(f["lef"], spec.get("top"))
        except Exception:  # noqa: BLE001
            lef = None
    if not lef:
        return None
    n = sum(1 for pn, p in lef["pins"].items() if not child_lint.is_pg(pn, p))
    return round(n / (2 * (W + H)), 3)


def propose_grant(cell: str, t: dict, why: str):
    """pin-dense edge tile worse / infeasible at M5: propose an M6 layer_cap_grant in the die lead's log (no M5 iteration)"""
    for f_, d in contracts():
        if any(sl.get("cell") == cell for sl in d["slots"]) and f_.name in DIE_LOG and \
                t.get("grant_proposed") != DIE_LOG[f_.name]:
            with LOCK, open(TAKE / DIE_LOG[f_.name], "a") as fh:
                fh.write(f"{dt.datetime.now().strftime('%m-%d %H:%M')} [reroute_m5] PROPOSAL to the {d.get('die')} die "
                         f"lead: layer_cap_grant M6 for {cell} (pin-dense edge tile; {why}). Not iterating at M5; "
                         f"grant -> set slot layer_cap M6 + layer_cap_grant, then reroute_batch.py re-generates.\n")
            t["grant_proposed"] = DIE_LOG[f_.name]
    if not t.get("grant_proposed"):          # placed through a parent cfg (cluster child): the die by name prefix
        lg = next((v for k, v in (("hgi_", "el1011-hbmdie.log"), ("ot_hgi", "el1011-hbmdie.log"), ("hfd_", "el1011-hbmdie.log"),
                                  ("qkd_", "el1011-q-kvd.log"), ("qfd_", "el1011-qwendie.log"), ("dsfd_", "el1011-s81die.log"),
                                  ("ot_dsrom", "el1011-s81die.log"), ("ot_pqc", "el1011-s81die.log"))
                   if cell.startswith(k) or any(str(x).startswith("cfg:" + k) for x in t.get("dies", []))), None)
        if lg:
            with LOCK, open(TAKE / lg, "a") as fh:
                fh.write(f"{dt.datetime.now().strftime('%m-%d %H:%M')} [reroute_m5] PROPOSAL to the die lead: "
                         f"layer_cap_grant M6 for {cell} (pin-dense edge tile; {why}). Not iterating at M5.\n")
            t["grant_proposed"] = lg


def compare(st: dict):
    for cell, t in sorted(st["tiles"].items()):
        if t.get("state") != "submitted" or (t.get("compare") or {}).get("final"):
            continue
        new = route_numbers(t["job"])
        if new["status"] not in TERMINAL:
            continue
        old = t.get("prev") or route_numbers(t["closed_job"])
        t["prev"] = old
        flags = []
        if new["status"] != "CLOSED":
            flags.append(f"M5 route {new['status']}")
        if (new.get("grt_overflow") or 0) > 0:
            flags.append(f"GRT overflow {new['grt_overflow']}")
        if new.get("drt_final_violations"):
            flags.append(f"DRT not converged ({new['drt_final_violations']} violations)")
        for k in ("tt_ps", "ff_ps"):
            if new.get(k) is not None and old.get(k) is not None and new[k] < old[k] - WORSE_SLACK_PS:
                flags.append(f"{k[:2].upper()} {old[k]:+.1f} -> {new[k]:+.1f} ps")
        dens = pin_density(t["kit"])
        t["compare"] = {"final": True, "at": now(), "m5": new, "prev": old, "flags": flags, "worse": bool(flags),
                        "pin_density_per_um": dens}
        t["state_m5"] = "closed" if new["status"] == "CLOSED" else "failed"
        line = (f"{cell}: M5 route {new['status']} TT {new['tt_ps']} / FF {new['ff_ps']} / GRT ovf {new['grt_overflow']} / "
                f"DRT iters {new['drt_iters']} / {new['route_min']} min vs previous {t['closed_job']} TT {old['tt_ps']} / "
                f"FF {old['ff_ps']} / GRT ovf {old['grt_overflow']} / DRT iters {old['drt_iters']} / {old['route_min']} min"
                + (f" -> WORSE: {'; '.join(flags)}" if flags else ""))
        log(t.get("owner"), line)
        if flags and dens is not None and dens >= PIN_DENSE:
            propose_grant(cell, t, f"{dens} signal pins/um; M5 re-route {t['job']} worse: {'; '.join(flags)}")
        save_state(st)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", nargs="?", default="plan", choices=["plan", "run", "status", "compare", "submit"])
    ap.add_argument("--priorities", type=lambda s: [int(x) for x in s.split(",")], default=[1, 2, 3, 4])
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--gates", type=int, default=12, help="concurrent remote gates")
    ap.add_argument("--local-gate", action="store_true", help="local gate only (no remote synthesis smoke)")
    ap.add_argument("--no-submit", action="store_true")
    ap.add_argument("--retry", action="store_true", help="also re-kit + re-gate gate_fail / error tiles and submitted "
                    "tiles whose M5 route ended NEEDS_HUMAN / FAILED (state_m5 failed)")
    a = ap.parse_args(argv)
    st = load_state()
    if a.cmd == "submit":
        submit(st)
        return 0
    if a.cmd == "compare":
        compare(st)
        return 0
    if a.cmd == "status":
        from collections import Counter
        print(Counter(t.get("state") for t in st["tiles"].values()))
        return 0
    p = plan()
    rows = p["rows"]
    for r in rows:
        t = st["tiles"].get(r["cell"], {})
        if t.get("state") == "submitted" and not (a.retry and t.get("state_m5") == "failed"):
            r["state"], r["reason"] = "skip", "submitted by this batch"
    from collections import Counter
    st["plan"] = {"at": now(), "eligible": sum(r["state"] == "eligible" for r in rows),
                  "by_priority": dict(Counter(r["priority"] for r in rows if r["state"] == "eligible")),
                  "skipped": dict(Counter(r.get("reason") for r in rows if r["state"] == "skip")), "rows": rows}
    print(json.dumps({k: v for k, v in st["plan"].items() if k != "rows"}, indent=1))
    if a.cmd == "run":
        run(a, rows, p["closed"], st)
        print(Counter(t.get("state") for t in st["tiles"].values()))
    save_state(st)
    return 0


if __name__ == "__main__":
    sys.exit(main())
