#!/usr/bin/env python3
"""Pre-redesign Fmax headroom of the reusable ASAP7 PRIMITIVES, from tight-target re-routes.

A routed record's ``fmax_hz`` is what that route achieved at its target, and most
published figures here came from targets the tool met and then stopped optimising
(see ``audit_asap7_fmax_inventory.py``).  On 2026-09-26 the current design's blocks
were re-routed at ``T = 1/(1.15*fmax)`` and ``T = 1/(1.35*fmax)`` of their published
Fmax, and the never-routed units (fdiv, fsqrt, the shipped engram hash) got a
baseline route first.  The sweep was HALTED part-way by a decision to re-specify the
core top-down, so some planned routes never landed; those are listed as cancelled,
not omitted.

This keeps only the PRIMITIVES a re-specified core is likely to reuse -- the fp32
add/mul pipes, fdiv, fsqrt, the exp/recip/rsqrt SFU pieces, softplus, top-k select,
the MAC/dot units, the quantisers, the engram hash and the package/express links --
and writes one table per primitive: the published record, every sweep route that
landed, the best CLOSED Fmax, and the best Fmax of any route with ``closed=false``
rows flagged.  A tight target is expected to miss, so a closed=false route's Fmax is
what ORFS reports for the achieved critical path (``finish__timing__fmax``), NOT a
closure claim.

WHAT THIS IS NOT.  It is pre-redesign characterisation of as-built blocks on the
predictive, non-manufacturable ASAP7 PDK: headroom evidence for setting a clock plan,
not a limiter, not a sign-off, and not a silicon claim.

Inputs (committed): the route records under
``results/physical_abi3/asap7/primitive_fmax_headroom/routes/`` with the sweep plan
``plan.json`` beside them, and each primitive's published base record.
``--import-from DIR`` copies the primitive routes and plan from a sweep output
directory first (``DIR/<job>/pnr.json``, ``DIR/jobs.json``).
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASAP7 = "results/physical_abi3/asap7/"
OUT_DIR = ROOT / ASAP7 / "primitive_fmax_headroom"
ROUTES = OUT_DIR / "routes"
PLAN = OUT_DIR / "plan.json"
OUTPUT = OUT_DIR / "primitive_fmax_headroom.json"
SCHEMA = "opentallas.physical.asap7_primitive_fmax_headroom.v1"
TOOL = "tools/summarize_primitive_fmax_headroom.py"

#: sweep variant -> (primitive class, published base record or None when first routed by the sweep)
PRIMITIVES: dict[str, tuple[str, str | None]] = {
    "fp32_add_rne_pipe": ("fp32 add pipe", "hdc/ot_fp32_add_rne_pipe/physical.json"),
    "fp32_mul_rne_pipe": ("fp32 mul pipe", "hdc/ot_fp32_mul_rne_pipe/physical.json"),
    "hdc_fp32_mul_pipe": ("fp32 mul pipe", "hdc/ot_hdc_fp32_mul_pipe/physical.json"),
    "hdc_fdiv": ("fp32 divide", None),
    "hdc_fsqrt": ("fp32 square root", None),
    "hdc_exp": ("SFU exp", "hdc/ot_hdc_exp_rebalanced_mul/physical.json"),
    "hdc_recip": ("SFU reciprocal", "hdc/ot_hdc_recip_rebalanced_mul/physical.json"),
    "hdc_rsqrt": ("SFU rsqrt", "hdc/ot_hdc_rsqrt_rebalanced_mul/physical.json"),
    "hdc_softplus": ("softplus", "hdc/v41/ot_hdc_softplus/physical.json"),
    "hdc_select_k6": ("top-k select", "hdc/v41/ot_hdc_select_k6/physical.json"),
    "hdc_select_k512": ("top-k select", "hdc/v41/ot_hdc_select_k512/physical.json"),
    "hdc_blockdot": ("MAC / block dot", "hdc/v41/ot_hdc_blockdot/physical.json"),
    "mac_bf16_fp32_pipe": ("MAC / block dot", "mac_bf16_fp32_pipe_round_stage/physical.json"),
    "hdc_actquant": ("quantiser", "hdc/v41/ot_hdc_actquant/physical.json"),
    "hdc_fp4qdq": ("quantiser", "hdc/v41/ot_hdc_fp4qdq/physical.json"),
    "hdc_engram_hash": ("engram hash", "hdc/v41/ot_hdc_engram_hash/physical.json"),
    "hdc_engram_hash_shipped": ("engram hash", None),
    "rom_pkg_link": ("link", "rom_pkg_link/physical.json"),
    "rom_express_link_s1000_L3000": ("link", "rom/ot_rom_express_link/s1000_w64_L3000/physical.json"),
}
#: planned routes killed by the OOM killer (detailed route, 12-16 GB floors on 32 GB workers),
#: relaunched at a 24 GB floor, and then cancelled by the halt
OOM_THEN_CANCELLED = {"hdc_exp_f115", "hdc_select_k512_f135", "hdc_engram_hash_shipped_f115"}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def _mhz(hz: Any) -> float | None:
    return round(hz / 1e6, 1) if hz else None


def _design(rec: dict[str, Any]) -> dict[str, Any]:
    d = rec.get("design") or {}
    return {"fmax_mhz": _mhz(d.get("fmax_hz")), "closed": d.get("closed"),
            "area_um2": d.get("area_um2") or d.get("standard_cell_area_um2"),
            "target_ns": rec.get("target_clock_period_ns"), "setup_wns_ns": d.get("setup_wns_ns"),
            "source_commit": (rec.get("git") or {}).get("commit")}


def import_routes(src: Path) -> None:
    plan = [j for j in json.loads((src / "jobs.json").read_text()) if j["variant"] in PRIMITIVES]
    ROUTES.mkdir(parents=True, exist_ok=True)
    keep = [{k: j[k] for k in ("job", "variant", "tag", "period_ns", "floor_gb", "argv")} for j in plan]
    PLAN.write_text(json.dumps(keep, indent=1) + "\n")
    for j in plan:
        p = src / j["job"] / "pnr.json"
        if p.exists():
            shutil.copyfile(p, ROUTES / f"{j['job']}.json")


def build() -> dict[str, Any]:
    plan = json.loads(PLAN.read_text())
    rows = []
    for variant, (klass, base_rel) in PRIMITIVES.items():
        row: dict[str, Any] = {"primitive": variant, "class": klass}
        if base_rel:
            base = json.loads((ROOT / ASAP7 / base_rel).read_text())
            row["top"] = (base.get("design") or {}).get("top") or (base.get("design") or {}).get("block")
            row["published"] = dict(_design(base), record=ASAP7 + base_rel)
        else:
            row["published"] = None
        routes, cancelled = [], []
        for j in (j for j in plan if j["variant"] == variant):
            p = ROUTES / f"{j['job']}.json"
            if not p.exists():
                cancelled.append({"job": j["job"], "target_ns": j["period_ns"],
                                  "why": ("OOM-killed in detailed route, relaunched at a 24 GB floor, then cancelled by the halt"
                                          if j["job"] in OOM_THEN_CANCELLED else "cancelled by the halt before landing")})
                continue
            rec = json.loads(p.read_text())
            r = dict(_design(rec), job=j["job"], kind=j["tag"], record=str(p.relative_to(ROOT)))
            if r["fmax_mhz"] is None:
                r["note"] = f"no Fmax: status={rec.get('status')}, stages_completed={rec.get('stages_completed')}"
            row.setdefault("top", (rec.get("design") or {}).get("top"))
            routes.append(r)
        row["sweep_routes"] = routes
        row["sweep_routes_not_landed"] = cancelled
        if not plan or not any(j["variant"] == variant for j in plan):
            row["note"] = "not in the sweep; published record only"
        cands = ([dict(row["published"], source="published")] if row["published"] else []) + \
                [dict(r, source=r["job"]) for r in routes]
        cands = [c for c in cands if c["fmax_mhz"]]
        closed = [c for c in cands if c["closed"]]
        bc = max(closed, key=lambda c: c["fmax_mhz"]) if closed else None
        ba = max(cands, key=lambda c: c["fmax_mhz"]) if cands else None
        row["best_closed"] = bc and {k: bc[k] for k in ("fmax_mhz", "area_um2", "target_ns", "source")}
        row["best_any"] = ba and {k: ba[k] for k in ("fmax_mhz", "area_um2", "target_ns", "source", "closed")}
        row["best_any_is_closed_false"] = bool(ba and not ba["closed"])
        if row["published"] and ba:
            row["headroom_over_published"] = round(ba["fmax_mhz"] / row["published"]["fmax_mhz"], 3) \
                if row["published"]["fmax_mhz"] else None
        rows.append(row)
    rows.sort(key=lambda r: (r["best_any"] or {}).get("fmax_mhz") or 0)
    return {
        "schema": SCHEMA,
        "label": "PRE-REDESIGN Fmax headroom of reusable primitives (characterisation of as-built blocks; "
                 "the core is being re-specified top-down)",
        "view": "asap7",
        "method": "re-route at T=1/(1.15*fmax) and T=1/(1.35*fmax) of the published Fmax; never-routed units get a "
                  "0.9 ns baseline first. Each route ran from its own pinned sparse worktree at the recorded commit "
                  "with a distinct DESIGN_NICKNAME tag.",
        "fmax_semantics": "best_closed is the highest Fmax of a route that met every acceptance check; best_any "
                          "includes closed=false routes (flagged), whose Fmax is ORFS finish__timing__fmax of the "
                          "achieved critical path at a deliberately missed target",
        "halted": "the sweep was halted on 2026-09-26 by a decision to re-specify the core; routes that had not landed "
                  "are listed per primitive under sweep_routes_not_landed",
        "excluded": {"hdc_sinkhorn": "multicycle unit (1/8 core clock under hdc_v41_sinkhorn_multicycle_8.tcl); "
                                     "not a single-cycle primitive",
                     "composites": "stream, matvec, kv_stream, tselect, su_lane, ROM collectives, fabric router, "
                                   "pkg_ctrl, host_if and mbist top were swept too but are as-built composites, not "
                                   "reusable primitives, and are not recorded here"},
        "primitives": rows,
        "not_a_claim": ["ASAP7 is a predictive, non-manufacturable academic PDK; no row here is a silicon claim",
                        "pre-redesign headroom, not the design's clock limiter"],
        "producer": {"tool": TOOL, "git": {"commit": _git("rev-parse", "HEAD")}},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--import-from", type=Path, default=None)
    ap.add_argument("--output", type=Path, default=OUTPUT)
    a = ap.parse_args(argv)
    if a.import_from:
        import_routes(a.import_from)
    out = build()
    a.output.write_text(json.dumps(out, indent=1) + "\n")
    for r in out["primitives"]:
        b, c = r["best_any"] or {}, r["best_closed"] or {}
        pub = (r["published"] or {}).get("fmax_mhz")
        print(f"{r['primitive']:30s} {r['class']:16s} published={pub}  best_closed={c.get('fmax_mhz')}  "
              f"best_any={b.get('fmax_mhz')}{'' if b.get('closed') else ' (closed=false)'}  area={b.get('area_um2')}  "
              f"not_landed={len(r['sweep_routes_not_landed'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
