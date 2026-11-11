#!/usr/bin/env python3
"""QC cb* centre-pin clock event (DIE-QC-97 2026-11-10; COORD ruling: centre-pin form is the cb* hold form).

    python3 -I physical/die_plan/qwen_compute/delta_cb_centrepin_1110.py PLAN --out OUT --nk-lef NK.lef \
        --nl-lef NL.lef [--report REPORT.json]
    python3 -I physical/die_plan/qwen_compute/delta_cb_centrepin_1110.py PLAN --verify --nk-lef NK.lef --nl-lef NL.lef

MEASURED (read-only FF STA on the cb* post-CTS DBs, kw43 wave efdb36e864): cbn_q00__cldbcda913 -413.12 ps, cbf_q11
-372.13, cbx_q10__cl89936551 -343.80; every endpoint beyond the hold stop is a core-input pin of an NK/NL tile.  The
plan taps each tile on its old EDGE ck pin (cores/a0_nk_pins.json ck M4 457.824,668.076) while the signed view
(kw43-views nk_p1, LEF 103f6e68 / porous 53a7be5c) carries ck on M5 at the tile centre (228.972, 578.880): the kit
grows a 183.5 ps FF leg (3 BUFx16f + a 232-um net) from the tap to the real pin after the early-tap window, so the
tile clock arrives ~180 ps late against its own inputs.  The edge-pin sibling (cbx_q10__cl94a12200, edge-pin LEF)
closes the same structure at -230.66.

FORM: tap port ON the real pin (hard_cores[].clock_entry_access, the DIE-QC-91 / DIE-S81-85 form):
  NK (62 cores): pins_file -> cores/a0_nk_pins_ck1109.json (only the ck row differs: M5 228.972,578.880),
     clock_entry_access = VIA56 on the real M5 pin + M6 bar + VIA67 + M7 utility pin, tap xy = that M7 pin, tap
     insertion = signed NK pin-flop mean (TT 733.25 / FF 586.0, the 11-09 NK event; same routed DB as nk_p1).
     Entry stack access_v2 (porous): VIA56 (228.984, 578.708), M6 track y 578.708, VIA67 + M7 x 228.640 (child frame).
     The 11-09 access_v1 stack (M7 x 229.024) sits 48 nm from a real NK M7 wire (porous rect 228.928..228.960), so
     the kit's derived access abstract (footprint + one pitch, gen_phys.clock_entry_lef) would cut that wire out of
     the OBS; access_v2 keeps >= 64 nm + on M6 (156 nm) and M7 (80 nm), so the derived window cuts nothing.
  NL (2 cores, cbx_q10 types): the reviewed NL ck1107 event unchanged (access_v4 patch via
     tools/qwen_dv/qc_nl_clock_adoption_1551/reapply_event.py: pins_file cores/a0_nl_pins_ck1107.json, IDLE_UCK=1,
     clock_entry_access, tap 928.8,656.652, insertion TT 774.38 / FF 610.59).
Every access is proven against the given abstracts at apply time (--nk-lef / --nl-lef = the porous views the kits
stage): lef_clock_entry.entry_clear on the LEF as is, derive_access_lef cuts == 0, validate_access on the derived
text, and the tap on the M7 track.  --verify re-runs the same proof on an applied plan (e.g. after an NK re-sign
with the u_t21 H channel, DIE-QC-97 nk-hchan: its M6 band y 830..990 is clear of this stack at y 578.7).

Refuses a plan that already declares clock_entry_access or a ck pin table on any NK/NL core (event applied?)."""
import argparse
import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


G = _load("lef_clock_entry", "tools/die_plan/lef_clock_entry.py")
NKA = _load("qc_nk_prepare_access", "tools/qwen_dv/qc_nk_clock_adoption_1109/prepare_access.py")
NLE = _load("qc_nl_reapply_event", "tools/qwen_dv/qc_nl_clock_adoption_1551/reapply_event.py")

