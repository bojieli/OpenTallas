#!/usr/bin/env python3
"""Slot fit (owner 2026-10-13: the first release needs die timing on a die assembled from REAL views, so a tile must be
known to fit its die slot BEFORE it routes).

    slot_fit.py KIT_DIR [--repo DIR] [--json]        exit 0 fit / no slot, 1 mismatch

Compares a ref_tile kit (spec.json + floorplan.json + kit.env) with the slot the die contract gives its top cell:
  outline     kit outline vs slot outline.w / outline.h
  pins        every contract pin planned, on the contract face; no planned port the contract does not know; no port
              left to the placer (ANY) when the contract fixes faces; the clock on the clock_entry face
  pin_layer   the layer the kit uses on a face (kit.env PIN_H for E/W, PIN_V for N/S) vs the contract pin layers /
              slot pin_layers
  layer_cap   kit routing cap (RLAYERS) vs slot layer_cap (else pg_layer)
  pin_align   (owner 2026-10-13) a port the tile spec plans in a range ("pin_ranges") vs the span the slot gives it:
              more than 20 um outside = a note, more than 36 um = a mismatch (tools/hier_contract/pin_align.py: the jog
              of a relay-pitch bus then fills 0.60 of a 20-um die channel by itself)
  insertion   estimated clock insertion vs slot target_insertion_ps (+-100 ps, child_lint (g)); the estimate is the
              spec's est_insertion_ps, else the cell's previous view in the kit (TT lib max_clock_tree_path, else
              insertion.json).  No estimate = a note, not a mismatch.
The slot: the spec's "contract": {"file", "slot"}, else every slot whose "cell" is the kit top in a live contract
(results/arch/hier_contract_*/*.json, schema opentallas.hier_contract.v1; a contract another one names in derived_from
is superseded).  Children of a hardened cluster are slots with the cluster as parent, or rows of the contract's
sub_layouts[<cluster cell>] (the cluster's plan, outline only).  A cell placed in several slot variants fits when it
matches one.
pre_route_gate.submit_check REFUSES a mismatch unless the spec (job spec or tile spec) carries
"slot_change_request": "<die lead log line or contract version>"; then it is a WARN and the request is appended to the
die lead's log (lead_log()).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import child_lint  # noqa: E402
try:
    import pin_align  # noqa: E402
except ImportError:      # a tree that ships slot_fit.py without pin_align.py: the one-ended alignment check is skipped
    pin_align = None

SCHEMA = "opentallas.hier_contract.v1"
CONTRACT_GLOB = "results/arch/hier_contract_*/*.json"
TOL_UM = 0.001
INSERTION_TOL_PS = child_lint.INSERTION_TOL_PS
LOG_DIR = Path(os.environ.get("OT_DIE_LEAD_LOG_DIR", "/home/ubuntu/claude-takeover-20261007"))
LEAD_LOGS = (("qwen", "el1011-qwen-tp8.log"), ("s81", "el1011-s81die.log"), ("ds_rom", "el1011-s81die.log"),
             ("r25gq", "el1011-hbmdie.log"), ("hbm", "el1011-hbmdie.log"))


def lead_log(die: str, contract: str = "") -> Path | None:
    key = f"{die} {Path(contract).name}".lower()
    for k, f in LEAD_LOGS:
        if k in key:
            return LOG_DIR / f
    return None


def base(name: str) -> str:
    return re.sub(r"\[[^\]]*\]$", "", name)


# ------------------------------------------------------------------------------------------------------ contracts
CONTRACT_REFS = ("origin/main", "main")


def _git(repo: Path, *args) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def load_contracts(repo: Path, ref: str | None = None) -> list[dict]:
    """live contracts: [{"file", "die", "version", "data"}], superseded ones dropped.  ref None = the working tree of
    repo; a git ref = the files at that ref (the closure loop's repo is an object store whose checkout is stale, so the
    submit gate reads origin/main)"""
    texts = {}
    if ref is None:
        for p in sorted(repo.glob(CONTRACT_GLOB)):
            try:
                texts[str(p.relative_to(repo))] = p.read_text()
            except OSError:
                continue
    else:
        ls = _git(repo, "ls-tree", "-r", "--name-only", ref, "results/arch/") or ""
        for f in sorted(ls.split("\n")):
            if re.fullmatch(r"results/arch/hier_contract_[^/]*/[^/]+\.json", f):
                tx = _git(repo, "show", f"{ref}:{f}")
                if tx is not None:
                    texts[f] = tx
    out, dead = [], set()
    for f, tx in texts.items():
        try:
            d = json.loads(tx)
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("schema") != SCHEMA or not isinstance(d.get("slots"), list):
            continue
        src = d.get("derived_from")
        if isinstance(src, dict) and src.get("contract"):
            dead.add(str(src["contract"]))
        if d.get("superseded_by"):
            dead.add(f)
        out.append({"file": f, "die": str(d.get("die", Path(f).stem)), "version": d.get("version"), "data": d})
    return [c for c in out if c["file"] not in dead]


def live_contracts(repo: Path, commit: str = "") -> tuple[list[dict], str]:
    """(contracts, where) for the submit gate: origin/main of the repo, else main, else the job's commit, else the
    working tree"""
    for ref in (*CONTRACT_REFS, commit):
        if ref:
            cs = load_contracts(repo, ref)
            if cs:
                return cs, ref
    return load_contracts(repo), "worktree"


def _entry(c: dict, s: dict) -> dict:
    e = dict(s)
    e.update(_file=c["file"], _die=c["die"], _version=s.get("version", c["version"]), _contract_version=c["version"])
    return e


def find_slots(contracts: list[dict], cell: str, explicit: dict | None = None) -> list[dict]:
    """plan entries for the cell: the explicit contract slot, else every slot / cluster sub-layout row of that cell"""
    if explicit:
        for c in contracts:
            if c["file"] == explicit.get("file"):
                return [_entry(c, s) for s in c["data"]["slots"] if isinstance(s, dict) and s.get("name") == explicit.get("slot")]
        return []
    out = []
    for c in contracts:
        d = c["data"]
        for s in d["slots"]:
            if isinstance(s, dict) and s.get("cell") == cell and s.get("kind") != "die":
                out.append(_entry(c, s))
        for parent, lay in (d.get("sub_layouts") or {}).items():
            for r in (lay.get("rows") or []) if isinstance(lay, dict) else []:
                if isinstance(r, dict) and r.get("cell") == cell and "w" in r and "h" in r:
                    out.append(_entry(c, {"name": f"{parent}:{r.get('tile', cell)}", "cell": cell, "kind": "tile",
                                          "parent": parent, "outline": {"w": r["w"], "h": r["h"]}, "_plan": "sub_layout"}))
    return out


# ------------------------------------------------------------------------------------------------------------ kit
def kit_facts(kd: Path, job: dict | None = None) -> dict:
    spec = json.loads((kd / "spec.json").read_text())
    fp = json.loads((kd / "floorplan.json").read_text())
    env = (kd / "kit.env").read_text() if (kd / "kit.env").exists() else ""

    def var(k):
        m = re.search(rf"^{k}='([^']*)'", env, re.M)
        return m.group(1).split() if m else []
    rl = var("RLAYERS")
    cap = rl[1] if len(rl) > 1 else (fp.get("layer_contract", {}).get("rlayers") or [None, None])[1]
    pins = fp.get("pins") if isinstance(fp.get("pins"), dict) else spec.get("pins")
    pins = pins if isinstance(pins, dict) else {}
    top = spec["top"]
    est, basis = None, None
    for src, d in (("job spec", job or {}), ("tile spec", spec)):
        if d.get("est_insertion_ps") is not None:
            est, basis = float(d["est_insertion_ps"]), f"{src} est_insertion_ps"
            break
    if est is None:
        for vd in (kd / "views" / top, kd / "views"):
            lib = vd / f"{top}_tt.lib"
            if lib.exists():
                ins = [v["max_ps"] for v in child_lint.clock_insertion(lib.read_text(errors="replace")).values() if v]
                if ins:
                    est, basis = max(ins), f"previous view {lib.name} max_clock_tree_path"
                    break
            ij = vd / "insertion.json"
            if ij.exists():
                try:
                    est = float(json.loads(ij.read_text())["tt"]["all"]["max"])
                    basis = "previous view insertion.json tt.all.max"
                    break
                except (ValueError, KeyError, TypeError):
                    pass
    req = (job or {}).get("slot_change_request") or spec.get("slot_change_request")
    return {"name": spec.get("name", kd.name), "top": top, "kind": spec.get("kind"), "contract": spec.get("contract"),
            "outline": [float(x) for x in fp["die"][2:4]], "pins": {f: list(n) for f, n in pins.items()},
            "clock_port": spec.get("clock_port"), "reset_ports": list(spec.get("reset_ports", [])),
            "pin_layers": {"E": var("PIN_H"), "W": var("PIN_H"), "N": var("PIN_V"), "S": var("PIN_V")},
            "cap": cap, "est_insertion_ps": est, "est_basis": basis, "slot_change_request": req,
            "pin_ranges": spec.get("pin_ranges") if isinstance(spec.get("pin_ranges"), dict) else {}}


# -------------------------------------------------------------------------------------------------------- compare
def _oriented(layer: str, face: str) -> bool:
    """asap7: even metals run horizontally (E/W face pins), odd metals vertically (N/S face pins)"""
    n = child_lint.metal(layer)
    return n is not None and (n % 2 == 0) == (face in ("E", "W"))


def slot_span(p: dict) -> tuple[float, float] | None:
    """(lo, hi) um along the face of a contract pin: "span_um", else "offset" (pin / bus centre) +- "width" / 2"""
    sp = p.get("span_um")
    try:
        if isinstance(sp, (list, tuple)) and len(sp) == 2:
            return tuple(sorted((float(sp[0]), float(sp[1]))))
        if p.get("offset") is not None:
            o, w = float(p["offset"]), float(p.get("width") or 0.0)
            return (o - w / 2, o + w / 2)
    except (TypeError, ValueError):
        pass
    return None


def compare(k: dict, s: dict) -> tuple[list[str], list[str]]:
    """(mismatches, notes) of kit facts k against plan entry s"""
    bad, notes = [], []
    ow, oh = float(s["outline"]["w"]), float(s["outline"]["h"])
    if abs(ow - k["outline"][0]) > TOL_UM or abs(oh - k["outline"][1]) > TOL_UM:
        bad.append(f"outline {k['outline'][0]:g} x {k['outline'][1]:g} != slot {ow:g} x {oh:g}")
    # ---- pin faces
    plan = {n: f for f, names in k["pins"].items() for n in names}
    want: dict[str, set] = {}
    want_layers: dict[str, set] = {}
    for p in s.get("pins") or []:
        if not isinstance(p, dict) or not p.get("name"):
            continue
        if p.get("face"):
            want.setdefault(base(p["name"]), set()).add(p["face"])
            if p.get("layer"):
                want_layers.setdefault(p["face"], set()).add(p["layer"])
        else:
            want.setdefault(base(p["name"]), set())
    ce = s.get("clock_entry") or {}
    side = {k["clock_port"], *k["reset_ports"]}
    if want:
        miss = sorted(n for n in want if n not in plan and not (n == ce.get("pin") and k["clock_port"] in plan))
        extra = sorted(n for n in plan if n not in want and n not in side)
        wrong = sorted(f"{n} {plan[n]} (slot {'/'.join(sorted(want[n]))})" for n in want
                       if n in plan and want[n] and plan[n] not in want[n])
        if miss:
            bad.append(f"{len(miss)} slot pins not in the pin plan (e.g. {', '.join(miss[:4])})")
        if extra:
            bad.append(f"{len(extra)} planned ports the slot does not have (e.g. {', '.join(extra[:4])})")
        if wrong:
            bad.append(f"{len(wrong)} pins off their slot face: {'; '.join(wrong[:4])}")
    ck = k["clock_port"]
    # a clock_entry whose layer cannot be a pin layer of its face (M4 on N: the s81 contract default) is not a plan
    planned_ce = bool(ce.get("face")) and (not ce.get("layer") or _oriented(ce["layer"], ce["face"]))
    if ce.get("face") and not planned_ce:
        notes.append(f"slot clock_entry {ce['face']}/{ce['layer']} is not a possible face pin (contract default): clock face "
                     "not checked; the die lead must fix the entry")
    if planned_ce and ck in plan and plan[ck] != ce["face"] and not (ck in want and plan[ck] in want[ck]):
        bad.append(f"clock {ck} on {plan[ck]} (slot clock_entry {ce['face']})")
    # ---- pin layers
    pl = s.get("pin_layers")
    for f in "NSEW":
        used = set(k["pin_layers"].get(f) or [])
        has = bool(k["pins"].get(f)) or f in want_layers
        if not used or not has:
            continue
        if isinstance(pl, dict) and pl.get(f):
            allowed = set(str(pl[f]).split())
        elif isinstance(pl, list) and pl and any(_oriented(x, f) for x in pl):
            allowed = {x for x in pl if _oriented(x, f)} | want_layers.get(f, set())
        else:
            allowed = set(want_layers.get(f, set()))
        if not allowed:
            continue
        if s.get("m6_pin_grant") and f in ("E", "W"):
            allowed.add("M6")
        over = sorted(used - allowed)
        lack = sorted(x for x in want_layers.get(f, set()) if x not in used and _oriented(x, f))
        if over:
            bad.append(f"{f}-face pins may land on {'/'.join(over)} (slot {'/'.join(sorted(allowed))})")
        if lack:
            bad.append(f"{f}-face slot pin layer {'/'.join(lack)} is not a kit pin layer ({'/'.join(sorted(used))})")
    # ---- pin alignment, one-ended (owner 2026-10-13, tools/hier_contract/pin_align.py): a port the kit plans in a
    # range (tile spec "pin_ranges") against the span the slot gives it.  The peer faces the SLOT span, so every um the
    # kit range lies outside it is a jog in the die channel: > WARN_UM a note, > FAIL_UM a mismatch (the jog of a bus
    # at the relay pin pitch then fills 0.60 of a 20-um channel by itself).  Slot pins still waiting for the view's
    # offsets (offset_pending_view) and ports without a planned range are not judged.
    rng = (k.get("pin_ranges") or {}) if pin_align is not None else {}
    for p in s.get("pins") or []:
        if not isinstance(p, dict) or p.get("offset_pending_view") or base(p.get("name") or "") not in rng:
            continue
        span = slot_span(p)
        try:
            lo, hi = sorted(float(x) for x in rng[base(p["name"])][:2])
        except (TypeError, ValueError):
            continue
        if span is None:
            continue
        jog = pin_align.range_jog(lo, hi, *span)
        msg = (f"{base(p['name'])} planned at {lo:g}..{hi:g} um lies up to {jog:.1f} um outside its slot span "
               f"{span[0]:g}..{span[1]:g} um on {p.get('face')}")
        if jog > pin_align.FAIL_UM:
            bad.append(f"pin_align: {msg} (> {pin_align.FAIL_UM} um: the jog alone fills a 20-um channel past the 0.60 cut rule)")
        elif jog > pin_align.WARN_UM:
            notes.append(f"pin_align WARN: {msg} (> {pin_align.WARN_UM:g} um jog in the die channel)")
    # ---- layer cap
    scap = s.get("layer_cap")
    if isinstance(scap, dict):      # derived contracts: {"cap": "M5", "view_max_layer": ..., "conforms": ...}
        scap = scap.get("cap")
    scap = scap or s.get("signal_max_layer") or s.get("pg_layer")
    if scap and k["cap"] and (child_lint.metal(k["cap"]) or 0) > (child_lint.metal(scap) or 99):
        bad.append(f"routing cap {k['cap']} above the slot layer cap {scap}")
    # ---- clock insertion
    tgt = s.get("target_insertion_ps")
    if tgt is not None:
        if k["est_insertion_ps"] is None:
            notes.append(f"no clock insertion estimate against the slot target {float(tgt):.0f} ps (give est_insertion_ps "
                         "from pre_route_gate --remote --cts)")
        elif abs(k["est_insertion_ps"] - float(tgt)) > INSERTION_TOL_PS:
            bad.append(f"estimated clock insertion {k['est_insertion_ps']:.0f} ps ({k['est_basis']}) vs slot target "
                       f"{float(tgt):.0f} ps (+-{INSERTION_TOL_PS:.0f})")
    return bad, notes


def check(kd: Path, repo: Path, job: dict | None = None, contracts: list[dict] | None = None) -> dict:
    """{"status": "no_slot"|"fit"|"mismatch", "mismatches", "notes", "slot", "die", "contract", "version", "variants",
    "slot_change_request"}"""
    k = kit_facts(kd, job)
    contracts = load_contracts(repo) if contracts is None else contracts
    ents = find_slots(contracts, k["top"], k["contract"])
    if not ents and k["contract"]:      # the named contract is superseded or lacks the slot: look the cell up
        ents = find_slots(contracts, k["top"])
    out = {"kit": k["name"], "top": k["top"], "slot_change_request": k["slot_change_request"], "slots": len(ents)}
    if not ents:
        return dict(out, status="no_slot", mismatches=[], notes=[])
    seen, best = set(), None
    for e in ents:
        sig = json.dumps({x: e.get(x) for x in ("outline", "pins", "pin_layers", "clock_entry", "layer_cap", "pg_layer",
                                                "signal_max_layer", "target_insertion_ps", "m6_pin_grant")}, sort_keys=True)
        if sig in seen:
            continue
        seen.add(sig)
        bad, notes = compare(k, e)
        if best is None or len(bad) < len(best[0]):
            best = (bad, notes, e)
        if not bad:
            break
    bad, notes, e = best
    return dict(out, status="mismatch" if bad else "fit", mismatches=bad, notes=notes, slot=e["name"], die=e["_die"],
                contract=e["_file"], version=e["_contract_version"], slot_version=e["_version"], variants=len(seen))


def append_request(res: dict, job_name: str, commit: str = "") -> Path | None:
    """append the slot change request to the die lead's log (once per job / request)"""
    log = lead_log(res.get("die", ""), res.get("contract", ""))
    if log is None:
        return None
    key = f"SLOT_CHANGE_REQUEST job={job_name} commit={commit[:12]} slot={res.get('slot')}"
    try:
        if log.exists() and key in log.read_text(errors="replace"):
            return log
        with log.open("a") as fh:
            fh.write(f"\n{time.strftime('%Y-%m-%d %H:%M %Z')} {key} cell={res.get('top')} contract={res.get('contract')} "
                     f"v{res.get('version')} request={res.get('slot_change_request')!r} (submit gate slot-fit WARN, tile routes "
                     f"against the request): {' | '.join(res.get('mismatches', []))[:900]}\n")
    except OSError:
        return None
    return log


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit")
    ap.add_argument("--repo", default=str(HERE.parent.parent))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = check(Path(a.kit), Path(a.repo))
    if a.json:
        print(json.dumps(res, indent=1))
    else:
        print(f"SLOT_FIT {res['status'].upper()} {res['kit']} ({res['top']})"
              + (f" slot {res['slot']} of {res['contract']} v{res['version']}" if res.get("slot") else ""))
        for m in res["mismatches"]:
            print(f"  MISMATCH {m}")
        for n in res["notes"]:
            print(f"  note {n}")
    return 1 if res["status"] == "mismatch" else 0


if __name__ == "__main__":
    sys.exit(main())
