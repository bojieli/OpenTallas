#!/usr/bin/env python3
"""QC NK H channel plan event (DIE-QC-97, 2026-11-10; COORD ruling on the cbx split-view GRT, QC-FAIL-22 14:51).

    python3 -I physical/die_plan/qwen_compute/delta_nk_hchan_1110.py PLAN [--out OUT] [--report REPORT.json] \
        [--slice physical/die_plan/qwen_compute/cores/a0_slices/qfd_tile_nk_a0c.json]

MEASURED (cbx_q10__cl89936551 a25 split view cbx_split2, GRT-0116 after 30 extra iterations, 8,858 overflow):
8,835 of 8,858 markers are H over NK u_t21, 11 gcell rows over the full tile width at core-frame y 854-947, each
row exactly one track short.  The GRT guides of that run show 923 parent nets crossing u_t21 W<->E (x 77.76 ->
535.68, all three cuts x 150/306/460 equal), 906 of them on M6 (M1-M5 are blanket OBS in the NK view).  The demand
is 1.5 nets/um of core height outside the band and ~3 nets/um at core y 850-950 (W-face wire-buffer chains at
x ~72 -> centre channel x ~539), where the NK detail view also has its densest M6 (blocked share 0.222 vs 0.18).

GRT PRICE (private a25 copies on epyc4, same 4_cts.odb / config / 30 extra iterations as cbx_split2):
  B = M6 open in the band only: M6 derated 29.62M -> 29.86M (+0.8 %); overflow at iteration 5 the same as the
      split2 control (band markers 9,498 vs 9,219).  M6 over NK is capped by OpenROAD's transition-layer halving
      above the blanket M5 OBS (adjustTransitionLayers) and the parent M6 PG pair every 4.32 um, not by the bands.
  C = M5 + M6 open in the band: M6 derated 31.80M (+7.4 %), the halving is gone there; band markers at iteration 5
      9,219 -> 106.  (Final numbers: see the DIE-QC-97 report.)

FORM: every qfd_tile_nk_a0c hard core (one master, so every instance in every type) reserves M5 and M6 at core
frame y SPAN_UM for the parent (hard_cores[].route_channels, core_route_channel.py): the NK kit gets M5 and M6
routing obstructions there (master-plan slice keepout route_channel0; its M5 PG pins are pins, not routing, and
stay), its exported abstract carries no M5/M6 OBS in the band (abstract_detail splice of M5-M7), and parent GRT
views leave the band open.  MEASURED on the signed NK routed DEF (dq96/nk_vr7n_eco2/i1 6_final.def): NK's own
signal wire in the band is M5 35.4 mm (2.3 % of the band's M5 tracks) and M6 83.5 mm (7.3 %), 118.9 mm of
2.66 m NK signal wire (4.5 %).  Parent demand in the span is ~390 nets against 2,500 M6 tracks (160 um / 0.064).
Cells still place under the band; M1-M4 and M7 of the core are unchanged.  NK must be re-routed and re-signed
with the obstruction (the abstract changes only after that re-sign).

Idempotent guard: refuses a plan that already declares route_channels on qfd_tile_nk_a0c.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
import core_route_channel as CRC  # noqa: E402

MODULE = "qfd_tile_nk_a0c"
SPAN_UM = [830.0, 990.0]
LAYERS = ["M5", "M6"]
REASON = ("DIE-QC-97 11-10 NK H channel: parent E-W nets over NK (cbx_split2 GRT-0116, 8,835 H markers at core y "
          "854-947, ~3 nets/um); M5+M6 reserved for the parent, NK routes off them")


def apply(plan):
    """plan with the NK route channel on every qfd_tile_nk_a0c hard core; (plan, report)."""
    p = json.loads(json.dumps(plan))
    ch = dict(dir="EW", span_um=list(SPAN_UM), layers=list(LAYERS), reason=REASON)
    hit, outline = [], None
    for tn, t in sorted(p["partition_types"].items()):
        for h in t.get("hard_cores", []) or []:
            if h.get("module") != MODULE:
                continue
            if h.get("route_channels"):
                raise SystemExit(f"{tn}/{h['inst']}: route_channels already declared (event applied?)")
            if outline is not None and list(h["outline_um"]) != outline:
                raise SystemExit(f"{tn}/{h['inst']}: {MODULE} outline {h['outline_um']} != {outline}")
            outline = list(h["outline_um"])
            h["route_channels"] = [dict(ch)]
            hit.append((tn, h))
    if not hit:
        raise SystemExit(f"no {MODULE} hard core in the plan")
    keep = CRC.slice_keepouts(hit, outline)        # also checks span inside the core and one list per module
    rep = dict(schema="opentallas.qc_nk_hchan_event.v1", module=MODULE, channel=ch, outline_um=outline,
               core_rect_um=keep[0]["rect_um"], instances=sorted(f"{tn}/{h['inst']}" for tn, h in hit),
               types=sorted({tn for tn, _ in hit}), slice_keepouts=keep)
    return p, rep


def apply_slice(sl, rep):
    """the module's master-plan slice with the route_channel keepouts (replacing earlier ones)."""
    if sl.get("module") != MODULE or sl.get("kind") != "core":
        raise SystemExit(f"slice is not the {MODULE} core slice")
    if [float(v) for v in sl["outline_um"]] != [float(v) for v in rep["outline_um"]]:
        raise SystemExit("slice outline differs from the plan core outline")
    s = json.loads(json.dumps(sl))
    s["keepouts"] = [k for k in s.get("keepouts", []) if k.get("kind") != "route_channel"] + rep["slice_keepouts"]
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--report")
    ap.add_argument("--slice", help="core master-plan slice JSON of qfd_tile_nk_a0c to update in place")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    p, rep = apply(plan)
    Path(a.out or a.plan).write_text(json.dumps(p, indent=1) + "\n")
    if a.slice:
        sp = Path(a.slice)
        sp.write_text(json.dumps(apply_slice(json.loads(sp.read_text()), rep), indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(instances=len(rep["instances"]), types=len(rep["types"]), rect=rep["core_rect_um"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
