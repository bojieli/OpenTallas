#!/usr/bin/env python3
"""HBM plan event SPB-PMA-PADS-1108 (lane HBM-SPB-IO, COORD 18:4x, DIE-HBM-93 final-plan open item (a)).

PORT_BIND FAIL extra 545 on the five SerDes-bearing HBM types (q_spb0, q_spb0__physical_v1, NE_io, vsN0, NW_io; the split
ot_pdie_serdes__p37 form): the bind exports the PMA line side as bound-only die-IO ports of the kit wrapper,
io_lk_<lane>_pma_rx (544 bits) and io_lk_<lane>_pma_rck (1), and the plan declares no type pads for them.

One plan event, no pin cycles, S81-SERDES-PHY-3 form (physical/die_plan/s81/delta_kp4_srams_1031.py):
  * io_lk_<lane>_pma_rx: type pad with macro_pin {inst: <rx_bm3_rest physical_inst>, pin: pma_rx}: the kit top pin sits ON
    the hard core's own contract LEF pin (gen_phys.pad_bumps/bump_pin_sites), no face register, face_guard bump proof.
  * io_lk_<lane>_pma_rck: type pad clock:true with an explicit clock.pad_clock row (a macro_pin pad may not be a clock, and
    the contract rx_bm3_rest LEF has no pma_rck pin; pma_rck reaches rck_clk on the rest core, clk on the three BM natives
    and on the KP4 channel through the wires-only p37 glue).  Pin on M7 in the bm/rest macro channel, PG clear
    (gen_phys._snap_tap), near the five sinks, cdc synchronized like the S81 serdes pad clock (same ot_pdie_serdes RTL).
  * PMA-EYE-1108 rows are NOT applied here: its rx min delay (+T/4 = 208.25 ps) fails the sdc_lint seam-hold limit on
    every input (-135 ps), so the rx pad keeps the generic seam input delay, as the S81 serdes pads do.

The lane name of a type's pads comes from the as-built bind, not the plan instance name (q_spb0__physical_v1 binds plan
u_lk_S0 from as-built lk_S3); the table below is checked against the bind's kit wrapper ports with --bind.  Plan content,
floorplan, hard cores and pin counts other than the new pads are unchanged.  A second run is refused.

    delta_spb_pma_pads_1108.py PLAN_DIR OUT_DIR [--bind BIND_DIR]   (OUT_DIR = new hard-linked copy; rewrites the plan files)
    delta_spb_pma_pads_1108.py check PLAN_JSON                       (schema-valid, the five types, pads exact)
"""
import argparse
import copy
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3] / "tools" / "die_plan"))

EVENT = "SPB-PMA-PADS-1108"
LANE = "HBM-SPB-IO"
# type -> as-built lane whose PMA line side the type's bound wrapper exports (bind asbuilt p37su5 + sub_core_leaf_variants)
TYPES = {"q_spb0": "lk_S0", "q_spb0__physical_v1": "lk_S3", "NE_io": "lk_N2", "vsN0": "lk_S1", "NW_io": "lk_N0"}
REST = "ot_pdie_serdes_rx_bm3_rest"
BM = "ot_pdie_serdes_rx_bm_native"
CHN = "ot_s81_kp4_dchn"
RCK_SINKS = [{"module": CHN, "pin": "clk"}, {"module": REST, "pin": "rck_clk"}, {"module": BM, "pin": "clk"}]
RCK_SOURCE = ("far-die PMA TX clock as recovered by the receive CDR (ot_pdie_serdes.sv pma_rck), plesiochronous to the die "
              "clock at the die period")
CDC_EVIDENCE = ("ot_pdie_serdes.sv pma_rck -> clk only through ot_s81_rate_match (gray-pointer FIFO, 2-flop synchronisers "
                "both ways, KP4 SRAM 1r1w2c wclk=pma_rck rclk=clk), per-domain reset synchronisers and 2-flop status "
                "synchronisers, same form as the S81 serdes io_pma_rck pad clock; p37 split keeps that crossing inside "
                "the rx_bm3_rest core")
CHANNEL_MARGIN_UM = 0.5        # a clock entry is not over or at the edge of a macro (kit_contract.clock_entry_clear)


def bound_path(physical_inst):
    """the kit's placed path of a hard core: gen_phys projects plan physical_inst through bound_macro_paths before
    pad_bumps (u_lk_S0.u_fcore... -> u_bound.u_u_lk_S0.u_fcore...), so macro_pin names that path, as S81 does."""
    return physical_inst if physical_inst.startswith("u_bound.") else "u_bound.u_" + physical_inst


