"""C-GPL-TD-INFLATION (CLASS-OWNERS-B 11-26): plan flag ``gpl_td`` (top-level plan dict, default OFF, absent = byte-identical kit).

    "gpl_td": {"top_overflow_trigger": 1, "firm_small_clusters": 1, "cell_growth_gate": 1}

Why (FABLE-FLOW-0847 A3): timing-driven GPL repair fires on the MEAN overflow of the top-level region and every odb region/group, so
a handful of tiny OT_LOGIC_CLUSTER regions (3-20 cells, finished at once) pull the mean under the first reweight threshold at
iteration 1 and repair_design buffers an unsettled placement (HEAD hd_lep0N fed00: +56,515 buffers, HPWL 1.30e7 -> 1.90e7).
  top_overflow_trigger  0 / 1 / settle overflow in (0, 1): timing-driven repair only on a placement whose TOP-LEVEL overflow has
                        settled (gpl_td.tcl: only the reweight thresholds at or under the settle overflow are kept).  1 = the
                        R-FLOW gpl_keep_overflow (0.25).
  firm_small_clusters   0 / 1 / N (3..20): logic_cluster_rects_um clusters of at most N movable cells (1 = 20) are seated FIRM at their
                        rect (logic_cluster.py), released for DPL, and are no GPL region.
  cell_growth_gate      0 / 1 / 2 ("report" / "fail"): non-tap cell count after GPL and after the place resize against
                        min(400k cap, pre-GPL count x 1.35), one OT_GPL_TD_GROWTH line per stage.
"""
import shutil
from pathlib import Path

KEYS = ("top_overflow_trigger", "firm_small_clusters", "cell_growth_gate")
SETTLE_DEFAULT = 0.25          # == gen_phys.RFLOW["gpl_keep_overflow"] (test_gpl_td asserts it)
SMALL_MIN, SMALL_MAX = 3, 20   # OWNER: seat 3-20 cell clusters FIRM
GROWTH_REL = 0.35
TCL = "gpl_td.tcl"


def spec(raw):
    """Normalised flag dict {top: settle overflow | 0, firm_small: max cells | 0, growth: 0|1|2}; {} when the plan has no gpl_td."""
    d = (raw or {}).get("gpl_td")
    if d is None:
        return {}
    if not isinstance(d, dict) or not d:
        raise ValueError("gpl_td must be a non-empty dict")
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
    return {"top": float(top), "firm_small": int(fs), "growth": int(g)}


def firm_small(raw):
    return spec(raw).get("firm_small", 0)


def cfg_lines(raw):
    """config.mk lines of the flag (empty without it)."""
    s = spec(raw)
    out = []
    if s.get("top"):
        out += ["# C-GPL-TD-INFLATION (plan gpl_td.top_overflow_trigger): timing-driven repair only at a settled top-level overflow",
                f"export OT_GPL_TD_TOP = {s['top']:g}"]
    if s.get("growth"):
        out += ["# C-GPL-TD-INFLATION (plan gpl_td.cell_growth_gate): non-tap cell growth after GPL / place resize (1 report, 2 fail)",
                f"export OT_GPL_TD_GROWTH = {s['growth']}", f"export OT_GPL_TD_GROWTH_REL = {GROWTH_REL:g}"]
    return out


def apply(kd, raw):
    """Install the Tcl hook and the config lines in kit dir ``kd`` (no-op without top_overflow_trigger / cell_growth_gate)."""
    s = spec(raw)
    lines = cfg_lines(raw)
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
