#!/usr/bin/env python3
"""QC-A0 (10-23): the A0 PLANNED HARD CORE of the Qwen compute die variant-B plan, one clock entry.

Plan (claude/qc-p2-1023 @6587487a5, physical/die_plan/qwen_compute/die_plan.json): every CB quad partition holds four
A0 cores at origins (86.4, 77.76) (699.84, 77.76) (86.4, 1382.4) (699.84, 1382.4), outline 457.92 x 1157.76, R0 in
the quad (bottom-half quads are MX copies of the whole partition); 720 NK + 48 NL instances.  COORD 07:24 ruling (2):
a partition takes ONE spine tap per planned core; plan clock rule: insertion budget at the core boundary flops
250 +/- 40 ps, neighbour spread <= 80 ps TT+FF.

Why the r3 kits (qfd_tile_n{k,l}_romleaf_rp{f,m}, 35/39 clock ENTRY ports) cannot meet that: NL rpf/rpm post-CTS setup
-168.8 / -425.4 ps are ALL inter-entry crossings (GATE_XCLK: L2C ring writer on ck -> TX9 reader on ck_tx<g>; rq_ce
on ck -> ROM leaf any_d on ck_rp<k>; out9 writer on ck_tx<g> -> qlr3 reader on ck; rpm also dw/de -> tx), each timed
with 210 ps inter-entry uncertainty (60 + OT_IO_SKEW_INTER 150) between entries whose trees differ by 3-6x (ck
16 BUFx24 deep, TT 607..1082 ps over 7,043 sinks; tx 111..183; dw/de 389/395; ROM/LSL macro 207/166 + 319/445 ps of
external compensation).  Intra-entry reg->reg is clean.  That is the clock architecture, not the logic depth.

This generator keeps the r3 floorplan, children, regions, request decoders, RTL body and every cycle, and changes ONLY
the clock interface: the core has one port `ck`; every former entry is an internal net tied to it in the core top
(qfd_tile_n{k,l}_a0c: the rr top with the clock ports turned into `wire ck_x = ck;`, same instance names, so every
region / decoder hook still matches).  The core is timed as one clock domain (no inter-entry uncertainty; CRPR on the
shared trunk) and CTS balances every sink, including the ROM / LSL / node macro clock pins through their Liberty
min/max_clock_tree_path insertion (ETM views carry them).

Variants (parallel fallback routes, owner 10-19):
  s  = the ref_tile cluster clock SPINE (physical/common_flow/clock_spine.tcl: pre-placed equal-delay bisection tree,
       leaves padded to equal MEASURED arrival; leaf target = sink arrival + the hard child's own clock insertion, so
       ROM / LSL / node internal flops are balanced against the core flops; hfd_attn 1,634 -> 24 ps).  MAIN.
  k  = "clock": "cts" + clock_split_km.tcl: K=48 compact k-means local roots on `ck` (~860 sinks each, one BUFx24 per
       centroid) under one TritonCTS top tree (macros via their Liberty clock_tree_path).  FALLBACK.
  (r3 ck tree for contrast: TritonCTS, 32-sink clusters of 151-um diameter, a BUFx24 every ~30 um = 16 levels.)

    gen_a0c.py --write      writes rtl/physical/a0_core/qfd_tile_n{k,l}_a0c.sv, tools/qwen_romleaf/a0core/<kit>_pins.tcl
                            and tools/qwen_romleaf/a0core/specs/<kit>.json  (then: ref_tile.py gen <spec>)
"""
import copy, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RR = "rtl/physical/a0_rc14_selected_2000/qfd_tile_{k}_rp2_romleaf_rr.sv"
CORE_RTL = "rtl/physical/a0_core/qfd_tile_{k}_a0c.sv"
KM_K = 48


def core_rtl(k):
    src = (ROOT / RR.format(k=k)).read_text()
    mod = f"qfd_tile_{k}_rp2_romleaf_rr"
    assert f"module {mod}" in src
    ports = re.findall(r"^\s*input\s+wire\s+(ck_\w+),\s*$", src, re.M)
    assert ports and "ck" not in ports
    out = src.replace(f"module {mod}", f"module qfd_tile_{k}_a0c", 1)
    out = re.sub(r"^\s*input\s+wire\s+ck_\w+,\s*\n", "", out, flags=re.M)
    head, sep, body = out.partition("\n);\n")
    assert sep
    ties = "".join(f"    wire {p} = ck;\n" for p in ports)
    hdr = (f"// QC-A0 10-23 (tools/qwen_romleaf/a0core/gen_a0c.py): the A0 planned hard core of the Qwen compute die plan,\n"
           f"// ONE clock entry.  Body = {RR.format(k=k)} unchanged; its {len(ports)} former clock-entry ports are\n"
           f"// internal nets of the core clock `ck` (one spine tap per planned core, COORD 10-23 07:24).  Same instance\n"
           f"// names, same logic, same cycles.\n")
    return hdr + head + sep + "    // former clock entries: one clock domain, CTS balances every sink (macros via clock_tree_path)\n" + ties + body, ports


