"""C-GPL-TD-INFLATION (CLASS-OWNERS-B 11-26): plan flag ``gpl_td`` (top-level plan dict, default OFF, absent = byte-identical kit).

    "gpl_td": {"top_overflow_trigger": 1, "firm_small_clusters": 1, "cell_growth_gate": 1}

Why (FABLE-FLOW-0847 A3): timing-driven GPL repair fires on the MEAN overflow of the top-level region and every odb region/group, so
a handful of tiny OT_LOGIC_CLUSTER regions (3-20 cells, finished at once) pull the mean under the first reweight threshold at
iteration 1 and repair_design buffers an unsettled placement (HEAD hd_lep0N fed00: +56,515 buffers, HPWL 1.30e7 -> 1.90e7).
  top_overflow_trigger  0 / 1 / settle overflow in (0, 1): timing-driven repair only on a placement whose TOP-LEVEL overflow has
                        settled (gpl_td.tcl: only the reweight thresholds at or under the settle overflow are kept).  1 = the
                        R-FLOW gpl_keep_overflow (0.25).  It also exports OT_LOGIC_CLUSTER_POST_GPL=1 (gen_phys, post_gpl_regions):
                        every logic_cluster region is created after global_placement, so GPL has only the top-level region and the
                        overflow OpenROAD tests IS the top-level overflow (C-TDREPAIR-REGION-MEAN 11-27).
  firm_small_clusters   0 / 1 / N (3..20): logic_cluster_rects_um clusters of at most N movable cells (1 = 20) are seated FIRM at their
                        rect (logic_cluster.py), released for DPL, and are no GPL region.
  cell_growth_gate      0 / 1 / 2 ("report" / "fail"): non-tap cell count after GPL and after the place resize against
                        min(400k cap, pre-GPL count x 1.35), one OT_GPL_TD_GROWTH line per stage.
  post_td_exit          0 / 1 / exit overflow in (0, 1): C-GPL-POSTTD-TAIL-SPARSE (HEAD-EAST-R4 11-27).  The timing-driven global placement
                        call ends at this overflow instead of the stock 0.10, so the Nesterov tail after the timing-driven pass is
                        short.  On a sparse kit (hd_lep0N C1d: 2.06 % movable util) that tail spread free cells into the empty
                        strips: TD at iter 363 overflow 0.244 HPWL 12.20M, exit at 0.0953 iter 403 HPWL 18.65M (+53 %).  1 = 0.20.
                        Needs top_overflow_trigger with a settle overflow at least 5 points above the exit (the TD pass then fires
                        before the exit; gpl_td.tcl also keeps only reweight thresholds in [exit + 5, settle] and raises a keep
                        threshold above 0 but under exit + 5 to exit + 10; a keep of 0 stays reweight-only).  The exit is at most
                        SETTLE_DEFAULT - 0.05 (0.20), so a stock keep of 0.25 is never raised onto a less settled placement.  DPL legalizes the residual
                        overlap.  OT_GPL_OVERFLOW / OT_GPL_SPARSE_OVERFLOW already set a GPL exit; this key exists for the per-type plan
                        scope and the TD-pass ordering.  The guard's GPL-0305 plain retry inherits the same exit (intended: one stop
                        for the call).  PROBE-ONLY until an hd_lep0N A/B shows place WNS/TNS, GRT overflow and the DPL verdict / max
                        displacement no worse (gen_phys records early-exit timing cost on hd_serdes); not for die-wide use.
  types                 optional regex (re.search on the partition type name, as tap_reach.types): the flag applies only to the
                        matching types; every other type gets the unchanged kit.  Absent = every type (the 11-26 behaviour,
                        byte-identical).  FLAG-SCOPE 11-27 (HEAD-INT-R3 W13 ruling: no die-wide keys; HEAD-EAST-R4).
"""
import re
import shutil
from pathlib import Path

