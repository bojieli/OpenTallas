#!/usr/bin/env python3
"""HEAD-92 11-10 form ZLP: put zero-logic hold pads into a generated kit (stage resume from CTS).

zl_hold_pad.tcl (PRE_CTS) keeps ONE HB4xp67 in front of every register / SRAM input whose driver reaches a register
Q/QN through at most OT_ZLP_DEPTH BUF/INV cells.  Such hops have clk-Q + one INV (~43 ps FF) of data delay, below
25 ps hold uncertainty + ~14 ps hold time + leaf / tap skew, so they are the FF hold class that GRT hold repair chases
for hours (hd_mesh a2 0432aced49ac: 8,700 -> 526 endpoints in 3 h, 1,754 after route).

  kit_zl_hold_pad.py KIT [--depth 4] [--slew-margin 20] [--cap-margin 20] [--report-only]

Writes KIT/zl_hold_pad.tcl, sources it first in KIT/pre_cts.tcl (kept copy pre_cts.tcl.pre_zlp), appends the OT_ZLP
exports to KIT/config.mk and writes KIT/resume.json {"start": "cts"} unless one exists.  Idempotent.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TCL = HERE / "zl_hold_pad.tcl"
MARK = "# OT_ZLP kit_zl_hold_pad.py"
SRC = "source /work/zl_hold_pad.tcl"


CLASS_RECIPE = HERE / "zl_hold_class" / "qc_seam_classes.json"


def class_regex(recipe=None, names=None):
    """Joined Tcl regexp of the recipe classes (all, or the named ones)."""
    rec = json.loads(Path(recipe or CLASS_RECIPE).read_text())
    cl = rec["classes"]
    pick = list(cl) if not names else list(names)
    bad = [n for n in pick if n not in cl]
    if bad:
        raise SystemExit(f"kit_zl_hold_pad: unknown class {bad}; recipe has {sorted(cl)}")
    return "|".join(f"({cl[n]})" for n in pick)


def check_recipe(kit, recipe=None, force=False):
    """applies_to / exclude_if of the class recipe, enforced: the kit family must be listed and its base signoff reasons must not name an excluded gate."""
    import re
    rec = json.loads(Path(recipe or CLASS_RECIPE).read_text())
    ap = rec.get("applies_to", {})
    kit = Path(kit)
    name = kit.name if kit.name != "" else kit.resolve().name
    fam = re.sub(r"__.*", "", name)
    fam = re.sub(r"_[0-9]{10}$", "", fam)
    why = []
    if ap.get("families") and fam not in ap["families"]:
        why.append(f"family {fam} not in applies_to")
    so = kit / "signoff" / "signoff.json"
    if so.is_file():
        try:
            reasons = str(json.loads(so.read_text()).get("reasons", ""))
        except ValueError:
            reasons = ""
        for ex in ap.get("exclude_if", []):
            if re.search(r"\b" + re.escape(ex) + r"\b", reasons):
                why.append(f"base sign-off fails {ex}")
    if why and not force:
        raise SystemExit("kit_zl_hold_pad: " + "; ".join(why) + " (--force overrides)")
    return why


def apply(kit: Path, depth=4, slew=20, cap=20, report_only=False, class_re=None):
    kit = Path(kit)
    pre = kit / "pre_cts.tcl"
    cfg = kit / "config.mk"
    if not pre.is_file() or not cfg.is_file():
        raise SystemExit(f"kit_zl_hold_pad: {kit} has no pre_cts.tcl / config.mk")
    shutil.copyfile(TCL, kit / "zl_hold_pad.tcl")
    text = pre.read_text()
    if SRC not in text:
        shutil.copyfile(pre, kit / "pre_cts.tcl.pre_zlp")
        pre.write_text(f"{MARK}: zero-logic hold pads before the tap trees\n{SRC}\n{text}")
    c = cfg.read_text()
    if MARK not in c:
        lines = [MARK, "export OT_ZLP = 1", f"export OT_ZLP_DEPTH = {int(depth)}"]
        if report_only:
            lines.append("export OT_ZLP_REPORT_ONLY = 1")
        if class_re:
            lines.append("export OT_ZLP_CLASS = " + class_re.replace("$", "$$"))
        if slew is not None:
            lines.append(f"export SLEW_MARGIN = {int(slew)}")
        if cap is not None:
            lines.append(f"export CAP_MARGIN = {int(cap)}")
        cfg.write_text(c.rstrip("\n") + "\n" + "\n".join(lines) + "\n")
    rs = kit / "resume.json"
    if not rs.exists():
        rs.write_text(json.dumps({"start": "cts"}) + "\n")
    return {"kit": str(kit), "pre_cts": SRC in pre.read_text(), "resume": json.loads(rs.read_text())}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit")
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--slew-margin", type=int, default=20)
    ap.add_argument("--cap-margin", type=int, default=20)
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--qc-seam", nargs="?", const="all", metavar="CLASS[,CLASS]",
                    help="restrict the pads to the QC seam classes of zl_hold_class/qc_seam_classes.json (all, or a comma list)")
    ap.add_argument("--force", action="store_true", help="skip the applies_to / exclude_if check of --qc-seam")
    ap.add_argument("--class-regexp", help="restrict the pads to capture registers whose instance name matches this Tcl regexp")
    a = ap.parse_args(argv)
    cre = a.class_regexp
    if a.qc_seam:
        check_recipe(a.kit, force=a.force)
        cre = class_regex(names=None if a.qc_seam == "all" else a.qc_seam.split(","))
    print(json.dumps(apply(Path(a.kit), a.depth, a.slew_margin, a.cap_margin, a.report_only, cre)))


if __name__ == "__main__":
    sys.exit(main())