NK, NL = "qfd_tile_nk_a0c", "qfd_tile_nl_a0c"
SIZE = NKA.SIZE
OLD_PINS = {NK: "cores/a0_nk_pins.json", NL: "cores/a0_nl_pins.json"}
NEW_PINS = {NK: NKA.NEW_PINS, NL: NLE.NEW_PINS}
TOP = 7
MARGINS = {6: 0.064, 7: 0.064}          # gen_phys._access_margins on ASAP7 (one routing pitch)
r6 = NKA.r6
# access_v2 entry stack (child frame), chosen on the porous NK abstract (fp_search: all >= 64 nm clear windows)
VIA56 = (228.984, 578.708)
VIA67 = (228.640, 578.708)
_m5 = NKA.box(VIA56, NKA.ENC["VIA56"]["M5"])
FP_CHILD = {5: [(_m5[0], min(_m5[1], r6(NKA.PIN_CENTRE[1] - 0.024)), _m5[2], max(_m5[3], r6(NKA.PIN_CENTRE[1] + 0.024)))],
            6: [NKA.union(NKA.box(VIA56, NKA.ENC["VIA56"]["M6"]), NKA.box(VIA67, NKA.ENC["VIA67"]["M6"]))],
            7: [(r6(VIA67[0] - 0.016), r6(NKA.PIN_CENTRE[1] - NKA.M7_PIN_LEN / 2), r6(VIA67[0] + 0.016),
                 r6(NKA.PIN_CENTRE[1] + NKA.M7_PIN_LEN / 2))]}
INS = (NKA.SIGNOFF["tt"], NKA.SIGNOFF["ff"])
BUDGET = ("DIE-QC-97 11-10 cb* centre-pin event: signed NK vR7 eco2 re-sign pin-flop mean TT %.2f / FF %.1f (n 2584) "
          "at the real M5 ck pin via clock_entry_access (access_v2)" % INS)
sha = lambda b: hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def _cores(plan, mod):
    for tn, t in plan["partition_types"].items():
        for ci, c in enumerate(t.get("hard_cores", []) or []):
            if c.get("module") == mod:
                yield tn, ci, c


def _site(c):
    dx, dy = c.get("track_offset_um", [0.0, 0.0])
    return (r6(c["origin_um"][0] + dx), r6(c["origin_um"][1] + dy), c.get("orient", "R0"))


def prove(lef_text, master, access, site, tap):
    """the kit-side proof of one access on one abstract: -> receipt dict; raises on any failure."""
    fps = {int(k[1:]): [tuple(r) for r in v] for k, v in access["footprints_um"].items()}
    blocks, target, _ = G.geometry(lef_text, master, access["pin"], TOP, site)
    if not G.entry_clear(fps, blocks, target, TOP):
        raise ValueError(f"{master} {site}: entry footprint blocked on the abstract as is")
    new, cuts = G.derive_access_lef(lef_text, master, access, TOP, site, MARGINS)
    if cuts:
        raise ValueError(f"{master} {site}: derived access window cuts {cuts} OBS rect(s) (would hide real metal)")
    box = (r6(tap[0] - 0.016), r6(tap[1] - NKA.M7_PIN_LEN / 2), r6(tap[0] + 0.016), r6(tap[1] + NKA.M7_PIN_LEN / 2))
    G.validate_access(new, master, access, TOP, site, box)
    if not NKA.on_track(tap[0], "M7"):
        raise ValueError(f"{master} {site}: tap x {tap[0]} off the M7 track")
    # check.py pin-layer proof: M5 footprint centre on a plan M5 track, within half a pitch of the pin centre
    f5 = access["footprints_um"]["M5"][0]
    if not NKA.on_track(r6((f5[0] + f5[2]) / 2), "M5"):
        raise ValueError(f"{master} {site}: M5 footprint off track")
    return dict(entry_clear=True, derive_cuts=0, validate_access="PASS")


def nk_access(c):
    site = _site(c)
    T = lambda r: tuple(r6(v) for v in G.transform(r, SIZE, site))
    fps = {L: [T(r) for r in FP_CHILD[L]] for L in (5, 6, 7)}
    pin_t = T(NKA.PIN_RECT)
    tap = (r6((fps[7][0][0] + fps[7][0][2]) / 2), r6((pin_t[1] + pin_t[3]) / 2))
    old = T((NKA.OLD_PIN[1], NKA.OLD_PIN[2], NKA.OLD_PIN[1], NKA.OLD_PIN[2]))[:2]
    if not (fps[5][0][1] <= tap[1] <= fps[5][0][3]):
        raise ValueError("M5 footprint does not contain the pin centre")
    return site, {"pin": "ck", "footprints_um": {f"M{k}": [list(r) for r in v] for k, v in fps.items()}}, tap, old


