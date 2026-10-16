#!/usr/bin/env python3
"""VMDEL v6 exact literal-pin plan for the H-DIE 10:25 grant (el1011-hbmdie.log 2026-10-16T10:27).

Grant: clk_cap single entry on the S face mid x=128.508 (M5, actual track grid phase 0.012 / pitch 0.048);
body clk entry moved from the W corner (y 40.6) to N-mid on the actual grid; rst_n pin flop + plain status pin
flops kept (they are in the v6 source 25a390064).  Outline 257.04 x 151.2 unchanged.

Checks (all hard asserts, results in check.json):
  * literal coverage: every declared port bit of ot_hbm_svc_vmdel_lane_v6 exactly once (physical_request ports);
  * actual grid: every M4 (W/E) / M5 (N/S) centre = 0.012 + 0.048 k (actual ODB readback, dense/tail/H7/F20);
  * notch: no N/S M5 pin overlaps an M5 PG stripe pair of pdn.tcl (width 0.12, spacing 0.072, pitch 5.4, offset
    0.300 from the 2.16 core origin; both the edge- and the centre-offset reading are excluded);
  * spacing: >= 0.096 um between signal pins, >= 0.192 um around a clock pin; >= 4.32 um off the corners;
  * cut: whole-face bits*0.096/length <= 0.60 and worst 10-um window <= 0.60.
The consuming gate must still read back the actual ODB pin rectangles (pre_route_gate floorplan.pin_geometry).
"""
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = "rtl/hbm_accel/loader/service_native/split/ot_hbm_svc_static_vm_delivery_split_v6.sv"
REQ = "results/rtl/hbm_vmdel_v6_0833/physical_request.json"
OUT = ROOT / "results/arch/hbm_die_v16/vmdel_v6_grant_1045"
W, H = 257.04, 151.2
PH, PITCH, PIN_HALF = 0.012, 0.048, 0.036     # actual track phase/pitch; pin half-width incl. min spacing guard
EDGE = 4.32
CLK = {"clk_cap": ("S", 128.508), "clk": ("N", 128.508)}
ORDER = {  # face -> ports in along-face order (low -> high), as the closed v5b kit
    "S": ["fill_v_i", "fill_bank_i", "fill_slot_i", "fill_epoch_i", "fill_data_i"],
    "N": ["dq"],
    "W": ["rst_n", "bank_id", "begin_v_i", "begin_bank_i", "begin_epoch_i", "start_i", "start_bank_i",
          "start_epoch_i", "start_base_sector_i", "full0_all", "full1_all", "pcbad_all"],
    "E": ["full0", "full1", "pcbad", "block_ready", "busy", "fault"],
}
LAYER = {"N": "M5", "S": "M5", "W": "M4", "E": "M4"}
# along-face bands: W inputs (all on clk_cap) sit low beside the S-mid clk_cap entry (worst reach (0,40) ~168 um vs the
# S corners ~124 um); E outputs (all on clk) sit high beside the N-mid body entry.  N/S use the whole face.
BAND = {"W": (EDGE, 40.0), "E": (H - 30.0, H - EDGE)}


def pg_blocked(pos):
    """M5 PG stripe pair (pdn.tcl): stripes at core0+0.300+5.4k (+0.192), width 0.12; both offset readings."""
    core0 = 2.16
    k0 = math.floor((pos - core0) / 5.4) - 1
    for k in range(k0, k0 + 3):
        for base in (core0 + 0.300 + 5.4 * k, core0 + 0.300 + 5.4 * k - 0.06):
            for a, b in ((base, base + 0.12), (base + 0.192, base + 0.312)):
                if pos + PIN_HALF > a and pos - PIN_HALF < b:
                    return True
    return False


def on_grid(pos):
    k = (pos - PH) / PITCH
    return abs(k - round(k)) < 1e-6


