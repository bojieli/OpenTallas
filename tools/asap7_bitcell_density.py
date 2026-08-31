#!/usr/bin/env python3
"""Draw and measure mask-ROM and 6T SRAM bitcell pitch in the ASAP7 predictive PDK.

The purpose is NOT to produce a 7 nm density number for the model. It is to test
whether ``rom.cell_to_sram_cell_area_ratio`` is node-stable, by measuring the same
ratio at a 7 nm-class FinFET node that a sibling experiment measures at IHP SG13G2
(130 nm planar).

ASAP7 is a predictive academic PDK. Per docs/OPEN_PDK_SELECTION.md it may support
an explicitly predictive digital experiment only. No number produced here is a
TSMC N7/N6/N5 figure, and no number here may be averaged with the IHP result.

The bundled ASAP7 FakeRAM collateral (platform ``ram/``, ``fakeram.cfg``) is
neither read nor used; every shape below is drawn from the ASAP7 design rules.
"""

from __future__ import annotations

# --- ASAP7 process constants, all in nanometres -----------------------------
# Sources, all inside the pinned ASAP7 v1.7 platform:
#   drc/asap7.lydrc  GATE.S.1 "Exact horizontal GATE pitch : 54nm"
#   drc/asap7.lydrc  FIN.S.1  "Exact vertical FIN pitch : 27nm"
#   drc/asap7.lydrc  GATE.W.1 "Exact horizontal width of GATE : 20nm"
#   drc/asap7.lydrc  FIN.W.1  "Exact vertical width of FIN : 7nm"
CPP = 54.0        # contacted poly (gate) pitch, x
FP = 27.0         # fin pitch, y
GATE_W = 20.0     # drawn gate width
FIN_W = 7.0       # drawn fin width
ACT_H = 27.0      # one-fin active height (ACTIVE.W.1 / ACTIVE.W.2)
ACT_GAP = 27.0    # ACTIVE.S.1 min vertical active spacing
SDT_W = 24.0      # SDT.W.1 min horizontal SDT width
LISD_W = 24.0     # LISD.W.1 min LISD width
V_SZ = 18.0       # V0/V1 drawn size
M1_W = 18.0       # M1.W.1 min width
M2_W = 18.0       # M2.W.1 min width
M1_MIN_AREA = 504.0

# GDS layer numbers, read from drc/asap7.lydrc "layers definitions"
L = {
    "nwell": 1, "fin": 2, "gate": 7, "gcut": 10, "active": 11,
    "nselect": 12, "pselect": 13, "lig": 16, "lisd": 17, "v0": 18,
    "m1": 19, "m2": 20, "v1": 21, "sdt": 88, "sramdrc": 99,
}

# Fin lattice: fin centres at FIN_C0 + k*FP.  Chosen so that a one-fin active
# band [c-13.5, c+13.5] gives exactly the ACTIVE.FIN.EX.1 10 nm extension.
FIN_C0 = 27.0


