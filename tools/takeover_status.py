#!/usr/bin/env python3
"""Takeover progress table (publication owner): blocks closed / total, die-level state and headline + gates per target.

Only COMMITTED evidence counts:
  * closed blocks = committed closure-loop verdict commits on the given ref ("closure-loop: <block> CLOSED SS <s> / FF <f>
    ps DRC <d> at <period>"), latest verdict per block, accepted when period 833.333, SS >= +15, FF >= +15, DRC 0
    (owner rule 5); a later non-CLOSED verdict line for the block is not a commit, so the latest CLOSED commit stands;
  * totals = distinct masters of the committed die abstract inventories (results/rtl/die_top_lint_20261006/*_abstract_list.json,
    dated 2026-10-06 -- the current S81 1,792 geometry and the HBM retile may differ; stated in the table);
  * headline + gates = results/arch/unified_composition_20261007/ledger.json (tools/unified_composition.py).

    python3 tools/takeover_status.py --ref origin/main --out /home/ubuntu/claude-takeover-20261007/STATUS.md
"""
import argparse
import datetime
import fnmatch
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "results/rtl/die_top_lint_20261006"
# S81 die view index (tools/s81/die_sta.py kit --index-out): the masters of the CURRENT S81 die case, each mapped to the
# view the die STA uses.  When present it replaces the 2026-10-06 S81 abstract inventories as the ds_rom total (those
# lists name the pre-1,792 masters, so no closed m221pq master ever matched them: "0 / 179").  Macros (ROM / PHY / SerDes
# hard IP liberty) are not closure-loop blocks and are left out of the total.
S81_INDEX = ROOT / "results/rtl/s81_die_view_index_20261008/index.json"
LEDGER = ROOT / "results/arch/unified_composition_20261007/ledger.json"
LB = ROOT / "results/arch/unified_composition_20261007/link_budget_restatus_20261007.json"   # SS re-STA (superseded by OB)
OB = ROOT / "results/closure_loop/option_b_status_20261007/status.json"   # option-B TT re-STA with the link budget (authoritative)
# CLOSURE LINE (OWNER DECISION 2026-10-07 evening): SS >= 0 / FF >= 0 / DRC 0 at 833.333 ps sign-off; +15 ps is a
# design target only. The consistent die-link budget and rule H1 still apply: a block counts only if its link-budget
# SS is also >= 0 (forwarded-clock stations stay unverified until a per-link model exists).
SS_LINE, FF_LINE = 0.0, 0.0
LINE_TEXT = ("Closure line (OWNER OPTION B, 2026-10-07 20:45; counts from results/closure_loop/option_b_status_20261007/"
             "status.json, TT re-STA of the final routes with the link budget): TT setup >= 0 ps, FF hold >= 0 ps, DRC 0 at 833.333 ps "
             "sign-off; SS setup is a sensitivity; +15 ps is a design target only. The consistent die-link budget "
             "(S + link + R + 150 ps skew <= T - 60) and rule H1 still apply. Loop verdicts committed before option B carry "
             "SS setup (SS >= 0 implies TT >= 0); verdicts after it carry TT setup in the same field. The link-budget "
             "revocations are subject to setup-triage's check of a possible reset-path artifact in the link-budget SDC")
PAT = re.compile(r"^closure-loop: (\S+) CLOSED SS ([+-]?[\d.]+) / FF ([+-]?[\d.]+) ps DRC (\d+) at ([\d.]+)")


def masters():
    out = {}
    q = json.loads((INV / "qwen_rom_abstract_list.json").read_text())
    out["qwen_rom"] = sorted({m for f in q["families"] for m in f.get("masters", [])})
    s = set()
    if S81_INDEX.exists():
        s = {m for m, r in json.loads(S81_INDEX.read_text())["masters"].items() if r["view"] != "macro"}
    else:
        for f in ("s81_layer_abstract_list.json", "s81_head_abstract_list.json"):
            d = json.loads((INV / f).read_text())
            s |= {m for fam in d["families"] for m in fam.get("masters", [])}
    out["ds_rom"] = sorted(s)
    h = json.loads((INV / "hbm_die_abstract_list.json").read_text())
    out["hbm_ds"] = [(f["family"], f["masters"]) for f in h["families"]]    # family glob, master count
    return out


VARIANT = re.compile(r"_(signoff\d+|host)$")


def canon(blk):
    """A verdict on a variant job of a master (e.g. qfd_chead_signoff833) closes that master; sub-blocks
    (e.g. dsfd_ctrl_ctr, a partition of dsfd_ctrl) do not and are reported separately."""
    while True:
        b2 = VARIANT.sub("", blk)
        if b2 == blk:
            return blk
        blk = b2


