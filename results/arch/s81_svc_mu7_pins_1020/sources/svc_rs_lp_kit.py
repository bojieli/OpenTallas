#!/usr/bin/env python3
"""PL-SVC (PARENTS-LANDED, 10-18): ref_tile specs + exact pin plans for the landed service slices
dsdv_svc_rs_lp (the 14 non-entry slices) and dsdv_svc_rs_entry_lp (the entry slices rsv_05 / rsv_11).

    python3 tools/s81_dv/svc_rs/svc_rs_lp_kit.py        -> tools/ref_tile/specs_s81dv_svc_lp/<top>.json
                                                           physical/dsdv_svc_rs_lp_pins/<top>.tcl
then  python3 tools/ref_tile/ref_tile.py gen tools/ref_tile/specs_s81dv_svc_lp/<top>.json
The up face is split (coordinator 10-18 option (a)): up_d {done, cr, ack} 13 b + up_f {rg fault, rg live, fault} 3 b a
face.  The entry adds the half's host endpoint (j 33 / jd 2 / q 515 / hw 292 / hc 9 / fault / st_rg 2 / pv_v + pv_d 514,
1,368 b): q / j / jd / hc / fault / st_rg on N beside the SM face (an entry slice has no N-face tree child: role children
E / S / W), hw on W, the P.V root word on E (N stays <= 6 pins/um).

Floorplan (origin SW, all hard children on the 43.2 lattice; W 1728 x H 2073.6):
  region c  (ck_c, core): the 8 dsdv_svc_sx_hrow leaves as a 4 x 2 array (column = score row r, row = half b) at
            x 345.6 .. 1339.2, y 302.4 .. 777.6; the 144 dsfd_dvrly_276 face stations around it (W / E: B at the slice
            edge, C, A beside the array; S: B / C / A rows under the array; N: A row above the array, C in the side
            channels of the SM head, B at the N edge); 16 attention staging SRAMs (soft attention share) in the corners
            and the SM-band side channels; the PC faces, tree nodes and landing rings are soft.
  region sm (ck_sm): the SM head above: 2 x 2 dsfd_su_t_smhq (bottom row MX, pins facing up; top row R0, pins
            facing down) around the root dsfd_su_t_smhr and the tap ot_s81_su_smq in the middle row.
Pins: every face carries its quarter of the 4-face neighbour lanes (dn 805 / up 16 / ri, ro 514 / gather 2,133 /
scatter 1,077 each way); HBM on S, the SM face on N; spread evenly (N / S M3 / M5, W / E M4 / M6), clocks at the
centre of the face beside their region (ck_c S, ck_sm N).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
L = 43.2
W, H = 1728.0, 2073.6
D = "rtl/dsrom_sys/s81_dv/svc_rs"
SM = "rtl/dsrom_sys/s81_dv/su_sm"
RLY = {f: f"physical/ref_tile/s81dv_rly_276_{f.lower()}/views/dsfd_dvrly_276_{f}" for f in ("NS", "SN", "EW", "WE")}
HROW = "physical/ref_tile/dsdv_svc_sx_hrow/views/dsdv_svc_sx_hrow"
SMHQ = "physical/ref_tile/s81su_smhq/views/dsfd_su_t_smhq"
SMHR = "physical/ref_tile/s81su_smhr/views/dsfd_su_t_smhr"
SMQ = "physical/ref_tile/s81su_smq/views/ot_s81_su_smq"
SRAM = "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2"
IN_M = {0: "NS", 1: "EW", 2: "SN", 3: "WE"}       # dsdv_sx_rly_in: IN through face F travels away from it
OUT_M = {0: "SN", 1: "WE", 2: "NS", 3: "EW"}      # dsdv_sx_rly_out
KS = ("g0", "g1", "s")


def r2(x):
    return round(x, 3)


def children():
    ch = []
    # score-exchange leaves: column r, row b
    for r in range(4):
        for b in range(2):
            ch.append(dict(view=HROW, inst=f"*u_sx.g_r?{r}?.g_h?{b}?.u_hrow", at=[r2(345.6 + 259.2 * r), r2(302.4 + 259.2 * b)]))
    # face stations: lane i = 3 r + k
    for r in range(4):
        for k, kk in enumerate(KS):
            i = 3 * r + k
            c, j = i % 2, i // 2
            # W (f 3): B x 43.2 / 86.4, C 129.6 / 172.8, A 259.2 / 302.4; rows y 302.4 + 86.4 j
            y = 302.4 + 86.4 * j
            ch.append(dict(view=RLY[OUT_M[3]], inst=f"*u_sx.g_r?{r}?.g_f?3?.g_ab?1?.u_{kk}*", at=[r2(43.2 + L * c), r2(y)]))
            ch.append(dict(view=RLY[IN_M[3]], inst=f"*u_sx.g_r?{r}?.g_f?3?.g_c?0?.u_{kk}*", at=[r2(129.6 + L * c), r2(y)]))
            ch.append(dict(view=RLY[OUT_M[3]], inst=f"*u_sx.g_r?{r}?.g_f?3?.g_ab?0?.u_{kk}*", at=[r2(259.2 + L * c), r2(y)]))
            # E (f 1): mirrored columns
            ch.append(dict(view=RLY[OUT_M[1]], inst=f"*u_sx.g_r?{r}?.g_f?1?.g_ab?1?.u_{kk}*", at=[r2(1684.8 - L * c), r2(y)]))
            ch.append(dict(view=RLY[IN_M[1]], inst=f"*u_sx.g_r?{r}?.g_f?1?.g_c?0?.u_{kk}*", at=[r2(1598.4 - L * c), r2(y)]))
            ch.append(dict(view=RLY[OUT_M[1]], inst=f"*u_sx.g_r?{r}?.g_f?1?.g_ab?0?.u_{kk}*", at=[r2(1425.6 - L * c), r2(y)]))
            # S (f 2): columns under the array, rows B 43.2 / C 129.6 / A 216
            x = 345.6 + 86.4 * i
            ch.append(dict(view=RLY[OUT_M[2]], inst=f"*u_sx.g_r?{r}?.g_f?2?.g_ab?1?.u_{kk}*", at=[r2(x), 43.2]))
            ch.append(dict(view=RLY[IN_M[2]], inst=f"*u_sx.g_r?{r}?.g_f?2?.g_c?0?.u_{kk}*", at=[r2(x), 129.6]))
            ch.append(dict(view=RLY[OUT_M[2]], inst=f"*u_sx.g_r?{r}?.g_f?2?.g_ab?0?.u_{kk}*", at=[r2(x), 216.0]))
            # N (f 0): A row above the array; C in the side channel (lanes 0-5 W, 6-11 E); B two rows at the N edge
            ch.append(dict(view=RLY[OUT_M[0]], inst=f"*u_sx.g_r?{r}?.g_f?0?.g_ab?0?.u_{kk}*", at=[r2(x), 820.8]))
            side, m = (0, i) if i < 6 else (1, i - 6)
            ch.append(dict(view=RLY[IN_M[0]], inst=f"*u_sx.g_r?{r}?.g_f?0?.g_c?0?.u_{kk}*",
                           at=[259.2 if side == 0 else 1641.6, r2(1425.6 + 86.4 * m)]))
            bx = (43.2, 129.6, 216.0) if side == 0 else (1468.8, 1555.2, 1641.6)
            ch.append(dict(view=RLY[OUT_M[0]], inst=f"*u_sx.g_r?{r}?.g_f?0?.g_ab?1?.u_{kk}*",
                           at=[bx[m % 3], 2030.4 if m < 3 else 1987.2]))
    # SM head (region sm)
    for q, (x, y, o) in enumerate(((345.6, 864.0, "MX"), (907.2, 864.0, "MX"), (345.6, 1598.4, "R0"), (907.2, 1598.4, "R0"))):
        ch.append(dict(view=SMHQ, inst=f"*u_smh.g_q?{q}?.u_q", at=[x, y], orient=o))
    ch.append(dict(view=SMHR, inst="*u_smh.u_r", at=[734.4, 1339.2]))
    ch.append(dict(view=SMQ, inst="*u_sms.u_smq", at=[518.4, 1339.2]))
    for c in ch:
        c["count"] = 1
    return ch


def macros(pmem=False):
    """the attention share's staging SRAMs: u_stage0 / u_stage1 x lane l x slice b (NSTAGE 2, NL 4, NB 2); with pmem
    (SVCB 10-19, COORD 0ix (2) option (b)) the att p store: 2 banks (even / odd) x 2 halves of ot_sram_1r1w_256x256 in
    the E column under the two E staging macros (x 1468.8, y 1080 .. 1339.2, beside smhq / smhr, W of the N-face C relays)"""
    spots = [(43.2, 43.2), (43.2, 129.6), (43.2, 216.0), (1512.0, 43.2), (1512.0, 129.6), (1512.0, 216.0)]
    spots += [(43.2, r2(907.2 + 86.4 * j)) for j in range(8)] + [(1468.8, 907.2), (1468.8, 993.6)]
    out = []
    n = 0
    for st in (0, 1):
        for ln in range(4):
            for b in range(2):
                out.append(dict(view=SRAM, count=1, at=list(spots[n]),
                                inst=f"*u_stage{st}.g_macro.g_lane?{ln}?.g_slice?{b}?.g_256.u_mem"))
                n += 1
    if pmem:
        for bk in range(2):
            for hf in range(2):
                out.append(dict(view=SRAM, count=1, at=[1468.8, r2(1080.0 + 86.4 * (2 * bk + hf))],
                                inst=f"*u_att.g_pmem.g_bank?{bk}?.g_half?{hf}?.u_mem"))
    return out


HOST_N = ("j", "jd", "q", "hc", "fault", "st_rg")
HOST = [("j", 33), ("jd", 2), ("q", 515), ("hw", 292), ("hc", 9), ("fault", 1), ("st_rg", 2), ("pv_v", 1), ("pv_d", 513)]


def bits(p, w):
    return [p] if w == 1 and p in ("fault", "pv_v", "w_v") else [f"{p}[{i}]" for i in range(w)]


def face_bits(entry=False):
    """{face: [bit names in order]} for the exact io plan"""
    F = {0: "N", 1: "E", 2: "S", 3: "W"}
    lanes = [("dn_i", 805), ("dn_o", 805), ("up_d_i", 13), ("up_d_o", 13), ("up_f_i", 3), ("up_f_o", 3), ("ri", 514), ("ro", 514),
             ("gi_v", 1), ("gi_d", 2132), ("go_v", 1), ("go_d", 2132), ("si_v", 1), ("si_d", 1076), ("so_v", 1), ("so_d", 1076)]
    faces = {f: [] for f in "NESW"}
    for f, fn in F.items():
        for p, w in lanes:
            faces[fn] += [f"{p}[{w * f + i}]" for i in range(w)]
    hbm = [("rq", 682), ("rk", 2), ("wd", 2), ("rv", 2), ("r_data", 512), ("r_tag", 34), ("r_beat", 8), ("hs", 2)]
    hb = [f"{p}[{i}]" for p, w in hbm for i in range(w)] + ["rst"] + [f"sid[{i}]" for i in range(4)]
    s = faces["S"]
    faces["S"] = s[:len(s) // 2] + hb[:len(hb) // 2] + ["ck_c"] + hb[len(hb) // 2:] + s[len(s) // 2:]
    smf = ["w_v"] + [f"w_a[{i}]" for i in range(14)] + [f"w_m[{i}]" for i in range(16)] + \
          [f"w_d[{i}]" for i in range(512)] + [f"w_st[{i}]" for i in range(12)]
    if entry:      # N <= 6 pins/um: q + job / credit / status pins on N beside the SM face, hw on W, P.V out on E
        hb = [b for p, w in HOST if p in HOST_N for b in bits(p, w)]
        smf = hb[:len(hb) // 2] + smf + hb[len(hb) // 2:]
        for fc, names in (("W", ("hw",)), ("E", ("pv_v", "pv_d"))):
            xb = [b for p, w in HOST if p in names for b in bits(p, w)]
            fb = faces[fc]
            faces[fc] = fb[:len(fb) // 2] + xb + fb[len(fb) // 2:]
    n = faces["N"]
    faces["N"] = n[:len(n) // 2] + smf[:len(smf) // 2] + ["ck_sm"] + smf[len(smf) // 2:] + n[len(n) // 2:]
    return faces


PITCH = {"M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064}
OFF = {"M3": 0.009, "M4": 0.012, "M5": 0.012, "M6": 0.016}
SIZE = {"M3": (0.018, 0.144), "M5": (0.024, 0.192), "M4": (0.192, 0.024), "M6": (0.192, 0.032)}


def io_tcl(faces, margin=4.32):
    lines = ["# generated by tools/s81_dv/svc_rs/svc_rs_lp_kit.py: every face spread evenly (N / S alternate M3 / M5, "
             "W / E alternate M4 / M6), bus bits per face slice, clocks at their face centre"]
    dens = {}
    for face, bits in faces.items():
        horiz = face in ("N", "S")
        span = (W if horiz else H) - 2 * margin
        step = span / len(bits)
        dens[face] = round(len(bits) / (W if horiz else H), 2)
        used = set()
        for i, b in enumerate(bits):
            c = margin + step * (i + 0.5)
            layer = ("M3" if i % 2 == 0 else "M5") if horiz else ("M4" if i % 2 == 0 else "M6")
            p, o = PITCH[layer], OFF[layer]
            v = round(round((c - o) / p) * p + o, 3)
            while (layer, v) in used:
                v = round(v + p, 3)
            used.add((layer, v))
            loc = f"{v:.3f} {0.0 if face == 'S' else H:.3f}" if horiz else f"{0.0 if face == 'W' else W:.3f} {v:.3f}"
            sx, sy = SIZE[layer]
            lines.append(f"place_pin -pin_name {{{b}}} -layer {layer} -location {{{loc}}} -pin_size {{{sx} {sy}}} -force_to_die_boundary")
    return "\n".join(lines) + "\n", dens


# SVCB (10-19, COORD 0ix (2)): the att p store (4 x 256x256 SRAM) only in the 4 P.V owner positions of quarter ST 0
# (rs_pvslot: rsv_08 / 09 / 10 / 12, kit dsdv_svc_rs_lp, PMEM 1); the 10 other non-entry positions take dsdv_svc_rs_lp_np
# and the entries (rsv_05 / rsv_11, not owners at ST 0) dsdv_svc_rs_entry_lp, both PMEM 0 (no store; fault 23 if mis-bound).
VARIANTS = {
    "dsdv_svc_rs_lp": dict(entry=False, flat="dsdv_svc_rs_f", pmem=1,
                           what="dsdv_svc_rs P.V owner positions (rsv_08 / 09 / 10 / 12 at ST 0: att p store in SRAM)"),
    "dsdv_svc_rs_lp_np": dict(entry=False, flat="dsdv_svc_rs_f", pmem=0,
                              what="dsdv_svc_rs non-owner positions (the 10 other non-entry slices: no att p store)"),
    "dsdv_svc_rs_entry_lp": dict(entry=True, flat="dsdv_svc_rs_entry_f", pmem=0,
                                 what="dsdv_svc_rs_entry (entry slices rsv_05 W / rsv_11 E: the half's host endpoint; no att p store)"),
}
VL = "VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
WIT = "results/rtl/s81_dv_1016/svc_rs/lp"


def benches(top, entry):
    e = 1 if entry else 0
    out = [dict(name=f"{top}_lockstep", cmd=f"SIM=verilator {VL} LP_MUTS=0 bash rtl/dsrom_sys/s81_dv/svc_rs/lp/{top}_bench.sh "
                f"lp_bench_out", expect="pass", pass_regex="LP_LOCKSTEP PASS", threads=8, peak_ram_gb=128,
                pass_witness=f"{WIT}/{top}_m0.log")]
    for m in (1, 2, 3, 4):
        out.append(dict(name=f"{top}_mut{m}", cmd=f"SIM=verilator {VL} LP_MUTS={m} bash rtl/dsrom_sys/s81_dv/svc_rs/lp/"
                        f"{top}_bench.sh lp_bench_out", expect="fail", fail_regex="LP_LOCKSTEP FAIL", threads=8,
                        peak_ram_gb=128, fail_witness=f"{WIT}/{top}_m{m}.log"))
    out.append(dict(name=f"{top}_refactor_feq", cmd=f"bash tools/s81_dv/svc_rs/lp_feq_bench.sh feq_out 0 '' {e}",
                    expect="pass", pass_regex="FEQ PASS", threads=8, peak_ram_gb=128,
                    pass_witness=f"{WIT}/feq_e{e}_m0.log"))
    out.append(dict(name=f"{top}_refactor_feq_mut", cmd=f"bash tools/s81_dv/svc_rs/lp_feq_bench.sh feq_out 1 '' {e}",
                    expect="fail", fail_regex="FEQ FAIL", threads=8, peak_ram_gb=128,
                    fail_witness=f"{WIT}/feq_e{e}_m1.log"))
    return out


def main():
    for top, v in VARIANTS.items():
        kit(top, **v)


def kit(TOP, entry, flat, what, pmem):
    NAME = TOP
    src = (ROOT / "tools/s81_dv/svc_rs/rs_files.sh").read_text()
    import re
    m = re.search(r"RS_SRC=\((.*?)\)", src, re.S).group(1)
    files = [f.replace("$D", D).replace("$SM", SM) for f in m.split()]
    hard = {f"{D}/dsdv_svc_sx_hrow.sv", "rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv", f"{SM}/ot_s81_su_smq.sv",
            f"{SM}/dsfd_su_t_smhq.sv", f"{SM}/dsfd_su_t_smhr.sv", f"{SM}/ot_s81_su_smh.sv",
            "rtl/dsrom_sys/s81_suhc/hier/dsfd_su_t_sm.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv"}
    files = [f for f in files if f not in hard]
    files = [f.replace("ot_sram_1r1w_256x256_m2_r2c2.v", "ot_sram_1r1w_256x256_m2_r2c2_bb.v") for f in files]
    # dsdv_svc_rs.sv stays (the original slice; the flat parents' children live in dsdv_svc_rs_glue.sv)
    files += ["rtl/dsrom_sys/s81_ph/svc/dsfd_svc_c.sv", f"{D}/dsdv_svc_rs_glue.sv",
              f"{D}/{flat}.sv", "rtl/common/landed_parent/ot_pl_land.sv", f"{D}/lp/{TOP}.sv"]
    faces = face_bits(entry)
    tcl, dens = io_tcl(faces)
    pins_dir = ROOT / "physical/dsdv_svc_rs_lp_pins"
    pins_dir.mkdir(parents=True, exist_ok=True)
    (pins_dir / f"{TOP}.tcl").write_text(tcl)
    ports = ["ck_c", "ck_sm", "rst", "sid"] + ([p for p, _ in HOST] if entry else []) + \
            ["dn_i", "dn_o", "up_d_i", "up_d_o", "up_f_i", "up_f_o", "ri", "ro", "gi_v", "gi_d", "go_v", "go_d",
             "si_v", "si_d", "so_v", "so_d", "rq", "rk", "wd", "rv", "r_data", "r_tag", "r_beat", "hs",
             "w_v", "w_a", "w_m", "w_d", "w_st"]
    spec = dict(
        name=NAME, top=TOP, kind="cluster",
        sources=files, params={"SRAM_MACRO": 1, "MUT": 0, "PMEM": pmem},
        defines=["SU_SMU_T", "SVCQ_ENG_FG3", "OT_SVC_RS_HARD"], hard_define="OT_SVC_RS_HARD",
        # SYNTH_ARGS -noshare (S81-SVCBK 10-18): the @6bc7f0f30 gates sat >7 h in yosys SHARE on the runtime-indexed
        # part-selects of dsdv_svc_sx / dsdv_svc_att; production practice (hbm_norm_noshare, lane_kh_overlay)
        # SYNTH_MEMORY_MAX_BITS 262144 (AD-S81-SVC 10-18 22:40): the -noshare gates passed SHARE and then FAILED the ORFS
        # memory inventory (3 h 13 m): dsdv_svc_att keeps deliberate flop memories pmem 512 x 512 (262,144 b, p FIFO,
        # 2 read ports) and land 640 x 256 (163,840 b, 3 write / 4 read ports), plus pvq 8 x 2,120, sw 32 x 512, tr 4 x
        # 512 x 18.  The cap is set to the largest MEASURED memory (not unbounded); SRAM banking of pmem is the open
        # coordinator option (lanes/COORD-REVIEW-QUEUE.md, AD-S81-SVC).
        # SVCB 10-19: pmem is SRAM now (option (b)); the largest flop memory left is land 640 x 256 = 163,840 b.
        orfs_vars={"VERILOG_INCLUDE_DIRS": f"/src/{D}", "SYNTH_ARGS": "-noshare", "SYNTH_MEMORY_MAX_BITS": "163840"},
        # ref_tile admits multiple_cts_roots only on leaf tiles (and then no sdc_extra): a landed CLUSTER takes the
        # Q-CLUSTER form (qc_kit.py): clock cts, one TritonCTS tree per region clock port, the lp.py SDC creates ck_<r>
        clock="cts", clock_port="ck_c", clock_ports=["ck_c", "ck_sm"],
        reset_ports=["rst"],
        sdc_extra=[f"{D}/lp/{TOP}.sdc"],
        outline=dict(w=W, h=H), cluster_level=2,
        children=children(), macros=macros(pmem=bool(pmem)),
        pins={"ANY": ports}, io_tcl=f"physical/dsdv_svc_rs_lp_pins/{TOP}.tcl",
        recipe=4, hold_budget="die", inhold=False, outhold=False,
        route=dict(pd=0.5, threads=16, peak_ram_gb=256, hold_margin_ns=0.03, io_hold_margin_ns=0.03, macro_halo_um=5.4),  # io margin >= 0.025 (KITS 10-18)
        pin_regs=dict(enable=False, reason="source-registered: every lane pin lands in a pin flop / closed relay station "
                      "(dn / up / ri / ro face flops, dsfd_dvrly_276 stations), HBM pins are the dsfd_svc_pc registers, "
                      "the SM face is the smq tap's output registers; sid is a static strap"),
        fill_reason=dict(pin_bound=f"4-face neighbour lanes: ~9.1k pin bits a face (+1.2k HBM on S, +0.6k SM on N); "
                         + ("; entry: + the half's host endpoint 1,368 b on N; " if entry else "; ") +
                         f"pin density {dens} pins/um at W {W} x H {H}"),
        structural_change=(f"PL-SVC (PARENTS-LANDED 10-18, landed-regions-standard-1018): {what} "
                           "hardened as a LANDED PARENT generated by tools/landed_parent/lp.py from the wires-only refactor "
                           f"{flat}: 2 clock regions (c = tree region: 8 sx_hrow + 144 relay stations + tree nodes + "
                           "attention share + PCs; sm = SM head: 4 smhq + smhr + smq), 8 landed crossings (532 b: SE / SM rows "
                           f"c -> sm, SM fault sm -> c), record results/arch/s81_dv_1016/svc_rs/lp/{TOP}_record.json. "
                           "Up face split up_d (done / credits / acks) + up_f (fault / rg status) so the END / done path never "
                           "sees the SM fault.  Score tree / dn / up_d / P.V / HBM ports unchanged; SM face +3, up_f / hs +6, "
                           + ("host jd / fault / st_rg +6 (hc, q, hw, j, pv 0), " if entry else "") +
                           "reset +3 (compiler record).  SVCB 10-19 (COORD 0ix (2) option (b)): the att p store is SRAM (2 even / odd banks x "
                           "2 x ot_sram_1r1w_256x256, one-cycle static prefetch, read schedule unchanged) in the P.V owner kit "
                           f"only (PMEM {pmem} here); land stays flops."),
        job=dict(owner="Claude:HOURLY-S81/SVCB", branch="claude/s81-svcb-1019", tag=TOP,
                 purpose=f"S81-DV regional service slice {what} as a landed parent (2 regions)",
                 extra_paths=["rtl/dsrom_sys/s81_dv", "rtl/common/landed_parent", "physical/dsdv_svc_rs_lp_pins",
                              "results/arch/s81_dv_1016/svc_rs/lp"],
                 benches=benches(TOP, entry)),
    )
    out = ROOT / "tools/ref_tile/specs_s81dv_svc_lp" / f"{NAME}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print(out, f"children {len(spec['children'])} macros {len(spec['macros'])} pins/um {dens}")


if __name__ == "__main__":
    main()