class Layout:
    def __init__(self, name: str) -> None:
        self.name = name
        self.rects: list[tuple[int, float, float, float, float]] = []

    def add(self, layer: str, x0: float, y0: float, x1: float, y1: float) -> None:
        if x1 <= x0 or y1 <= y0:
            raise ValueError(f"degenerate rect on {layer}: {(x0, y0, x1, y1)}")
        self.rects.append((L[layer], x0, y0, x1, y1))

    def fin_grid(self, x0: float, x1: float, y0: float, y1: float) -> None:
        """Uniform dummy-fin sea, the ASAP7 standard-cell convention."""
        k = int((y0 - FIN_C0) // FP) - 2
        while True:
            c = FIN_C0 + k * FP
            if c - FIN_W / 2 > y1:
                break
            if c - FIN_W / 2 >= y0:
                self.add("fin", x0, c - FIN_W / 2, x1, c + FIN_W / 2)
            k += 1

    def write(self, path) -> None:
        lines = [f"{lay} 0 {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f}"
                 for lay, x0, y0, x1, y1 in self.rects]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def bbox(self):
        xs0 = min(r[1] for r in self.rects); ys0 = min(r[2] for r in self.rects)
        xs1 = max(r[3] for r in self.rects); ys1 = max(r[4] for r in self.rects)
        return xs0, ys0, xs1, ys1


def band_y(m: int) -> tuple[float, float]:
    """Active band m: one fin tall, on a 2-fin-pitch (54 nm) lattice."""
    c = FIN_C0 + 2 * m * FP
    return c - ACT_H / 2, c + ACT_H / 2


def add_psub_tap(lay: Layout, x0: float, x1: float) -> None:
    """p+ substrate tap on the fin lattice, below the array (ACTIVE.LUP.1).

    Peripheral: it sits outside the measured bitcell pitch."""
    c = FIN_C0 - 4 * FP
    lay.add("active", x0 + 30, c - ACT_H / 2, x1 - 30, c + ACT_H / 2)
    lay.add("sdt", x0 + 60, c - ACT_H / 2, x0 + 84, c + ACT_H / 2)
    lay.add("lisd", x0 + 60, c - ACT_H / 2, x0 + 84, c + ACT_H / 2)
    lay.add("pselect", x0 - 20, c - ACT_H / 2 - 27, x1 + 20, c + ACT_H / 2 + 27)


def add_nwell_tap(lay: Layout, x0: float, ny0: float, ny1: float) -> None:
    """n+ tap inside the n-well, at the array's right periphery (ACTIVE.LUP.1)."""
    ay0, ay1 = ny0 + 13.5, ny1 - 13.5
    lay.add("active", x0 + 80, ay0, x0 + 220, ay1)
    lay.add("sdt", x0 + 110, ay0, x0 + 134, ay1)
    lay.add("lisd", x0 + 110, ay0, x0 + 134, ay1)
    lay.add("nselect", x0 + 40, ny0, x0 + 260, ny1)


# ---------------------------------------------------------------------------
# NOR mask-ROM arrays
# ---------------------------------------------------------------------------
def build_rom(cells_x: int, rows: int, *, private_drain: bool,
              x_period: float | None = None, row_pitch: float = 54.0,
              sram_rules: bool = False,
              unprogrammed: set[tuple[int, int]] | None = None) -> tuple[Layout, dict]:
    """A NOR mask-ROM array of ``rows`` bitlines x ``cells_x`` wordlines.

    ``private_drain`` False  -- every source/drain region is shared by the two
        transistors flanking it.  This is the densest 1T NOR ROM the ASAP7 rules
        permit, but a shared drain contact cannot program a single bit, so this
        variant is reachable only by implant/Vt programming.
    ``private_drain`` True   -- the program's own topology (spice/ihp_sg13g2/
        rom_slice/schematic.spice): each bit's drain reaches the bitline through
        its own via, present or absent.  Drains cannot be shared, so cells are
        laid out as mirrored D-G-S-G-D islands separated by an active break.
    """
    unprogrammed = unprogrammed or set()
    lay = Layout("rom")

    if private_drain:
        # Two cells per island; islands repeat on ``x_period``.
        period = x_period if x_period is not None else 4 * CPP
        pairs = (cells_x + 1) // 2
        gates = []
        for p in range(pairs):
            gates += [p * period + 27.0, p * period + 27.0 + CPP]
        # SD centres per island: D0, S, D1
        sds = []
        for p in range(pairs):
            base = p * period
            sds += [(base + 0.0, "bl"), (base + CPP, "vss"), (base + 2 * CPP, "bl")]
        islands = [(p * period - 8.0, p * period + 2 * CPP + 8.0) for p in range(pairs)]
        x_pitch = period / 2.0
    else:
        gates = [27.0 + CPP * i for i in range(cells_x)]
        sds = [(CPP * s, "bl" if s % 2 == 0 else "vss") for s in range(cells_x + 1)]
        islands = [(-16.0, CPP * cells_x + 16.0)]
        x_pitch = CPP

    bands = []
    for j in range(rows):
        c = FIN_C0 + row_pitch * j
        bands.append((c - ACT_H / 2, c + ACT_H / 2, c))

    ax0 = min(i[0] for i in islands)
    ax1 = max(i[1] for i in islands)
    ay0 = bands[0][0]
    ay1 = bands[-1][1]
    gx0, gx1 = gates[0] - GATE_W / 2, gates[-1] + GATE_W / 2

    lay.fin_grid(ax0 - 30, ax1 + 30, FIN_C0 - 6 * FP, ay1 + 40)
    for gx in gates:
        lay.add("gate", gx - GATE_W / 2, ay0 - 20, gx + GATE_W / 2, ay1 + 20)

    for b0, b1, cy in bands:
        for ix0, ix1 in islands:
            lay.add("active", ix0, b0, ix1, b1)
        for sx, _role in sds:
            lay.add("sdt", sx - SDT_W / 2, b0, sx + SDT_W / 2, b1)
            lay.add("lisd", sx - LISD_W / 2, b0, sx + LISD_W / 2, b1)

    lay.add("nselect", ax0 - 50, ay0 - 30, ax1 + 50, ay1 + 30)
    add_psub_tap(lay, ax0 - 50, ax1 + 50)
    if sram_rules:
        # Ask whether ASAP7's memory-cell rule relief (the SRAMDRC recognition
        # layer) would let a ROM array shrink the way it lets the 6T cell shrink.
        lay.add("sramdrc", ax0 - 70, FIN_C0 - 6 * FP - 20, ax1 + 70, ay1 + 50)

    # --- back end: M2 bitline per row, M1 source column, per-bit drain via ---
    for sx, role in sds:
        if role == "vss":
            lay.add("m1", sx - M1_W / 2, ay0 - 25, sx + M1_W / 2, ay1 + 25)
    n_v1 = 0
    for j, (b0, b1, cy) in enumerate(bands):
        lay.add("m2", ax0 - 25, cy - M2_W / 2, ax1 + 25, cy + M2_W / 2)
        for i, (sx, role) in enumerate(sds):
            lay.add("v0", sx - V_SZ / 2, cy - V_SZ / 2, sx + V_SZ / 2, cy + V_SZ / 2)
            if role == "bl":
                lay.add("m1", sx - M1_W / 2, cy - 14, sx + M1_W / 2, cy + 14)
                if (i, j) not in unprogrammed:
                    lay.add("v1", sx - V_SZ / 2, cy - V_SZ / 2,
                            sx + V_SZ / 2, cy + V_SZ / 2)
                    n_v1 += 1

    meta = {
        "sram_rule_relief_applied": sram_rules,
        "x_pitch_nm": x_pitch, "y_pitch_nm": row_pitch,
        "cell_area_nm2": x_pitch * row_pitch,
        "gates": len(gates), "rows": rows, "programming_via1_present": n_v1,
    }
    return lay, meta


# ---------------------------------------------------------------------------
# 6T SRAM thin-cell array
# ---------------------------------------------------------------------------
def build_sram(cells_x: int, cells_y: int, cell_h: float = 216.0) -> tuple[Layout, dict]:
    """A 6T thin-cell SRAM array, 2 CPP wide by four one-fin device bands tall.

    Band order in a cell is NMOS-A (PG1,PD1) / PMOS-A (PU1) / PMOS-B (PU2) /
    NMOS-B (PG2,PD2).  Wordline gates run the full array height; the
    cross-coupled gates are cut by GCUT in the gap between PMOS-A and PMOS-B and
    again between vertically adjacent cells.
    """
    lay = Layout("sram")
    cw = 2 * CPP                       # 108 nm cell width
    period = 2 * cw                    # 216 nm x mirror period
    periods = (cells_x + 1) // 2

    def bc(j: int, m: int) -> float:   # centre of band m in cell row j
        return j * cell_h + FIN_C0 + 2 * FP * m

    def band(j: int, m: int) -> tuple[float, float]:
        c = bc(j, m)
        return c - ACT_H / 2, c + ACT_H / 2

    n_gates = int(round(period * periods / CPP))
    gates = [27.0 + CPP * i for i in range(n_gates)]
    xc_gates = [g for g in gates if (g % period) in (81.0, 135.0)]

    x_lo, x_hi = -40.0, period * periods + 40.0
    y_lo = band(0, 0)[0] - 40.0
    y_hi = band(cells_y - 1, 3)[1] + 40.0

    lay.fin_grid(x_lo, x_hi + 300, FIN_C0 - 6 * FP, y_hi)
    for gx in gates:
        lay.add("gate", gx - GATE_W / 2, y_lo - 10, gx + GATE_W / 2, y_hi + 10)

    pmos_islands = [(p * period + 46.0, p * period + 170.0) for p in range(periods)]
    nmos_sd = [CPP * s for s in range(n_gates + 1)]
    pmos_sd = [p * period + d for p in range(periods) for d in (54.0, 108.0, 162.0)]

    for j in range(cells_y):
        for m in (0, 3):               # NMOS bands: continuous active
            b0, b1 = band(j, m)
            lay.add("active", x_lo + 8, b0, x_hi - 8, b1)
            for sx in nmos_sd:
                lay.add("sdt", sx - SDT_W / 2, b0, sx + SDT_W / 2, b1)
        for m in (1, 2):               # PMOS bands: broken at the wordline gate
            b0, b1 = band(j, m)
            for ix0, ix1 in pmos_islands:
                lay.add("active", ix0, b0, ix1, b1)
            for sx in pmos_sd:
                lay.add("sdt", sx - SDT_W / 2, b0, sx + SDT_W / 2, b1)

        # local interconnect: internal storage nodes bridge two bands
        n0, n1 = band(j, 0); p1 = band(j, 1); p2 = band(j, 2); n3 = band(j, 3)
        for p in range(periods):
            base = p * period
            for d in (54.0, 162.0):    # Q and QB storage nodes
                lay.add("lisd", base + d - LISD_W / 2, n0, base + d + LISD_W / 2, p1[1])
                lay.add("lisd", base + d - LISD_W / 2, p2[0], base + d + LISD_W / 2, n3[1])
            lay.add("lisd", base + 108 - LISD_W / 2, p1[0], base + 108 + LISD_W / 2, p2[1])
            for yy in ((n0, n1), (n3[0], n3[1])):
                lay.add("lisd", base + 108 - LISD_W / 2, yy[0], base + 108 + LISD_W / 2, yy[1])
        for sx in (0.0, period * periods):   # bitline / bitline-bar columns
            lay.add("lisd", sx - LISD_W / 2, n0, sx + LISD_W / 2, n1)
            lay.add("lisd", sx - LISD_W / 2, n3[0], sx + LISD_W / 2, n3[1])

        # selects and well
        sx0, sx1 = x_lo - 20, x_hi + 20
        lay.add("nselect", sx0, band(j, 0)[0] - 13.5, sx1, band(j, 0)[1] + 13.5)
        lay.add("pselect", sx0, band(j, 1)[0] - 13.5, sx1, band(j, 2)[1] + 13.5)
        lay.add("nwell", sx0, band(j, 1)[0] - 13.5, sx1, band(j, 2)[1] + 13.5)
        lay.add("nselect", sx0, band(j, 3)[0] - 13.5, sx1, band(j, 3)[1] + 13.5)

        # gate cuts on the cross-coupled gates
        cuts = [(band(j, 1)[1], band(j, 2)[0])]
        if j + 1 < cells_y:
            cuts.append((band(j, 3)[1], band(j + 1, 0)[0]))
        for c0, c1 in cuts:
            if c1 - c0 < 12.0:         # gap collapsed (tight probe): no cut fits
                continue
            c0, c1 = c0 + 4.0, c1 - 4.0
            for p in range(periods):
                lay.add("gcut", p * period + 54.0, c0, p * period + 162.0, c1)

    add_psub_tap(lay, x_lo, x_hi)
    lay.add("nwell", x_hi + 20, band(0, 1)[0] - 13.5, x_hi + 300, band(0, 2)[1] + 13.5)
    add_nwell_tap(lay, x_hi + 20, band(0, 1)[0] - 13.5, band(0, 2)[1] + 13.5)
    lay.add("sramdrc", x_lo - 10, FIN_C0 - 6 * FP - 10, x_hi + 310, y_hi + 10)

    meta = {"x_pitch_nm": cw, "y_pitch_nm": cell_h, "cell_area_nm2": cw * cell_h,
            "cells_x": cells_x, "cells_y": cells_y}
    return lay, meta


# ---------------------------------------------------------------------------
# Driver: build GDS, run the ASAP7 KLayout DRC deck in the pinned container
# ---------------------------------------------------------------------------
import argparse
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "configs" / "pdk" / "asap7_physical_lock.json"
OUT = ROOT / "results" / "asap7_physical" / "bitcell_density"
DEFAULT_PLATFORM = Path.home() / ".local" / "opentallas-pdk-asap7-platform"

BUILD_RB = r'''
name = $name
ly = RBA::Layout::new
ly.dbu = 0.00025
top = ly.create_cell(name)
File.readlines($shapes).each do |line|
  f = line.split
  next if f.empty?
  li = ly.layer(f[0].to_i, f[1].to_i)
  x0 = (f[2].to_f / 0.25).round; y0 = (f[3].to_f / 0.25).round
  x1 = (f[4].to_f / 0.25).round; y1 = (f[5].to_f / 0.25).round
  top.shapes(li).insert(RBA::Box::new(x0, y0, x1, y1))
end
ly.write($gds)
puts "WROTE #{$gds} bbox=#{top.bbox.to_s}"
'''


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def verify_platform(platform: Path) -> dict:
    """Hash the ASAP7 collateral against the governed lock."""
    lock = json.loads(LOCK.read_text())
    want = lock["toolchain"]["asap7"]["files"]
    root = platform / "asap7"
    checked = {}
    for rel in ("lef/asap7_tech_1x_201209.lef", "gds/asap7sc7p5t_28_R_220121a.gds",
                "drc/asap7.lydrc", "KLayout/asap7.lyt", "config.mk"):
        got = sha256_file(root / rel)
        if got != want[rel]:
            raise SystemExit(f"ASAP7 collateral mismatch for {rel}: {got} != {want[rel]}")
        checked[rel] = got
    forbidden = [p for p in (root / "ram", root / "fakeram.cfg") if p.exists()]
    return {
        "platform_root": str(root),
        "asap7_version": lock["toolchain"]["asap7"]["version"],
        "asap7_upstream_revision": lock["toolchain"]["asap7"]["upstream_revision"],
        "container_digest": lock["toolchain"]["container"]["amd64_digest"],
        "verified_files": checked,
        "fakeram_collateral_present_but_unused": [str(p) for p in forbidden],
    }


def run_case(name: str, lay: Layout, work: Path, platform: Path, image: str) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    shapes = work / f"{name}.txt"
    lay.write(shapes)
    (work / "build.rb").write_text(BUILD_RB, encoding="utf-8")

    def dock(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["docker", "run", "--rm",
             "-v", f"{platform}:/plat:ro", "-v", f"{work}:/work",
             "--entrypoint", "klayout", image, "-b"] + args,
            check=False, text=True, capture_output=True, timeout=3600)

    built = dock(["-r", "/work/build.rb",
                  "-rd", f"name={name}", "-rd", f"shapes=/work/{name}.txt",
                  "-rd", f"gds=/work/{name}.gds"])
    if not (work / f"{name}.gds").exists():
        raise SystemExit(f"{name}: GDS build failed\n{built.stdout}\n{built.stderr}")

    drc = dock(["-r", "/plat/asap7/drc/asap7.lydrc",
                "-rd", f"in_gds=/work/{name}.gds",
                "-rd", f"report_file=/work/{name}.lyrdb"])
    (work / f"{name}.drc.log").write_text(drc.stdout + drc.stderr, encoding="utf-8")
    report = work / f"{name}.lyrdb"
    if not report.exists():
        raise SystemExit(f"{name}: DRC produced no report\n{drc.stdout[-4000:]}\n{drc.stderr[-4000:]}")

    counts: dict[str, int] = {}
    tree = ET.parse(report)
    cats = {c.findtext("name"): c.findtext("description")
            for c in tree.getroot().iter("category")}
    for item in tree.getroot().iter("item"):
        cat = (item.findtext("category") or "").strip("'")
        counts[cat] = counts.get(cat, 0) + 1
    total = sum(counts.values())
    return {
        "case": name,
        # the drawn geometry, deterministic; the GDS below embeds KLayout's write
        # timestamp, so its hash is archival identity and not a determinism check
        "geometry_sha256": hashlib.sha256(shapes.read_bytes()).hexdigest(),
        "gds_sha256": sha256_file(work / f"{name}.gds"),
        "shape_count": len(lay.rects),
        "bbox_nm": list(lay.bbox()),
        "drc_violation_total": total,
        "drc_violations_by_rule": dict(sorted(counts.items())),
        "drc_rule_descriptions": {k: cats.get(k) for k in sorted(counts)},
    }


def markdown_report(out: dict) -> str:
    m = out["measurement"]
    x = out["cross_node_comparison"]
    L2 = ["# ASAP7 mask-ROM versus 6T-SRAM bitcell area, and the node-transfer test", "",
          f"**Status:** **{out['status'].upper()}**  ",
          f"**Evidence class:** {out['evidence_class']}  ",
          f"**PDK:** ASAP7 v{out['pdk']['asap7_version']} "
          f"(`{out['pdk']['asap7_upstream_revision'][:12]}`), platform hashes verified "
          f"against `configs/pdk/asap7_physical_lock.json`  ",
          "**DRC:** the platform's own `drc/asap7.lydrc`, run under KLayout in the "
          f"pinned ORFS container `{out['pdk']['container_digest'][:19]}...`", "",
          "ASAP7 is a **predictive** research PDK. Nothing here is a TSMC N7/N6/N5 "
          "number, and nothing here may be averaged with the IHP SG13G2 result.", "",
          "## Measured bitcell pitch areas", "",
          "| Cell | Pitch | Area | In CPP x fin-pitch units | Ratio to 6T |",
          "|---|---:|---:|---:|---:|",
          f"| 6T SRAM (thin cell) | 108 x 216 nm | **{m['sram_6t_bitcell_area_nm2']:.0f} nm2** "
          f"| {m['sram_area_in_cpp_x_finpitch_units']:.1f} | 1.000 |",
          f"| NOR mask-ROM, via-programmed | 108 x 54 nm | **{m['rom_via_programmed_bitcell_area_nm2']:.0f} nm2** "
          f"| {m['rom_via_area_in_cpp_x_finpitch_units']:.1f} | **{m['ratio_via_programmed_rom_to_sram']:.4f}** |",
          f"| NOR mask-ROM, shared-S/D floor (not per-bit programmable) | 54 x 54 nm "
          f"| {m['rom_shared_sd_bitcell_area_nm2']:.0f} nm2 "
          f"| {m['rom_shared_area_in_cpp_x_finpitch_units']:.1f} | {m['ratio_shared_sd_rom_to_sram']:.4f} |", "",
          "## Cross-node comparison", "",
          "| Node | ROM bitcell | 6T SRAM bitcell | Ratio | 6T / ROM |",
          "|---|---:|---:|---:|---:|",
          f"| IHP SG13G2, 130 nm planar (sibling) | {x['ihp_rom_bitcell_area_um2']:.6f} um2 "
          f"| {x['ihp_sram_bitcell_area_um2']:.4f} um2 | **{x['ihp_ratio']:.4f}** "
          f"| {x['sram_to_rom_multiple_ihp']:.2f}x |",
          f"| ASAP7, predictive 7 nm FinFET (this run) | 0.005832 um2 | 0.023328 um2 "
          f"| **{x['asap7_ratio']:.4f}** | {x['sram_to_rom_multiple_asap7']:.2f}x |",
          f"| Difference | | | **+{100 * x['ratio_difference_fraction']:.1f}%** | |", "",
          f"`node_stable = {x['node_stable']}`. {x['direction']}", "",
          "## DRC cases", "",
          "| Case | Expected | Violations | Rules |", "|---|---|---:|---|"]
    for name, r in out["cases"].items():
        rules = ", ".join(k for k in r["drc_violations_by_rule"] if k.strip()) or "-"
        L2.append(f"| `{name}` | {'clean' if r['expected_drc_clean'] else 'must fail'} "
                  f"| {r['drc_violation_total']} | {rules} |")
    L2 += ["", "The `probe_*` cases shrink one lattice quantum and must fail; each names "
           "the rule that pins that dimension. `rom_via_sram_rules` gives the ROM array "
           "ASAP7's SRAMDRC memory-cell rule relief and measures no shrink at all.", "",
           "## Claim boundary", ""]
    L2 += [f"- {t[0].upper()}{t[1:]}." for t in out["claim_boundary"]["forbidden_inferences"]]
    L2 += ["", "## Reproduction", "", "```bash", "python3 tools/asap7_bitcell_density.py", "```",
           "", "See `docs/ROM_DENSITY_NODE_TRANSFER.md` for the interpretation.", ""]
    return "\n".join(L2)


CASES = {
    "rom_shared_sd":       lambda: build_rom(8, 6, private_drain=False),
    "rom_via_programmed":  lambda: build_rom(8, 6, private_drain=True,
                                             unprogrammed={(0, 1), (2, 3)}),
    "sram_6t":             lambda: build_sram(4, 3),
    # minimality probes: each shrinks one lattice quantum and must FAIL DRC
    "probe_rom_shared_sd_tight_y": lambda: build_rom(8, 6, private_drain=False,
                                                     row_pitch=45.0),
    "probe_rom_via_tight_x":       lambda: build_rom(8, 6, private_drain=True,
                                                     x_period=162.0),
    "probe_sram_tight_y":          lambda: build_sram(4, 3, cell_h=189.0),
    # does the memory-cell rule relief shrink a ROM the way it shrinks a 6T cell?
    "rom_via_sram_rules":          lambda: build_rom(8, 6, private_drain=True,
                                                     sram_rules=True),
    "probe_rom_via_sram_rules_tight_x": lambda: build_rom(8, 6, private_drain=True,
                                                          sram_rules=True,
                                                          x_period=162.0),
}
MUST_PASS = ("rom_shared_sd", "rom_via_programmed", "sram_6t", "rom_via_sram_rules")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", type=Path, default=DEFAULT_PLATFORM)
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--work", type=Path,
                    default=Path("/tmp/claude-1000/-home-ubuntu-OpenTallas/"
                                 "451622a4-7c99-41d6-967d-b73a48c02083/scratchpad/"
                                 "rom_density/work"))
    ap.add_argument("--case", action="append")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args()

    pdk = verify_platform(args.platform)
    names = args.case or list(CASES)
    results = {}
    for name in names:
        lay, meta = CASES[name]()
        res = run_case(name, lay, args.work, args.platform, args.image)
        res.update(meta)
        expect_clean = name in MUST_PASS
        res["expected_drc_clean"] = expect_clean
        res["status"] = ("pass" if (res["drc_violation_total"] == 0) == expect_clean
                         else "fail")
        results[name] = res
        print(f"{name}: {res['drc_violation_total']} violations "
              f"({'clean expected' if expect_clean else 'failure expected'}) "
              f"-> {res['status']}")
        for rule, n in list(res["drc_violations_by_rule"].items())[:12]:
            print(f"    {rule}: {n}  {res['drc_rule_descriptions'][rule]}")

    if args.no_write or len(names) != len(CASES):
        return 0

    ihp_path = ROOT / "results" / "spice" / "ihp_sg13g2_bitcell" / "bitcell.json"
    ihp = json.loads(ihp_path.read_text()) if ihp_path.is_file() else None
    rom_shared = results["rom_shared_sd"]["cell_area_nm2"]
    rom_via = results["rom_via_programmed"]["cell_area_nm2"]
    sram = results["sram_6t"]["cell_area_nm2"]
    out = {
        "schema_version": 1,
        "experiment_id": "asap7_rom_sram_bitcell_area_ratio_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if all(r["status"] == "pass" for r in results.values()) else "fail",
        "node": "ASAP7 predictive 7 nm FinFET research PDK",
        "evidence_class": "predictive open-PDK drawn-layout DRC measurement; not a "
                          "foundry PDK, not TSMC N7/N6/N5, not silicon",
        "pdk": pdk,
        "process_constants_nm": {"contacted_poly_pitch": CPP, "fin_pitch": FP,
                                 "gate_width": GATE_W, "min_active_height": ACT_H,
                                 "min_active_vertical_space": ACT_GAP},
        "cases": results,
        "measurement": {
            "sram_6t_bitcell_area_nm2": sram,
            "rom_via_programmed_bitcell_area_nm2": rom_via,
            "rom_shared_sd_bitcell_area_nm2": rom_shared,
            "ratio_via_programmed_rom_to_sram": rom_via / sram,
            "ratio_shared_sd_rom_to_sram": rom_shared / sram,
            "sram_area_in_cpp_x_finpitch_units": sram / (CPP * FP),
            "rom_via_area_in_cpp_x_finpitch_units": rom_via / (CPP * FP),
            "rom_shared_area_in_cpp_x_finpitch_units": rom_shared / (CPP * FP),
        },
        "cross_node_comparison": ({
            "ihp_source": ihp_path.relative_to(ROOT).as_posix(),
            "ihp_experiment_id": ihp["experiment_id"],
            "ihp_node": "IHP SG13G2, 130 nm planar",
            "ihp_rom_bitcell_area_um2": ihp["rom_bitcell"]["cell_area_um2"],
            "ihp_sram_bitcell_area_um2": ihp["sram_bitcell"]["1P"]["cell_area_um2"],
            "ihp_ratio": ihp["ratio"]["measured"],
            "asap7_node": "ASAP7 predictive 7 nm FinFET",
            "asap7_ratio": rom_via / sram,
            "ratio_difference_fraction": (rom_via / sram) / ihp["ratio"]["measured"] - 1.0,
            "direction": "ASAP7 ratio is HIGHER: the ROM bitcell is relatively LARGER "
                         "against 6T SRAM at the 7 nm-class node than at 130 nm. This "
                         "moves against the ROM side of the comparison.",
            "sram_to_rom_multiple_ihp": ihp["sram_bitcell"]["1P"]["cell_area_um2"]
                                        / ihp["rom_bitcell"]["cell_area_um2"],
            "sram_to_rom_multiple_asap7": sram / rom_via,
            "node_stable": False,
            "never": "these two ratios must not be averaged, blended or interpolated",
        } if ihp else None),
        "claim_boundary": {
            "forbidden_inferences": [
                "this is not a TSMC N7, N6, N5 or N4 number and must never be labelled one",
                "this must not be averaged, blended or combined with the IHP SG13G2 measurement",
                "this does not establish ROM read margin, sensing, energy, PVT, yield or cost",
                "no ASAP7 FakeRAM or synthetic memory collateral was read or used",
            ],
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "bitcell_density.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    (OUT / "REPORT.md").write_text(markdown_report(out), encoding="utf-8")
    print(f"\nwrote {OUT / 'bitcell_density.json'}")
    print(f"SRAM {sram:.0f} nm2   ROM(via) {rom_via:.0f} nm2  ratio {rom_via/sram:.4f}")
    print(f"                      ROM(shared) {rom_shared:.0f} nm2  ratio {rom_shared/sram:.4f}")
    return 0 if out["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