def pad_names(lane):
    return f"io_{lane}_pma_rx", f"io_{lane}_pma_rck"


def box(c):
    ox, oy = c.get("track_offset_um", [0.0, 0.0])
    x, y = c["origin_um"][0] + ox, c["origin_um"][1] + oy
    w, h = c["outline_um"]
    return x, y, x + w, y + h


def rck_site(P, t, tn):
    """xy of the pad clock: M7 (partition top signal layer) in the channel between the BM native column and the rest
    core, the bm0..2 column's vertical centre, PG clear (gen_phys._snap_tap), never over a macro."""
    import gen_phys as G
    cores = t["hard_cores"]
    rest = [c for c in cores if c.get("physical_master") == REST]
    bms = [c for c in cores if c.get("physical_master") == BM]
    if len(rest) != 1 or len(bms) != 3:
        raise SystemExit(f"{tn}: expected one {REST} and three {BM} hard cores ({len(rest)}, {len(bms)})")
    rest_box, bm_boxes = box(rest[0]), [box(c) for c in bms]
    x0, x1 = max(b[2] for b in bm_boxes), rest_box[0]
    if x1 - x0 < 4 * CHANNEL_MARGIN_UM:
        raise SystemExit(f"{tn}: bm/rest channel {x0:g}..{x1:g} too narrow for a clock entry")
    x, y = (x0 + x1) / 2, (min(b[1] for b in bm_boxes) + max(b[3] for b in bm_boxes)) / 2
    xs, ys = G._snap_tap(P, x, y)
    if not (x0 + CHANNEL_MARGIN_UM <= xs <= x1 - CHANNEL_MARGIN_UM):
        raise SystemExit(f"{tn}: snapped pma_rck entry x {xs} left the bm/rest channel {x0:g}..{x1:g}")
    for c in cores:
        b = box(c)
        if b[0] - CHANNEL_MARGIN_UM <= xs <= b[2] + CHANNEL_MARGIN_UM and b[1] - CHANNEL_MARGIN_UM <= ys <= b[3] + CHANNEL_MARGIN_UM:
            raise SystemExit(f"{tn}: pma_rck entry ({xs},{ys}) over or at the edge of {c.get('inst')}")
    return [round(xs, 4), round(ys, 4)]


def apply(raw, P=None):
    """Return (new_raw, rows).  raw: the plan dict; P: a schema.Plan of raw (built when None)."""
    import pad_clock  # noqa: F401
    import schema as S
    out = copy.deepcopy(raw)
    P = S.Plan(out) if P is None else P
    rows = []
    period = float(P.die["period_ps"])
    for tn, lane in TYPES.items():
        t = out["partition_types"][tn]
        rx, rck = pad_names(lane)
        if t.get("pads"):
            raise SystemExit(f"{tn}: type pads already present (second run refused)")
        clock = t["clock"]
        if "pad_clock" in clock:
            raise SystemExit(f"{tn}: clock.pad_clock already present (second run refused)")
        rest = [c for c in t["hard_cores"] if c.get("physical_master") == REST]
        if len(rest) != 1 or not rest[0].get("physical_inst"):
            raise SystemExit(f"{tn}: no single rest core with a physical_inst")
        xy = rck_site(P, t, tn)
        layer = P.layer_budget["partition_signal_max"]
        t["pads"] = [
            dict(name=rx, dir="in", width=544, macro_pin=dict(inst=bound_path(rest[0]["physical_inst"]), pin="pma_rx")),
            dict(name=rck, dir="in", width=1, clock=True),
        ]
        clock["pad_clock"] = dict(pins=[dict(
            name=rck, dir="in", period_ps=period, source=RCK_SOURCE, layer=layer, xy_um=xy,
            sink_pins=[dict(s) for s in RCK_SINKS], cdc="synchronized", cdc_evidence=CDC_EVIDENCE)])
        rows.append(dict(type=tn, lane=lane, pad_rx=rx, pad_rck=rck, rck_xy_um=xy, rest_inst=bound_path(rest[0]["physical_inst"])))
    return out, dict(event=EVENT, lane=LANE, types=list(TYPES), pad_rows=rows, pin_cycles=0)


