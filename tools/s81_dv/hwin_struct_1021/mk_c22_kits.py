#!/usr/bin/env python3
"""S81-ELEM2-HWIN 10-21: successor kits of dsdv_mu_hwin c21q/c21r (NEEDS_RTL TT -148.19 / -141.73, cmp_r -> rec_r).

  dsdv_mu_hwin_c22q  MAIN  NEV 8  (= the G8IQ die master dsdv_mu_hwin #(47, NEV 8, NEP 4, NRT 2)), LOCAL_RECORD=1,
                           44 SRAMs on the c21q 43.2 lattice in 7 columns (345.6 x 388.8), same rows / band y159.84..206.28
  dsdv_mu_hwin_c22r  FB    NEV 16 (c21r geometry 561.6 x 388.8, 84 SRAMs), LOCAL_RECORD=1, pd 0.55

Both drop the c21j source-hash-locked native manifests/fences (they cannot qualify changed RTL) and use the c21h
row-pruned band (hwin_cell_band.tcl, before tapcell) + GPL row envelope (hwin_gpl_row_envelope.tcl): every standard
cell lives in the full-width band between the SRAM rows.  Run from the repo root with the c21q/c21r base kits
present (git checkout e20095385 -- physical/ref_tile/dsdv_mu_hwin_c21q physical/ref_tile/dsdv_mu_hwin_c21r, not committed
here), then each kit's regen.py.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RT = ROOT / "physical/ref_tile"
BAND = (159.84, 206.28)
ROWS = [216.0, 259.2, 302.4, 345.6, 129.6, 86.4, 43.2]       # c21q fill order inside one column
PRIVATE = ["candidate_birth_bind.tcl", "hwin_fixture_fences.tcl", "hwin_native_fences.tcl", "native_cell_fence.tcl",
           "native_cell_manifest.tsv", "native_flow_removed_cells.tsv", "native_macro_manifest.tsv", "place_fixture.tcl",
           "gate_result.json", "tb_dsdv_mu_hwin_cfg_relay.sv", "run_c21j_bench.sh"]
SYNTH_SRC_UM2_LR0_NEV16 = 9151.137          # c21q pre-GPL source area (69,564 -noabc cells)
CELLS = {16: 80098, 8: 49913}               # -noabc cells at LOCAL_RECORD=1 (ep7 sizing, scratch s81-elem2-hwin)
CELLS_LR0_NEV16 = 69564


def macros_nev8(src):
    by = {m["inst"]: m for m in src}
    order = []
    for e in range(4):
        order += [m for m in src if f"g_event_mem?{e}?" in m["inst"]]
    order += [m for m in src if "event" not in m["inst"]]
    for e in range(4, 8):
        order += [m for m in src if f"g_event_mem?{e}?" in m["inst"]]
    assert len(order) == 44 and all(o["inst"] in by for o in order)
    out = []
    for k, m in enumerate(order):
        col, row = divmod(k, 7)
        out.append({**m, "at": [round(43.2 * (col + 1), 4), ROWS[row]]})
    return out


def bench(kit, nev):
    w = "results/arch/s81_hwin_struct_1021/benches/{}/run.log"
    b = [("ns47", "pass", None), ("ns2", "pass", None), ("norelay", "fail", "EARLY_MITER|CBREF_MITER"),
         ("eastcopy", "fail", "EARLY_MITER|CBREF_MITER"), ("mut2", "fail", "EARLY_MITER|CBREF_MITER"),
         ("eastdue", "fail", "event boot count differs")]
    out = []
    for v, exp, rx in b:
        j = {"name": f"c22_{v}", "cmd": f"NEV_KIT={nev} bash physical/ref_tile/{kit}/run_c22_bench.sh {{RUN}}/{v} {v}",
             "expect": exp, "threads": 4, "peak_ram_gb": 16 if v == "eastdue" else 8}
        if exp == "pass":
            j["pass_regex"] = "^MUWIN PASS$"
            if v == "ns47":
                j["min_count_regex"] = r"^MUWIN starts (\d+) fires \d+ expected \d+ K \d+ t_mf 0000 hslot 0000 hwin 00$"
        else:
            j["fail_regex"] = rx
            j["fail_witness"] = w.format(v)
        out.append(j)
    return out


def make(name, base, nev, pd, purpose):
    src = RT / base
    kd = RT / name
    if kd.exists():
        shutil.rmtree(kd)
    shutil.copytree(src, kd, ignore=shutil.ignore_patterns("gate_layout", *PRIVATE))
    s = json.loads((src / "spec.json").read_text())
    for k in ("planning_birth_budget", "planning_std_area_um2", "measured_area_basis"):
        s.pop(k, None)
    s["name"] = name
    s["params"]["NEV"] = nev
    s["params"]["LOCAL_RECORD"] = 1
    std = round(SYNTH_SRC_UM2_LR0_NEV16 * CELLS[nev] / CELLS_LR0_NEV16, 1)
    s["std_area_um2"] = std
    if nev == 8:
        s["macros"] = macros_nev8(s["macros"])
        s["outline"] = {"w": 345.6, "h": 388.8}
        # same pin phase vs the 43.2 macro lattice as c21q (whole-lattice shift -129.6 um)
        s["pin_ranges"] = {p: [round(a - 129.6, 4), round(b - 129.6, 4)] for p, (a, b) in s["pin_ranges"].items()}
    W = s["outline"]["w"]
    s["route"]["pd"] = pd
    s["route"]["tag"] = name.rsplit("_", 1)[-1]
    s["orfs_vars"] = {"PRE_GLOBAL_PLACE_TCL": f"physical/ref_tile/{name}/hwin_gpl_row_envelope.tcl",
                      "PRE_GLOBAL_PLACE_SKIP_IO_TCL": f"physical/ref_tile/{name}/hwin_gpl_row_envelope.tcl"}
    band_um2 = (W - 2 * 2.16) * (BAND[1] - BAND[0])
    s["fill_reason"] = {"lattice_channel_bound": {
        "why": (f"S81-ELEM2-HWIN {name}: the ratified HWIN lattice/channel exception class (c21d..c21q, approved_by codex "
                f"coordinator): SRAM origins on the c21q 43.2 lattice ({len(s['macros'])} macros, {W:g} x 388.8, >=24.8 um "
                f"channels, halo 8.64), ONE full-width standard-cell band y{BAND[0]}..{BAND[1]} (rows outside it pruned "
                f"before tapcell, c21h hook). Source std area {std} um2 = c21q 9151.137 x -noabc cell ratio "
                f"{CELLS[nev]}/{CELLS_LR0_NEV16} (NEV {nev}, LOCAL_RECORD=1); placed 40..60% band density is measured by the gate."),
        "lattice_um": 43.2, "min_channel_um": 24.84, "std_band_util": round(std / band_um2, 4),
        "approved_by": "codex coordinator", "std_band_y_um": list(BAND)}}
    s["structural_change"] = (
        f"S81-ELEM2-HWIN successor of {base} (daemon NEEDS_RTL: c21q TT -148.19 / FF -8.26, c21r TT -141.73 / FF -11.76, "
        "DRC 0). Failing class: g_compare_copy.cmp_r -> 47-entry identity compare + OR reduce -> global duplicate flag udup "
        "-> distributed to all 16x2 event rec_r + slot record_group across the 561.6 um band (two 113/148 ps buffer hops, "
        "arrival 1222.75 vs required 1081.02). Fix (RTL, codex adf49d4f8 LOCAL_RECORD=1): each of the (NEV/4 event + 6 slot) "
        "record consumer groups gets its own kept duplicate-region cone (2 local 10-bit user landing flops, 47 compares, "
        "8-entry partial ORs), so admission drives <= 8 local record flops instead of a band-wide broadcast; 0 cycles added "
        "(waveform miter vs frozen HWIN21cb + anchor). "
        + ("NEV 8 = the exact G8IQ die parameter (dsdv_seq_host_mux u_hwin), 44 SRAMs, outline 345.6 x 388.8 (band 341 um "
           "wide instead of 557: every cone/band hop shorter). " if nev == 8 else
           "NEV 16 fallback on the unchanged c21r 84-SRAM geometry (superset of the die's 8 events). ")
        + "Physical: c21j hash-locked native manifests/fences dropped (cannot qualify changed RTL); c21h row-pruned band "
        f"+ GPL row envelope instead; pd {pd}; OPT_POST_GRT_WNS=0 pre_grt kept (EST-0104 class).")
    s["reroute_reason"] = {"kind": "rtl_change",
                           "note": f"{base} NEEDS_RTL TT -148/-142 (cmp_r -> rec_r global duplicate admission); "
                                   "LOCAL_RECORD=1 regional admission successor, codex adf49d4f8."}
    s["owner"] = "Claude:S81-ELEM2-HWIN"
    j = s["job"]
    j.update({"owner": "Claude:S81-ELEM2-HWIN", "branch": "claude/s81-elem2-hwin-1021", "tag": name.rsplit("_", 1)[-1],
              "purpose": purpose, "views_to": f"physical/ref_tile/{name}/views", "record_to": f"results/rtl/ref_tile/{name}"})
    j["extra_paths"] = ["rtl/lib", "rtl/dsrom_sys/s81_dv/unit", "physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1",
                        "physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2", "rtl/dsrom_sys/s81_ph",
                        "tools/hwin_private_package_1019", "tools/s81_dv/hwin_struct_1021",
                        "results/arch/s81_hwin_struct_1021"]
    j["benches"] = bench(name, nev)
    (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    (kd / "hwin_cell_band.tcl").write_text(
        "# HWIN-CENTRAL (c21h hook): one full-width central standard-cell band, before tapcell.\n"
        "set ot_cb [ord::get_db_block]\nset ot_cd [[ord::get_db_tech] getDbUnitsPerMicron]\nset ot_cr {}\nset ot_keep 0\n"
        "foreach row [$ot_cb getRows] {\n  set bb [$row getBBox]\n"
        f"  if {{[$bb yMin] < round({BAND[0]}*$ot_cd) || [$bb yMax] > round({BAND[1]}*$ot_cd)}} {{\n"
        "    lappend ot_cr $row\n  } else { incr ot_keep }\n}\n"
        "foreach row $ot_cr { odb::dbRow_destroy $row }\n"
        f"if {{$ot_keep == 0}} {{ error \"HWIN_CELL_BAND no rows in y{BAND[0]}..{BAND[1]}\" }}\n"
        f"puts \"HWIN_CELL_BAND kept=$ot_keep removed=[llength $ot_cr] y{BAND[0]}..{BAND[1]}\"\n")
    env = (ROOT / "tools/s81_dv/hwin_struct_1021/hwin_gpl_row_envelope.tcl.in").read_text()
    (kd / "hwin_gpl_row_envelope.tcl").write_text(env.replace("@NMACRO@", str(len(s["macros"]))))
    (kd / "regen.py").write_text(
        '#!/usr/bin/env python3\n"""Regenerate ' + name + ': ref_tile gen + c21h band hooks + c21q OPT_POST_GRT_WNS=0."""\n'
        "import subprocess\nfrom pathlib import Path\nroot = Path(__file__).resolve().parents[3]\n"
        "kit = Path(__file__).resolve().parent\n"
        "rc = subprocess.run(['python3', str(root/'tools/ref_tile/ref_tile.py'), 'gen', str(kit/'spec.json')], cwd=root).returncode\n"
        "with (kit/'place.tcl').open('a') as out:\n"
        "    out.write('\\n# Row pruning must precede tapcell; physical core and macro placements remain unchanged.\\n"
        f"source /src/physical/ref_tile/{name}/hwin_cell_band.tcl\\n')\n"
        "with (kit/'pre_grt.tcl').open('a') as out:\n"
        "    out.write('\\n# c21q: skip ORFS post-GRT vt_swap/reroute WNS pass (EST-0104 class)\\nset ::env(OPT_POST_GRT_WNS) 0\\n"
        "puts \"HWIN_OPT_POST_GRT_WNS=0\"\\n')\n"
        "raise SystemExit(rc)\n")
    shutil.copy(ROOT / "tools/s81_dv/hwin_struct_1021/run_c22_bench.sh", kd / "run_c22_bench.sh")
    return s


if __name__ == "__main__":
    make("dsdv_mu_hwin_c22q", "dsdv_mu_hwin_c21q", 8, 0.48,
         "HWIN c22q MAIN: LOCAL_RECORD=1 regional duplicate admission (c21q/c21r cmp_r->rec_r TT -148), NEV 8 = G8IQ die "
         "parameter, 44 SRAM 345.6x388.8, row-pruned band, pd 0.48.")
    make("dsdv_mu_hwin_c22r", "dsdv_mu_hwin_c21r", 16, 0.55,
         "HWIN c22r FB: LOCAL_RECORD=1 regional duplicate admission (c21q/c21r cmp_r->rec_r TT -148), NEV 16 on c21r "
         "84-SRAM geometry, row-pruned band, pd 0.55.")