RECLOSE = re.compile(r"; job (\S+?-(?:lbc|cgfix|lbpin))(?:,|\s|$)")


def verdicts(ref):
    """Latest committed verdict per block on `ref`; re-close jobs (-lbc / -cgfix / -lbpin, routed under the consistent
    link budget) are also taken from any remote branch, since the loop commits them to the owner's branch first."""
    log = subprocess.check_output(["git", "log", ref, "--reverse", "--format=%h %cI %s"], cwd=ROOT, text=True)
    extra = subprocess.check_output(["git", "log", "--remotes", "--reverse", "--format=%h %cI %s",
                                     "--grep=^closure-loop: .* CLOSED"], cwd=ROOT, text=True)
    log += "\n".join(l for l in extra.splitlines() if RECLOSE.search(l))
    latest = {}
    for line in log.splitlines():
        h, t, subj = line.split(" ", 2)
        m = PAT.match(subj)
        if m:
            blk, ss, ff, drc, per = m.group(1), float(m.group(2)), float(m.group(3)), int(m.group(4)), float(m.group(5))
            blk = canon(blk)
            rc = RECLOSE.search(subj)
            if blk in latest and latest[blk].get("reclose") and not rc:
                continue        # a re-close under the consistent budget is newer evidence than any pre-budget verdict
            latest[blk] = dict(commit=h, at=t, ss=ss, ff=ff, drc=drc, period=per, reclose=rc.group(1) if rc else None,
                               accepted=abs(per - 833.333) < 0.01 and ss >= SS_LINE and ff >= FF_LINE and drc == 0)
    return latest


def link_budget():
    """canonical block -> worst verdict of its closed jobs under the consistent link budget (REVOKED > NOT CHECKED > HOLDS)."""
    if not LB.exists():
        return {}
    rank = {"HOLDS": 0, "NOT CHECKED": 1, "REVOKED": 2}
    out = {}
    for r in json.loads(LB.read_text())["rows"]:
        b = canon(r["block"])
        if b not in out or rank[r["verdict"]] > rank[out[b]["verdict"]]:
            out[b] = r
    return out


def apply_option_b(v):
    """Authoritative when present: integrate's option-B status (TT setup >= 0 under the consistent link budget, FF >= 0,
    DRC 0). Closed / unverified / revoked come from it; re-close jobs from branches (newer) still supersede."""
    d = json.loads(OB.read_text())
    out = {}
    for b in d["closed"]:
        out[canon(b["block"])] = dict(commit=(b.get("commit") or "")[:9], at="", ss=b["tt_lb_ps"], ff=b["ff_ps"], drc=b["drc"],
                                      period=833.333, accepted=True, lb="HOLDS", lb_ss=b["tt_lb_ps"], source="option_b")
    for b in d["unverified_forwarded_clock"]["blocks"]:
        out[canon(b["block"])] = dict(commit=(b.get("commit") or "")[:9], at="", ss=b.get("tt_ps"), ff=b.get("ff_ps"), drc=b.get("drc", 0),
                                      period=833.333, accepted=False, lb="NOT CHECKED", lb_ss=b.get("tt_lb_ps"), source="option_b")
    for b in d["revoked_previously_closed"]["blocks"]:
        out[canon(b["block"])] = dict(commit="", at="", ss=b.get("tt_ps"), ff=b.get("ff_ps"), drc=0, period=833.333,
                                      accepted=False, lb="REVOKED", lb_ss=b["tt_link_budget_ps"], source="option_b")
    for blk, x in v.items():
        if x.get("reclose"):
            out[blk] = dict(x, lb="HOLDS" if x["accepted"] else "REVOKED", lb_ss=x["ss"])
        elif blk not in out and x["accepted"]:
            out[blk] = dict(x, accepted=False, lb="not re-checked", source="loop commit")
    return out


def apply_link_budget(v):
    """A committed CLOSED verdict counts only if it HOLDS under the consistent link budget."""
    lb = link_budget()
    for b, x in v.items():
        r = lb.get(b)
        if x.get("reclose"):
            x["lb"] = "HOLDS" if x["accepted"] else "REVOKED"
            x["lb_ss"] = x["ss"]
            continue
        if x["accepted"]:
            if r is None:
                x["lb"] = "not re-checked"
            else:
                x["lb_ss"] = r.get("period_correction", r["link_budget_ss_ps"])
                x["lb"] = ("NOT CHECKED" if r["verdict"] == "NOT CHECKED" else "HOLDS" if x["lb_ss"] >= SS_LINE else "REVOKED")
            x["accepted"] = x["lb"] == "HOLDS"
    return v