def pins_tcl(k, kit):
    src = (ROOT / f"tools/qwen_romleaf/repack/qfd_tile_{k}_romleaf_rpf_pins.tcl").read_text().splitlines()
    keep = [l for l in src if not re.match(r"place_pin -pin_name \{ck_\w+\}", l)]
    assert any(l.startswith("place_pin -pin_name {ck}") for l in keep)
    hdr = [f"# {kit}: QC-A0 10-23 (gen_a0c.py) = the rpf pin plan with the clock-entry pins removed; the single core",
           "# clock `ck` stays at its rpf E-face site (y 668.076, beside the issue pocket at the tile centre of mass)."]
    return "\n".join(hdr + keep) + "\n", len(src) - len(keep)


def spec(k, var):
    base = json.load(open(ROOT / f"physical/ref_tile/qfd_tile_{k}_romleaf_rpf/spec.json"))
    kit = f"qfd_tile_{k}_a0c{var}"
    s = copy.deepcopy(base)
    s["name"] = kit
    s["top"] = f"qfd_tile_{k}_a0c"
    rr = RR.format(k=k)
    assert rr in s["sources"]
    s["sources"] = [CORE_RTL.format(k=k) if x == rr else x for x in s["sources"]]   # core top replaces the rr top
    for key in ("clock", "clock_ports", "clock_cts_roots", "required_hybrid_roots"):
        s.pop(key, None)
    s["clock_port"] = "ck"
    # one clock domain: Yosys merges the per-entry reset relays (r3 kept them apart by clock), so one landing copy
    # fanned out to 38 loads (native census FAIL > 32, nk_a0cs 07:57).  Twice the landing copies -> <= ~19 each.
    s["reset_landing"]["copies"] = {"rst_n": 32}
    s["pins"] = {f: [p for p in v if not p.startswith("ck_")] for f, v in base["pins"].items()}
    s["io_tcl"] = f"tools/qwen_romleaf/a0core/{kit}_pins.tcl"
    ov = dict(s.get("orfs_vars") or {})
    if var == "k":
        s["clock"] = "cts"
        s["pre_cts_extra"] = ["physical/common_flow/clock_split_km.tcl"]
        ov.update({"OT_CKKM_PORT": "ck", "OT_CKKM_K": str(KM_K)})
        lab = f"FALLBACK: one core clock ck, {KM_K} k-means local roots (clock_split_km.tcl) under one TritonCTS top tree"
    else:
        s["pre_cts_extra"] = []
        lab = "MAIN: one core clock ck, ref_tile cluster clock spine (child-insertion leaf targets, measured padding)"
    s["orfs_vars"] = ov
    s["structural_change"] = (f"QC-A0 10-23 ({lab}): A0 planned hard core of the Qwen compute variant-B plan (CB quad, 4 "
        "cores at (86.4|699.84, 77.76|1382.4), 457.92 x 1157.76, one spine tap per core). Same rpf floorplan, children, "
        "regions, request decoders, RTL body and cycles as qfd_tile_" + k + "_romleaf_rpf@fce5d5cb2; the 35/39 clock-entry "
        "ports become internal nets of ck (r3 NL setup -169/-425 ps were 100% inter-entry crossings under 210 ps "
        "inter-entry uncertainty).")
    s["reroute_reason"] = "QC-A0 10-23: plan-derived core clock interface (one entry per planned core)."
    s["slot_change_request"] = ("QC-A0 10-23: core outline/pins = rpf (plan contents u_t00..u_t11); clock ports ck_* "
        "removed, one ck at E (457.824, 668.076). Report to QC-P2: core tap = ck pin, budget measured at gate.")
    sdc = s.get("safe_design_checklist") or {}
    sdc["7_clock"] = ("ONE core clock entry ck (plan: one spine tap per planned core). Former entries are internal nets: "
                      "no inter-entry uncertainty, CTS balances all sinks incl. macro clock_tree_path insertion. "
                      "Boundary TT/FF spread must pass 80 ps; insertion vs plan budget 250+/-40 reported to QC-P2.")
    s["safe_design_checklist"] = sdc
    j = s["job"]
    j["owner"] = "Claude:QC-A0"; j["branch"] = "claude/qc-a0-1023"; j["tag"] = f"a0c{var}"
    j["purpose"] = s["structural_change"]
    j["views_to"] = f"physical/ref_tile/{kit}/views"; j["record_to"] = f"results/rtl/ref_tile/{kit}"
    return kit, s


if __name__ == "__main__":
    if "--write" in sys.argv:
        for k in ("nk", "nl"):
            rtl, ports = core_rtl(k)
            p = ROOT / CORE_RTL.format(k=k); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(rtl)
            print("WROTE", p.relative_to(ROOT), len(ports), "former entries")
            for var in ("k", "s"):
                kit, s = spec(k, var)
                ptcl, nrm = pins_tcl(k, kit)
                (HERE / f"{kit}_pins.tcl").write_text(ptcl)
                (HERE / "specs").mkdir(exist_ok=True)
                (HERE / "specs" / f"{kit}.json").write_text(json.dumps(s, indent=1) + "\n")
                print("WROTE", kit, "pins removed", nrm)