def check_bind(bind_dir, rows=()):
    """Every type's wrapper in the bind exports exactly the two ports the event declares (width 544 and 1), and holds
    the bound leaf instance that macro_pin names (u_bound.<leaf>...)."""
    errors = []
    leaf = {r["type"]: r["rest_inst"].split(".")[1] for r in rows}
    for tn, lane in TYPES.items():
        f = Path(bind_dir) / "rtl" / f"hbm_arch_{tn}.sv"
        txt = f.read_text() if f.is_file() else ""
        for name, w in zip(pad_names(lane), (544, 1)):
            m = re.search(r"input\s+wire\s+\[(\d+):0\]\s+" + re.escape(name) + r"\b", txt)
            if m is None or int(m.group(1)) != w - 1:
                errors.append(f"{tn}: {name} [{w - 1}:0] not exported by {f}")
        if tn in leaf and not re.search(r"\b" + re.escape(leaf[tn]) + r"\s*\(", txt):
            errors.append(f"{tn}: bound leaf {leaf[tn]} not in {f}")
    if errors:
        raise SystemExit("bind check failed:\n" + "\n".join(errors))
    return [dict(type=tn, lane=lane, bound=True) for tn, lane in TYPES.items()]


def fsha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(plan_dir, out_dir, bind):
    plan_dir, out_dir = Path(plan_dir).resolve(), Path(out_dir).resolve()
    if out_dir.exists():
        raise SystemExit(f"{out_dir} exists")
    text = (plan_dir / "die_plan.json").read_text()
    raw = json.loads(text)
    if json.dumps(raw, indent=1) + "\n" != text:
        raise SystemExit("plan is not canonical indent=1 JSON: refusing (would rewrite unrelated bytes)")
    new, receipt = apply(raw)
    bind_rows = check_bind(bind, receipt["pad_rows"]) if bind else None
    shutil.copytree(plan_dir, out_dir, copy_function=os.link, symlinks=True)   # hard-linked copy, new files replace links
    for name in ("die_plan.json", "die_plan.json.gz", "SHA256SUMS", "README.md"):
        (out_dir / name).unlink()
    (out_dir / "die_plan.json").write_text(json.dumps(new, indent=1) + "\n")
    with gzip.GzipFile(str(out_dir / "die_plan.json.gz"), "wb", mtime=0) as gz:
        gz.write((json.dumps(new, indent=1) + "\n").encode())
    sha_in = hashlib.sha256(text.encode()).hexdigest()
    sha_out = fsha(out_dir / "die_plan.json")
    receipt.update(plan_in=str(plan_dir / "die_plan.json"), sha_in=sha_in, sha_out=sha_out, bind_check=bind_rows)
    (out_dir / "spb_pma_pads_1108_event.json").write_text(json.dumps(receipt, indent=1) + "\n")
    readme = (plan_dir / "README.md").read_text() + (
        f"\n## {EVENT} ({LANE} 2026-11-08)\nplan_final2 ({sha_in[:12]}) + {EVENT}: type pads io_lk_<lane>_pma_rx (macro_pin on "
        f"rx_bm3_rest pma_rx) and io_lk_<lane>_pma_rck (pad clock, M7 in the bm/rest channel, cdc synchronized) on "
        f"{', '.join(TYPES)}; 0 pin cycles; die_plan.json sha256 {sha_out[:12]}. "
        f"Receipt spb_pma_pads_1108_event.json.\n")
    (out_dir / "README.md").write_text(readme)
    old = {}
    for line in (plan_dir / "SHA256SUMS").read_text().splitlines():
        sha, _, name = line.partition("  ")
        old[name] = sha
    for name in ("die_plan.json", "die_plan.json.gz", "README.md", "spb_pma_pads_1108_event.json"):
        old[name] = fsha(out_dir / name)
    (out_dir / "SHA256SUMS").write_text("".join(f"{sha}  {name}\n" for name, sha in sorted(old.items())))
    return receipt


def check(plan_json):
    import schema as S
    import pad_clock as PC
    raw = json.loads(Path(plan_json).read_text())
    P = S.Plan(raw)
    errs = S.validate(raw)
    assert not errs, errs[:5]
    for tn, lane in TYPES.items():
        t = raw["partition_types"][tn]
        rx, rck = pad_names(lane)
        assert [p["name"] for p in t["pads"]] == [rx, rck], tn
        assert [p["name"] for p in PC.pins(P, tn)] == [rck], tn
    return "OK"


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "check":
        print(check(argv[1]))
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--bind")
    a = ap.parse_args(argv)
    r = run(a.plan_dir, a.out_dir, a.bind)
    print(f"{EVENT}: {len(r['pad_rows'])} types, sha_out {r['sha_out'][:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
