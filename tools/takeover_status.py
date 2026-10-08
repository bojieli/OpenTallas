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
LEDGER = ROOT / "results/arch/unified_composition_20261007/ledger.json"
PAT = re.compile(r"^closure-loop: (\S+) CLOSED SS ([+-]?[\d.]+) / FF ([+-]?[\d.]+) ps DRC (\d+) at ([\d.]+)")


def masters():
    out = {}
    q = json.loads((INV / "qwen_rom_abstract_list.json").read_text())
    out["qwen_rom"] = sorted({m for f in q["families"] for m in f.get("masters", [])})
    s = set()
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


def verdicts(ref):
    log = subprocess.check_output(["git", "log", ref, "--reverse", "--format=%h %cI %s"], cwd=ROOT, text=True)
    latest = {}
    for line in log.splitlines():
        h, t, subj = line.split(" ", 2)
        m = PAT.match(subj)
        if m:
            blk, ss, ff, drc, per = m.group(1), float(m.group(2)), float(m.group(3)), int(m.group(4)), float(m.group(5))
            blk = canon(blk)
            latest[blk] = dict(commit=h, at=t, ss=ss, ff=ff, drc=drc, period=per,
                               accepted=abs(per - 833.333) < 0.01 and ss >= 15 and ff >= 15 and drc == 0)
    return latest


def tally(inv, v):
    rows = {}
    for tgt in ("qwen_rom", "ds_rom"):
        ms = inv[tgt]
        acc = [m for m in ms if v.get(m, {}).get("accepted")]
        below = [m for m in ms if m in v and not v[m]["accepted"]]
        rows[tgt] = dict(total=len(ms), closed=acc, closed_below_rule=below)
    tot, acc, below = 0, [], []
    for fam, n in inv["hbm_ds"]:
        tot += n
        hit = sorted(b for b in v if fnmatch.fnmatch(b, fam))
        a = [b for b in hit if v[b]["accepted"]][:n]
        acc += a
        below += [b for b in hit if not v[b]["accepted"]]
    rows["hbm_ds"] = dict(total=tot, closed=acc, closed_below_rule=below)
    return rows


DIE_STATE = dict(
    qwen_rom="REOPENED 2026-10-07: interim die-top only; no full-die detailed route, die SS/FF STA, DRC/LVS or IR",
    ds_rom="actual 1,792 mixed geometry (77ffa0428 / 2d811aafb) is the integration basis; die DRT/SS/FF/IR not run",
    hbm_ds="die views + r23 closure ledger; no full-die detailed route / SS / FF / IR")
HEAD = dict(qwen_rom=("unified_candidate", "published"), ds_rom=("published", "actual1792_half_dedicated", "actual1792_full_shared"),
            hbm_ds=("unified_candidate", "unified_candidate_refill_cdc_only", "unified_candidate_refill_both"))


def render(ref, rows, v):
    L = json.loads(LEDGER.read_text())
    sha = subprocess.check_output(["git", "rev-parse", "--short=9", ref], cwd=ROOT, text=True).strip()
    now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    o = [f"# Takeover status ({now}; evidence = commits on {ref} @ {sha})", "",
         "Only committed evidence counts. A block is closed when its latest committed closure-loop verdict is at 833.333 ps "
         "with SS >= +15, FF >= +15 and DRC 0. Totals come from the committed 2026-10-06 die abstract inventories, which may "
         "lag the current S81 1,792 geometry and the HBM retile. No headline is adopted; every rate is a candidate.", "",
         "| Target | Blocks closed / total | Die-level state | Headline candidates (AR / MTP tok/s) | Open gates |",
         "|---|---|---|---|---|"]
    for t in ("qwen_rom", "ds_rom", "hbm_ds"):
        r = rows[t]
        comps = L["targets"][t]["compositions"]
        hl = "; ".join(f"{c}: {comps[c]['AR_tok_s']:,.1f} / " + (f"{comps[c]['MTP_tok_s']:,.1f}" if comps[c].get("MTP_tok_s") else "AR mode")
                       for c in HEAD[t] if c in comps)
        gates = ", ".join(L["targets"][t]["gates"])
        o.append(f"| {t} | {len(r['closed'])} / {r['total']} | {DIE_STATE[t]} | {hl} | {gates} |")
    o += ["", "Unestablished contracts (zero credit): " + ", ".join(c["id"] for c in L["unestablished_contracts"]), ""]
    for t in ("qwen_rom", "ds_rom", "hbm_ds"):
        r = rows[t]
        o.append(f"## {t}")
        o.append("Closed: " + (", ".join(f"{b} ({v[b]['commit']} SS {v[b]['ss']:+.2f} / FF {v[b]['ff']:+.2f})" for b in r["closed"]) or "none"))
        if r["closed_below_rule"]:
            o.append("Committed CLOSED verdicts below the +15/+15 rule or off-period (not counted): "
                     + ", ".join(f"{b} (SS {v[b]['ss']:+.2f} / FF {v[b]['ff']:+.2f} @ {v[b]['period']})" for b in r["closed_below_rule"]))
        o.append("")
    other = sorted(b for b in v if v[b]["accepted"] and not any(b in rows[t]["closed"] for t in rows))
    o.append("Accepted verdicts on blocks outside the inventories (sub-blocks or new masters; not counted): " + (", ".join(other) or "none"))
    return "\n".join(o) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    v = verdicts(a.ref)
    rows = tally(masters(), v)
    a.out.write_text(render(a.ref, rows, v))
    print({t: f"{len(r['closed'])}/{r['total']}" for t, r in rows.items()})


if __name__ == "__main__":
    main()
