#!/usr/bin/env python3
"""DIE-QC-97 st_b 11-10: clock.tap_group (gen_phys.tap_group_exports -> OT_TAP_GROUP_RE, the clock_taps.tcl group form)
on the QC st_b types whose routed TT STA shows a TAP SPLIT inside one compact station block.

MEASURED (read-only STA on copies, epyc4 /srv/opentallas-scratch2/claude/dq97/{stb1pv0q,stbv2w/sta}):
  sle_st_b_v1__pv0e7b1dcc (sl_E2_st_b) C: 25 paths in r4/r7 g_l7[0].u_lo.g_exact.u_d, launch/capture 10-20 um apart on
      clk_t5/clk_t9 (r4) and clk_t17/clk_t19 (r7); the tap window forced 227-417 ps of HB4 hold buffers onto the setup
      paths (logic 417-556 ps); D: r4 g_sc[1] mul, clk_t8 -> clk_t11, skew 87 ps, ~12 um.
  slw_st_b_v2__pvc2ec5bfb (sl_W5_st_b) D: 11 paths in r5 g_l7[0].u_hi / g_l9[0].u_add, clk_t8/t9 -> clk_t10, HB 227-368
      ps, all 11 close without the HB; C: 51 paths inside r7 g_sc[0/1].u_mul (front half at the station on clk_t15, back
      half at the left face on clk_t13/t14, skew 90-154 ps), all 51 close at zero launch-capture skew (worst +79.8 ps).
clock.tap_pair_affinity {} was tried first (COORD ruling): emulated on the v1 3_place.odb with the kit's own clock_taps.tcl
it changes 0 clock pins (13 taps above cap at start = donate only; largest component 3951, 69 frozen oversized).  The group
form on the same DBs: v1 32 groups, 25 were split, 0 split now; W5 24 (adders) groups, 16 split, 0 split now.
Keyed on station math instance paths only (no relay / synthesized names).  Opt-in type key; other types unchanged."""
import argparse
import json
from pathlib import Path

RE = (r"(u_u_r[4-7]\.(?:g_l[79]\\?\[[0-9]+\\?\]\.u_(?:lo|hi|add)\.g_exact\.u_d"
      r"|g_sc\\?\[[0-9]+\\?\]\.u_mul\.genblk1\.g_exact\.u_d))[/.]")
TYPES = ("sle_st_b_v1__pv0e7b1dcc", "slw_st_b_v2__pvc2ec5bfb")


def apply(raw):
    for tn in TYPES:
        t = raw["partition_types"][tn]
        assert {"u_r4", "u_r5", "u_r6", "u_r7"} <= {c["inst"] for c in t["contents"]}, tn
        ck = t.setdefault("clock", {})
        want = {"re": RE}
        if "tap_group" in ck:
            assert ck["tap_group"] == want, tn + ": type already has a different clock.tap_group: merge by hand"
            continue
        ck["tap_group"] = want
    return raw


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("output")
    a = p.parse_args()
    text = Path(a.input).read_text()
    base = json.loads(text)
    raw = apply(json.loads(text))
    for tn in TYPES:   # every key outside the edits is unchanged
        b, r = dict(base["partition_types"][tn]), dict(raw["partition_types"][tn])
        bc, rc = dict(b.pop("clock", {})), dict(r.pop("clock", {}))
        rc.pop("tap_group", None); bc.pop("tap_group", None)
        assert b == r and bc == rc, tn
    assert {k: v for k, v in base.items() if k != "partition_types"} == {k: v for k, v in raw.items() if k != "partition_types"}
    assert {k for k in base["partition_types"] if base["partition_types"][k] != raw["partition_types"][k]} <= set(TYPES)
    Path(a.output).write_text(_style(text, base)(raw))


def _style(text, P):
    """The base file's own JSON style when a plain dump reproduces it, else compact (type_safe_event._style rule)."""
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n"):
        if f(P) == text:
            return f
    return lambda p: json.dumps(p, separators=(",", ":")) + "\n"


if __name__ == "__main__":
    main()