def tally(inv, v):
    rows = {}
    for tgt in ("qwen_rom", "ds_rom"):
        ms = inv[tgt]
        acc = [m for m in ms if v.get(m, {}).get("accepted")]
        below = [m for m in ms if m in v and not v[m]["accepted"] and "lb" not in v[m]]
        rev = [m for m in ms if v.get(m, {}).get("lb") == "REVOKED"]
        unv = [m for m in ms if v.get(m, {}).get("lb") in ("NOT CHECKED", "not re-checked")]
        rows[tgt] = dict(total=len(ms), closed=acc, closed_below_rule=below, revoked=rev, unverified=unv)
    tot, acc, below, rev, unv = 0, [], [], [], []
    for fam, n in inv["hbm_ds"]:
        tot += n
        hit = sorted(b for b in v if fnmatch.fnmatch(b, fam))
        acc += [b for b in hit if v[b]["accepted"]][:n]
        below += [b for b in hit if not v[b]["accepted"] and "lb" not in v[b]]
        rev += [b for b in hit if v[b].get("lb") == "REVOKED"]
        unv += [b for b in hit if v[b].get("lb") in ("NOT CHECKED", "not re-checked")]
    rows["hbm_ds"] = dict(total=tot, closed=acc, closed_below_rule=below, revoked=rev, unverified=unv)
    return rows


# die inventories the streams keep on their branches (committed, not yet on main): reported, not merged into the counts
STREAM_INDEX = [
    "Stream die inventories (branch commits, not on main): HBM die views index r23 = 45 closed / 3 interim / 33 missing / "
    "2 reservation (claude/hbm-die-20261007 bc38f4908, physical/hbm_accel_die_views/index.json).",
    "Reported in stream logs, not yet committed (no credit): Qwen full-die GRT overflow 0 (adjfix_t4p8) and die STA on GRT "
    "parasitics SS WNS -90.23 ps (relay hops; SS is a sensitivity under option B) / FF -5.50 ps (qfd_tile assumed views) -- "
    "qwen-dietop.log 19:32-20:08.",
    "Committed block closures outside the closure loop (branch, not on main): WFC source die150 SS +31.5 / FF +22.7 DRC 0 "
    "(claude/s81-die-20261007 dc8570b5d).",
    "integrate re-verdicts: 24 NEEDS_RTL jobs requeued to the verdict / ECO completion at 20:31 (closure_loop.py reverdict); "
    "they count once their closure-loop commits land on main.",
]
DIE_STATE = dict(
    qwen_rom="REOPENED 2026-10-07; die-level items in the evidence table below (no flat full-die DRT by design)",
    ds_rom=("actual 1,792 mixed geometry is the basis; block total = the m221pq_r3 layer1 die view index "
                "(results/rtl/s81_die_view_index_20261008/index.json, macros excluded)"),
    hbm_ds="r23 die views; die-level items in the evidence table below")
HEAD = dict(qwen_rom=("unified_candidate", "unified_candidate_with_closure_upper"),
            ds_rom=("published", "published_m221pq_die", "actual1792_half_dedicated", "actual1792_full_shared"),
            hbm_ds=("unified_candidate", "unified_candidate_contracts_rtl", "unified_candidate_refill_cdc_only"))