def _tap(t, inst):
    ti = [i for i, x in enumerate(t["clock"]["taps"]) if x.get("name") == inst + ".ck" and x.get("kind") == "core"]
    if len(ti) != 1:
        raise ValueError(f"{inst}: expected one core tap {inst}.ck, got {len(ti)}")
    return ti[0], t["clock"]["taps"][ti[0]]


def apply(plan, nk_lef, nl_lef, with_nl=True):
    """-> (new plan, report).  nk_lef / nl_lef: abstract texts the access is proven on.  with_nl=False (unit tests
    only): skip the NL ck1107 patch, whose test ops name the two real cbx_q10 types."""
    for mod in (NK, NL):
        for tn, _, c in _cores(plan, mod):
            if c.get("clock_entry_access") or c.get("pins_file") != OLD_PINS[mod]:
                raise SystemExit(f"{tn}/{c['inst']}: clock_entry_access or pins_file {c.get('pins_file')} already "
                                 f"set (event applied?)")
    # NL: the reviewed ck1107 event, byte-for-byte (its own test ops guard the base)
    nl_ops = json.loads((NLE.ADO / "proposed_event.patch.json").read_text())
    N = NLE.apply(plan, nl_ops) if with_nl else copy.deepcopy(plan)
    rows = []
    for tn, ci, c in _cores(N, NL):
        ti, tp = _tap(N["partition_types"][tn], c["inst"])
        rec = prove(nl_lef, NL, c["clock_entry_access"], _site(c), tp["xy"])
        old_tp = plan["partition_types"][tn]["clock"]["taps"][ti]
        rows.append(dict(type=tn, inst=c["inst"], module=NL, orient=c.get("orient", "R0"), site=list(_site(c)),
                         old_xy=old_tp["xy"], new_xy=tp["xy"], old_insertion=[old_tp["insertion_ps"], old_tp["insertion_ff_ps"]],
                         new_insertion=[tp["insertion_ps"], tp["insertion_ff_ps"]], proof=rec,
                         footprints_um=c["clock_entry_access"]["footprints_um"]))
    # NK: access_v2 on every instance
    touched = set()
    for tn, ci, c in list(_cores(N, NK)):
        if c.get("params") or c.get("lef") or list(c["outline_um"]) != list(SIZE):
            raise ValueError(f"{tn}/{c['inst']}: unexpected params/lef/outline")
        site, access, tap, old = nk_access(c)
        t = N["partition_types"][tn]
        ti, tp = _tap(t, c["inst"])
        if any(abs(u - v) > 1e-6 for u, v in zip(tp["xy"], old)):
            raise ValueError(f"{tn}/{c['inst']}: tap {tp['xy']} != origin + offset + old edge pin {old}")
        rec = prove(nk_lef, NK, access, site, tap)
        rows.append(dict(type=tn, inst=c["inst"], module=NK, orient=site[2], site=list(site), old_xy=list(tp["xy"]),
                         new_xy=list(tap), old_insertion=[tp["insertion_ps"], tp["insertion_ff_ps"]],
                         new_insertion=list(INS), proof=rec, footprints_um=access["footprints_um"]))
        c["pins_file"] = NEW_PINS[NK]
        c["clock_entry_access"] = access
        tp.update(xy=list(tap), insertion_ps=INS[0], insertion_ff_ps=INS[1], budget_owner=BUDGET)
        touched.add(tn)
    _preserved(plan, N)
    types = sorted({r["type"] for r in rows})
    rep = dict(schema="opentallas.qc_cb_centrepin_event.v1", lane="DIE-QC-97", date="2026-11-10",
               base_plan_sha256=None, cores=len(rows), types=types,
               nk=dict(cores=sum(r["module"] == NK for r in rows), pins_file=NEW_PINS[NK], insertion=list(INS),
                       entry_stack_child=dict(via56=list(VIA56), via67=list(VIA67), m7_x=VIA67[0],
                                              m7_len_um=NKA.M7_PIN_LEN),
                       footprints_child_um={f"M{k}": [list(r) for r in v] for k, v in FP_CHILD.items()},
                       lef_sha256=sha(nk_lef)),
               nl=dict(cores=sum(r["module"] == NL for r in rows), pins_file=NEW_PINS[NL],
                       patch_sha256=sha((NLE.ADO / "proposed_event.patch.json").read_bytes()), lef_sha256=sha(nl_lef)),
               proof="per instance: entry_clear on the abstract as is, derive_access_lef cuts 0, validate_access on "
                     "the derived text, tap on the M7 track, M5 footprint on track", taps=rows,
               preservation="every other partition type and top-level key byte-identical; in the cb* types only the "
                            "NK/NL hard-core entries and their core taps differ (checked)")
    return N, rep