def main():
    req_raw = subprocess.check_output(["git", "-C", str(ROOT), "show", "25a390064:" + REQ])
    req = json.loads(req_raw)
    src_raw = (ROOT / SRC).read_bytes()
    assert req["top"] == "ot_hbm_svc_vmdel_lane_v6" and req["outline_um"] == [W, H]
    ports = req["ports"]
    assert set(ports) == set(CLK) | {p for v in ORDER.values() for p in v}, set(ports) ^ (set(CLK) | {p for v in ORDER.values() for p in v})
    pos = {}
    for n, (f, c) in CLK.items():
        assert on_grid(c) and (f in "WE" or not pg_blocked(c)), (n, c)
        pos[n] = (f, c)
    faces = {}
    for f, names in ORDER.items():
        bits = [n if ports[n]["bits"] == 1 else f"{n}[{i}]" for n in names for i in range(ports[n]["bits"])]
        length = W if f in "NS" else H
        clocks = [c for (cf, c) in CLK.values() if cf == f]
        avail = []
        lo, hi = BAND.get(f, (EDGE, length - EDGE))
        for k in range(math.ceil((lo - PH) / PITCH), math.floor((hi - PH) / PITCH) + 1):
            p = round(PH + k * PITCH, 6)
            if f in "NS" and pg_blocked(p):
                continue
            if any(abs(p - c) < 0.192 - 1e-9 for c in clocks):
                continue
            if not avail or p - avail[-1] >= 0.096 - 1e-9:
                avail.append(p)
        assert len(avail) >= len(bits), (f, len(bits), len(avail))
        picks = [avail[round(i * (len(avail) - 1) / (len(bits) - 1))] for i in range(len(bits))] if len(bits) > 1 else [avail[len(avail) // 2]]
        assert len(set(picks)) == len(picks)
        for b, p in zip(bits, picks):
            pos[b] = (f, p)
        allc = sorted(picks + clocks)
        assert all(b - a >= 0.096 - 1e-9 for a, b in zip(allc, allc[1:]))
        win = 0
        for i, a in enumerate(allc):
            j = i
            while j < len(allc) and allc[j] < a + 10.0:
                j += 1
            win = max(win, (j - i) * 0.096 / 10.0)
        faces[f] = dict(bits=len(allc), length_um=length, layer=LAYER[f], whole_face_cut=round(len(allc) * 0.096 / length, 6),
                        worst_10um_window_cut=round(win, 6), span_um=[allc[0], allc[-1]])
        assert faces[f]["whole_face_cut"] <= 0.60 and win <= 0.60, faces[f]
    expected = {n if v["bits"] == 1 else f"{n}[{i}]" for n, v in ports.items() for i in range(v["bits"])}
    assert set(pos) == expected, (expected - set(pos), set(pos) - expected)
    assert all(on_grid(p) for _, p in pos.values())
    assert not any(pg_blocked(p) for f, p in pos.values() if f in "NS")
    OUT.mkdir(parents=True, exist_ok=True)
    lines = ["# VMDEL v6 exact literal pins (H-DIE grant 2026-10-16 10:25: clk_cap S-mid 128.508 M5, body clk N-mid).",
             "# Generated by tools/hbm_v15_harden/vmdel_v6_pin_grant_1045.py; actual ODB readback mandatory.",
             "source /src/physical/common_flow/assigned_pin_exact.tcl"]
    for n, (f, p) in sorted(pos.items()):
        lines.append(f"ot_assigned_pin_exact {{{n}}} {LAYER[f]} {f} {p:.3f}")
    (OUT / "assigned_pins.tcl").write_text("\n".join(lines) + "\n")
    tcl_sha = hashlib.sha256((OUT / "assigned_pins.tcl").read_bytes()).hexdigest()
    grant = dict(
        schema="opentallas.hbm.vmdel_v6_literal_pin_grant.v1",
        status="GRANTED_H_DIE_1025_ISOLATED_MEASUREMENT",
        grant_issued="2026-10-16T10:25-07:00 H-DIE -> H-NETLIST (el1011-hbmdie.log 10:27): VMDEL v6 clk_cap S-mid x=128.508 on M5 with body clk at N-mid",
        cell="ot_hbm_svc_vmdel_lane_v6", source=SRC, source_sha256=hashlib.sha256(src_raw).hexdigest(),
        source_commit="25a390064", request=REQ, request_sha256=hashlib.sha256(req_raw).hexdigest(),
        outline_um=[W, H], layer_cap="M5", pg_layer="M5", strap_layer="M6",
        clock_entries=[dict(pin=n, face=f, layer=LAYER[f], center_um=c,
                            role="input capture band (every input pin incl. rst_n, bank_id)" if n == "clk_cap" else "body: control, PC state, 4 SRAMs, output flops")
                       for n, (f, c) in CLK.items()],
        clock_relationship=dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0),
        supersedes_request_clock="S x 4.320..4.416 (W corner) -- revised per VIS-HBM/H-HARDEN 10:08: E half of S face was ~250 um from a corner entry",
        actual_grid=dict(M4=dict(phase=PH, pitch=PITCH), M5=dict(phase=PH, pitch=PITCH),
                         evidence="results/arch/hbm_idx_scheduled_0811/dense_actual_track_readback_0935.json"),
        notch_rule="N/S M5 pins clear of the M5 PG stripe pairs (core 2.16 + 0.300 + 5.4k, w 0.12, s 0.072), both offset readings",
        faces=faces, bits=len(pos), assigned_pins_tcl_sha256=tcl_sha,
        instances=req["instances"], extra_clock_entries_per_die=32, added_normal_cycles=0,
        open=["actual ODB pin rectangle readback (gate floorplan.pin_geometry)", "per-root insertion/spread, native launch<=220/capture<=190/spread<=80",
              "TT setup / FF hold / DRC 0", "die parent binding (d4 frozen; no view alias)"])
    (OUT / "grant.json").write_text(json.dumps(grant, indent=1) + "\n")
    (OUT / "check.json").write_text(json.dumps(dict(verdict="PASS", bits=len(pos), faces=faces, tcl_sha256=tcl_sha), indent=1) + "\n")
    print(json.dumps(dict(bits=len(pos), faces=faces)))


if __name__ == "__main__":
    sys.exit(main())