def render(ref, rows, v):
    L = json.loads(LEDGER.read_text())
    sha = subprocess.check_output(["git", "rev-parse", "--short=9", ref], cwd=ROOT, text=True).strip()
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    o = [f"# Takeover status ({now}; evidence = commits on {ref} @ {sha})", "",
         "Only committed evidence counts. " + LINE_TEXT + ". A block is closed when its latest committed closure-loop verdict "
         "meets that line and its link-budget re-STA SS is >= 0. Totals come from the committed 2026-10-06 die abstract inventories, which may "
         "lag the current S81 1,792 geometry and the HBM retile. No headline is adopted; every rate is a candidate.", "",
         "| Target | Blocks closed / total | Die-level state | Headline candidates (AR / MTP tok/s) | Open gates |",
         "|---|---|---|---|---|"]
    for t in ("qwen_rom", "ds_rom", "hbm_ds"):
        r = rows[t]
        comps = L["targets"][t]["compositions"]
        hl = "; ".join(f"{c}: {comps[c]['AR_tok_s']:,.1f} / " + (f"{comps[c]['MTP_tok_s']:,.1f}" if comps[c].get("MTP_tok_s") else "AR mode")
                       for c in HEAD[t] if c in comps)
        gates = ", ".join(L["targets"][t]["gates"])
        o.append(f"| {t} | {len(r['closed'])} / {r['total']} (revoked: link budget {len(r['revoked'])}; unverified {len(r['unverified'])}) "
                 f"| {DIE_STATE[t]} | {hl} | {gates} |")
    o += ["", "Unestablished contracts (zero credit): " + ", ".join(c["id"] for c in L["unestablished_contracts"]),
          "Contracts established at RTL + bench (credit only in compositions that name them; physical pending): "
          + ", ".join(c["id"] for c in L.get("established_contracts_rtl_bench", [])), ""]
    E = L.get("die_level_evidence")
    if E:
        o += ["## Die-level evidence (academic validation; " + E["policy"] + ")", "",
              "| Target | Full-die GRT overflow | Die SS/FF STA (GRT parasitics) | CTS skew plan | IR | Region DRT + GRT-vs-DRT error bar |",
              "|---|---|---|---|---|---|"]
        cols = ("grt_overflow", "die_sta_grt_parasitics", "cts_skew_plan", "ir", "region_drt_and_error_bar")
        for t in ("qwen_rom", "ds_rom", "hbm_ds"):
            cells = []
            for c in cols:
                x = E[t][c]
                g = f" [{x['geometry']}]" if x.get("geometry") else ""
                cells.append(f"**{x['status']}**{g}: {x['note']}")
            o.append(f"| {t} | " + " | ".join(cells) + " |")
        o.append("")
    for line in STREAM_INDEX:
        o.append(line)
    o.append("")
    for t in ("qwen_rom", "ds_rom", "hbm_ds"):
        r = rows[t]
        o.append(f"## {t}")
        o.append("Closed: " + (", ".join(f"{b} ({v[b]['commit']} setup {v[b]['ss']:+.2f} / FF {v[b]['ff']:+.2f}"
                                          + (f"; re-closed under the link budget by {v[b]['reclose']}, branch commit" if v[b].get("reclose") else "")
                                          + ")" for b in r["closed"]) or "none"))
        if r["revoked"]:
            o.append("Revoked: link budget (TT setup slack under the consistent split): "
                     + ", ".join(f"{b} ({v[b]['lb_ss']:+.1f})" for b in r["revoked"]))
        if r["unverified"]:
            o.append("Unverified (needs a per-link model; forwarded-clock / source-synchronous): "
                     + ", ".join(f"{b} (common-clock split {v[b]['lb_ss']:+.1f})" if "lb_ss" in v[b] else f"{b} (not re-checked)" for b in r["unverified"]))
        if r["closed_below_rule"]:
            o.append("Committed CLOSED verdicts below the closure line or off-period (not counted): "
                     + ", ".join(f"{b} (SS {v[b]['ss']:+.2f} / FF {v[b]['ff']:+.2f} @ {v[b]['period']})" for b in r["closed_below_rule"]))
        o.append("")
    other = sorted(b for b in v if v[b]["accepted"] and not any(b in rows[t]["closed"] for t in rows))
    o.append("Holding verdicts on blocks outside the inventories (sub-blocks or new masters; not counted): " + (", ".join(other) or "none"))
    orev = sorted(b for b in v if v[b].get("lb") == "REVOKED" and not any(b in rows[t]["revoked"] for t in rows))
    o.append("Revoked (link budget) outside the inventories: " + (", ".join(f"{b} ({v[b]['lb_ss']:+.1f})" for b in orev) or "none"))
    if OB.exists():
        d_ = json.loads(OB.read_text())
        o += ["", f"Option-B status (results/closure_loop/option_b_status_20261007/status.json, evidence {d_['evidence_commit']}): "
                  f"{d_['counts']} over all loop blocks (inventory masters and sub-blocks). Revocations may change: setup-triage "
                  "is checking a possible reset-path artifact in the link-budget check."]
    if LB.exists():
        L_ = json.loads(LB.read_text())
        o += ["", f"Link-budget re-STA ({L_['rule']}; {L_['method']}): {L_['counts']}. Re-close queue: {L_['requeued']['note']}."]
    return "\n".join(o) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    v = apply_option_b(verdicts(a.ref)) if OB.exists() else apply_link_budget(verdicts(a.ref))
    rows = tally(masters(), v)
    a.out.write_text(render(a.ref, rows, v))
    print({t: f"{len(r['closed'])}/{r['total']}" for t, r in rows.items()})


if __name__ == "__main__":
    main()