def _preserved(P, N):
    if {k: v for k, v in P.items() if k != "partition_types"} != {k: v for k, v in N.items() if k != "partition_types"}:
        raise ValueError("top-level key changed")
    if list(P["partition_types"]) != list(N["partition_types"]):
        raise ValueError("type order changed")
    for tn, a in P["partition_types"].items():
        b = N["partition_types"][tn]
        a2, b2 = copy.deepcopy(a), copy.deepcopy(b)
        for t2 in (a2, b2):
            insts = [c["inst"] for c in t2.get("hard_cores", []) or [] if c.get("module") in (NK, NL)]
            t2["hard_cores"] = [None if c.get("module") in (NK, NL) else c for c in t2.get("hard_cores", []) or []]
            if insts:
                t2["clock"]["taps"] = [None if x.get("name") in {i + ".ck" for i in insts} else x
                                       for x in t2["clock"]["taps"]]
        if a2 != b2:
            raise ValueError(f"{tn}: change outside the NK/NL cores and their taps")


def verify(plan, nk_lef, nl_lef):
    """the apply-time proof on an applied plan (after a view change): -> rows; raises on the first failure."""
    out = []
    for mod, lef in ((NK, nk_lef), (NL, nl_lef)):
        for tn, _, c in _cores(plan, mod):
            if not c.get("clock_entry_access"):
                raise ValueError(f"{tn}/{c['inst']}: no clock_entry_access (event not applied)")
            _, tp = _tap(plan["partition_types"][tn], c["inst"])
            out.append(dict(type=tn, inst=c["inst"], **prove(lef, mod, c["clock_entry_access"], _site(c), tp["xy"])))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--nk-lef", type=Path, required=True)
    ap.add_argument("--nl-lef", type=Path, required=True)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args(argv)
    src = a.plan.read_bytes()
    P = json.loads(src)
    nk_lef, nl_lef = a.nk_lef.read_text(), a.nl_lef.read_text()
    if a.verify:
        rows = verify(P, nk_lef, nl_lef)
        print(json.dumps(dict(verify="PASS", cores=len(rows), nk_lef_sha256=sha(nk_lef), nl_lef_sha256=sha(nl_lef))))
        return 0
    if not a.out:
        ap.error("--out required (new file)")
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: new output required")
    for mod in (NK, NL):
        pins = a.out.parent / NEW_PINS[mod]
        if not pins.is_file():
            raise SystemExit(f"{pins} missing: stage the plan cores/ (incl {NEW_PINS[mod]}) beside the output first")
    N, rep = apply(P, nk_lef, nl_lef)
    sep = (",", ":") if json.dumps(P, separators=(",", ":")).encode() + b"\n" == src else None
    out = (json.dumps(N, separators=sep) if sep else json.dumps(N, indent=1)).encode() + b"\n"
    a.out.write_bytes(out)
    rep.update(base_plan=str(a.plan), base_plan_sha256=sha(src), plan_output=str(a.out), plan_output_sha256=sha(out),
               pins_sha256={m: sha((a.out.parent / NEW_PINS[m]).read_bytes()) for m in (NK, NL)},
               nk_lef=str(a.nk_lef), nl_lef=str(a.nl_lef))
    if a.report:
        a.report.write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(cores=rep["cores"], types=len(rep["types"]), nk=rep["nk"]["cores"], nl=rep["nl"]["cores"],
                          out_sha256=rep["plan_output_sha256"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