KEYS = ("top_overflow_trigger", "firm_small_clusters", "cell_growth_gate", "post_td_exit")
SETTLE_DEFAULT = 0.25          # == gen_phys.RFLOW["gpl_keep_overflow"] (test_gpl_td asserts it)
SMALL_MIN, SMALL_MAX = 3, 20   # OWNER: seat 3-20 cell clusters FIRM
EXIT_DEFAULT = 0.20            # post_td_exit 1: end the timing-driven GPL call at overflow 0.20
EXIT_MARGIN = 0.05             # the TD pass fires at least 5 overflow points before the exit
GROWTH_REL = 0.35
TCL = "gpl_td.tcl"
SCOPE = "types"


def in_scope(raw, tn):
    """True when the plan gpl_td applies to type tn: no scope (absent types = every type) or gpl_td.types matches tn (re.search)."""
    d = (raw or {}).get("gpl_td")
    if not isinstance(d, dict) or SCOPE not in d:
        return True
    rx = d[SCOPE]
    if not isinstance(rx, str) or not rx:
        raise ValueError(f"gpl_td.types must be a non-empty regex string, got {rx!r}")
    try:
        return re.search(rx, tn or "") is not None
    except re.error as e:
        raise ValueError(f"gpl_td.types is not a valid regex {rx!r}: {e}") from None


def spec(raw, tn=None):
    """Normalised flag dict {top: settle overflow | 0, firm_small: max cells | 0, growth: 0|1|2[, exit: overflow]}; {} when the plan has no gpl_td, or
    when tn is given and gpl_td.types does not match it (tn None = the die-wide reading: scope validated, not applied)."""
    d = (raw or {}).get("gpl_td")
    if d is None:
        return {}
    if not isinstance(d, dict) or not d:
        raise ValueError("gpl_td must be a non-empty dict")
    hit = in_scope(raw, "" if tn is None else tn)          # validates gpl_td.types in every reading
    scoped = True if tn is None else hit
    d = {k: v for k, v in d.items() if k != SCOPE}
    if not d:
        raise ValueError("gpl_td must set at least one of " + ", ".join(KEYS))
    bad = sorted(set(d) - set(KEYS))
    if bad:
        raise ValueError(f"gpl_td: unknown keys {bad}")
    top = d.get("top_overflow_trigger", 0)
    if isinstance(top, bool) or top in (0, 1):
        top = SETTLE_DEFAULT if top else 0
    elif not isinstance(top, (int, float)) or not 0 < top < 1:
        raise ValueError(f"gpl_td.top_overflow_trigger must be 0, 1 or a settle overflow in (0, 1), got {top!r}")
    fs = d.get("firm_small_clusters", 0)
    if isinstance(fs, bool) or fs in (0, 1):
        fs = SMALL_MAX if fs else 0
    elif not isinstance(fs, int) or not SMALL_MIN <= fs <= SMALL_MAX:
        raise ValueError(f"gpl_td.firm_small_clusters must be 0, 1 or an int in {SMALL_MIN}..{SMALL_MAX}, got {fs!r}")
    g = d.get("cell_growth_gate", 0)
    g = {"report": 1, "fail": 2}.get(g, g) if isinstance(g, str) else g
    if g not in (0, 1, 2):
        raise ValueError(f"gpl_td.cell_growth_gate must be 0, 1 (report) or 2 (fail), got {d.get('cell_growth_gate')!r}")
    ex = d.get("post_td_exit", 0)
    if isinstance(ex, bool) or ex in (0, 1):
        ex = EXIT_DEFAULT if ex else 0
    elif not isinstance(ex, (int, float)) or not 0 < ex < 1:
        raise ValueError(f"gpl_td.post_td_exit must be 0, 1 or an exit overflow in (0, 1), got {ex!r}")
    if ex and not top:
        raise ValueError("gpl_td.post_td_exit needs top_overflow_trigger (the TD pass must be placed above the exit)")
    if ex and round(top - ex, 6) < EXIT_MARGIN:
        raise ValueError(f"gpl_td.post_td_exit {ex:g} must be at least {EXIT_MARGIN:g} under the settle overflow {top:g}")
    if ex and round(SETTLE_DEFAULT - ex, 6) < EXIT_MARGIN:
        raise ValueError(f"gpl_td.post_td_exit {ex:g} must be at most {SETTLE_DEFAULT - EXIT_MARGIN:g} (keep threshold {SETTLE_DEFAULT:g} stays above the pass)")
    if not scoped:
        return {}
    out = {"top": float(top), "firm_small": int(fs), "growth": int(g)}
    if ex:
        out["exit"] = float(ex)          # absent key when off: the 11-26 spec dict, byte-identical
    return out


