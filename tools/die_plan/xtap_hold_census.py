#!/usr/bin/env python3
"""C-XTAP-HOLD census (read-only): per kit gen dir, the pre-GRT FF hold class lines (pregrt_ff_hold.log) joined with the
tap-affinity knobs of config.mk, aggregated per die.

    xtap_hold_census.py GEN_DIR [GEN_DIR ...] [--tsv OUT]     (one gen dir per kit; reads pregrt_ff_hold.log, config.mk)
    xtap_hold_census.py --list FILE                           (GEN_DIR per line)

A kit counts as RESIDUAL when the class line AFTER the pre-GRT repair still lists cross_tap (or same_tap) endpoints: those
are named related endpoints the generator-level tap grouping and the hold cells did not close (hard-seam witnesses).
Static predictor (calibration, not a gate): cross_tap-before density with / without OT_TAP_PAIR_AFFINITY.  Report only.
"""
import argparse
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

CLS = re.compile(r"class (before|after) port_in (\d+) ws (\S+) same_tap (\d+) ws (\S+) cross_tap (\d+) ws (\S+) port_out (\d+)")
KNOB = re.compile(r"^export (OT_TAP_PAIR_[A-Z_]+|OT_TAP_CHAIN_AFFINITY)\s*=\s*(\S+)", re.M)


def die_of(path):
    p = str(path)
    if "qwen_compute" in p:
        return "QC"
    if "qwen_kvsys" in p:
        return "KV"
    if "/s81_head/" in p:
        return "HEAD"
    if "/s81/" in p:
        return "S81"
    return "other"


def parse_log(text):
    """-> {'before': dict, 'after': dict} from the LAST before / after class lines; missing = absent."""
    out = {}
    for m in CLS.finditer(text):
        w, pi, pw, st, sw, ct, cw, po = m.groups()
        out[w] = {"port_in": int(pi), "same_tap": int(st), "same_ws": float(sw),
                  "cross_tap": int(ct), "cross_ws": float(cw), "port_out": int(po)}
    return out


def parse_knobs(text):
    return dict(KNOB.findall(text))


def kit_row(gen):
    gen = Path(gen)
    log = gen / "pregrt_ff_hold.log"
    if not log.is_file():
        return None
    cls = parse_log(log.read_text(errors="replace"))
    if "before" not in cls:
        return None
    cfg = gen / "config.mk"
    knobs = parse_knobs(cfg.read_text(errors="replace")) if cfg.is_file() else {}
    return {"die": die_of(gen), "gen": str(gen), "before": cls["before"], "after": cls.get("after"),
            "affinity": knobs.get("OT_TAP_PAIR_AFFINITY") == "1", "knobs": knobs}


def residual(row):
    a = row["after"]
    return bool(a) and (a["cross_tap"] > 0 or a["same_tap"] > 0)


def summarize(rows):
    res = {}
    for die in sorted({r["die"] for r in rows}):
        rs = [r for r in rows if r["die"] == die]
        rd = [r for r in rs if residual(r)]
        res[die] = {
            "kits": len(rs),
            "cross_before_kits": sum(1 for r in rs if r["before"]["cross_tap"] > 0),
            "cross_before_ends": sum(r["before"]["cross_tap"] for r in rs),
            "residual_kits": len(rd),
            "residual_ends": sum(r["after"]["cross_tap"] + r["after"]["same_tap"] for r in rd),
            "residual_worst_ps": min([r["after"]["cross_ws"] for r in rd if r["after"]["cross_tap"]] or [0.0]),
            "affinity_on": sum(1 for r in rs if r["affinity"]),
            "median_cross_before_on": _med([r["before"]["cross_tap"] for r in rs if r["affinity"]]),
            "median_cross_before_off": _med([r["before"]["cross_tap"] for r in rs if not r["affinity"]]),
        }
    return res


def _med(v):
    return statistics.median(v) if v else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("gens", nargs="*")
    ap.add_argument("--list")
    ap.add_argument("--tsv")
    a = ap.parse_args(argv)
    gens = list(a.gens)
    if a.list:
        gens += [x.strip() for x in Path(a.list).read_text().splitlines() if x.strip()]
    rows = [r for r in (kit_row(g) for g in gens) if r]
    for die, s in summarize(rows).items():
        print("XTAP_CENSUS", die, " ".join(f"{k}={v}" for k, v in s.items()))
    if a.tsv:
        with open(a.tsv, "w") as f:
            f.write("die\taffinity\tcross_before\tcross_ws_before\tsame_before\tresidual_cross\tresidual_ws\tgen\n")
            for r in rows:
                af = r["after"] or {}
                f.write("\t".join(str(x) for x in (r["die"], int(r["affinity"]), r["before"]["cross_tap"], r["before"]["cross_ws"],
                                                  r["before"]["same_tap"], af.get("cross_tap", ""), af.get("cross_ws", ""), r["gen"])) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