def firm_small(raw, tn):
    """FIRM small-cluster bound of type tn (0 without the flag or outside gpl_td.types).  tn is required: a per-type caller that
    forgets it must fail, never read the flag die-wide."""
    return spec(raw, _need(tn)).get("firm_small", 0)


def _need(tn):
    if not isinstance(tn, str) or not tn:
        raise ValueError(f"gpl_td: a per-type reading needs the partition type name, got {tn!r}")
    return tn


def post_gpl_regions(raw, tn):
    """C-TDREPAIR-REGION-MEAN 11-27: True when top_overflow_trigger is on.  OpenROAD tests the timing-driven trigger on the MEAN overflow of
    the top-level region and every odb region/group; the threshold wrapper alone still reads that mean when logic clusters larger than
    firm_small_clusters stay GPL regions.  gen_phys then exports OT_LOGIC_CLUSTER_POST_GPL=1 (regions created after global_placement)."""
    return bool(spec(raw, _need(tn)).get("top"))


def cell_growth_gate(raw, tn):
    """0 / 1 (report) / 2 (fail) cell growth gate of type tn; 0 without the flag or outside gpl_td.types."""
    return spec(raw, _need(tn)).get("growth", 0)


def cfg_lines(raw, tn):
    """config.mk lines of the flag (empty without it, or for a type tn outside gpl_td.types)."""
    s = spec(raw, _need(tn))
    out = []
    if s.get("top"):
        out += ["# C-GPL-TD-INFLATION (plan gpl_td.top_overflow_trigger): timing-driven repair only at a settled top-level overflow",
                f"export OT_GPL_TD_TOP = {s['top']:g}"]
    if s.get("exit"):
        out += ["# C-GPL-POSTTD-TAIL-SPARSE (plan gpl_td.post_td_exit): the timing-driven GPL call ends at this overflow (short post-TD tail)",
                f"export OT_GPL_TD_EXIT = {s['exit']:g}"]
    if s.get("growth"):
        out += ["# C-GPL-TD-INFLATION (plan gpl_td.cell_growth_gate): non-tap cell growth after GPL / place resize (1 report, 2 fail)",
                f"export OT_GPL_TD_GROWTH = {s['growth']}", f"export OT_GPL_TD_GROWTH_REL = {GROWTH_REL:g}"]
    return out


def apply(kd, raw, tn):
    """Install the Tcl hook and the config lines in kit dir ``kd`` (no-op without top_overflow_trigger / cell_growth_gate / post_td_exit, or for a
    type tn outside gpl_td.types)."""
    s = spec(raw, _need(tn))
    lines = cfg_lines(raw, tn)
    if not lines:
        return False
    kd = Path(kd)
    shutil.copyfile(Path(__file__).with_name(TCL), kd / TCL)
    ff = kd / "face_flops.tcl"
    ff.write_text(ff.read_text() + "\nsource /work/gpl_td.tcl\n")
    rel = kd / "face_flops_release.tcl"
    if s["growth"]:
        rel.write_text(rel.read_text() + "\nset ot_gpl_td_release 1\nsource /work/gpl_td.tcl\not_gpl_td_growth_gate post_resize\n")
    mk = kd / "config.mk"
    mk.write_text(mk.read_text().rstrip("\n") + "\n" + "\n".join(lines) + "\n")
    return True
