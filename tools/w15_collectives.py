#!/usr/bin/env python3
"""W15: deterministic hardware collectives, built and measured end to end.

Link-layer RTL:     rtl/link/ot_link_{afifo,tx,rx}.sv (synthesizable), rtl/link/ot_link_chan_model.sv (analog PHY and
                    channel, simulation only).
Benches:            rtl/test/tb_w15_link_unit.sv    one link direction
                    rtl/test/tb_w15_v41_tp4.sv      the V4.1 TP-4 group (2 packages x 2 dies), 12 layer-0 collectives
                    rtl/test/tb_w15_qwen_tp2.sv     the Qwen TP-2 pair, 73 exchanges of a token

Subcommands:
    qwen-fixture DIR [--lanes L] [--h H]      partials, golden sums and gather words for the Qwen bench
    links                                     print the link constants (every one cited or ASSUMED)
    campaign ...                              build, run the seed sweeps, collect, write the record

Every link constant is in LINKS below with its source; ASSUMED marks a number with no measurement or normative
figure behind it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

VERILATOR = Path.home() / ".local/opentallas-tools/verilator-5.050/bin/verilator"
OUT = ROOT / "results/rtl/w15_collectives.json"

# ---------------------------------------------------------------------------------------------------------------
# Link constants.  ns unless stated.  Each entry: value, grade (normative / published / derived / floorplan /
# ASSUMED), source.
# ---------------------------------------------------------------------------------------------------------------
T_CORE_V41 = 0.92        # V4.1 die clock target (AGENTS/briefing: 0.92 ns ASAP7, 60 ps uncertainty)
LINKS = {
    "ucie_a": {
        "what": "UCIe-A (advanced package) die-to-die link inside a package, 17 x64 modules at 32 GT/s",
        "modules": dict(value=17, grade="derived",
                        source="results/floorplan/v41_rtl_engine_profile.json gaps: 'UCIe-A modules (17)'; "
                               "configs/hardware/technology.json links.rom_package_ucie.bytes_s 4.2 TB/s / "
                               "(64 lanes x 32 GT/s / 8 = 256 GB/s per module)"),
        "raw_bits_per_ns": dict(value=17 * 64 * 32, grade="derived", source="17 modules x 64 lanes x 32 Gb/s"),
        "fdi_clock_ns": dict(value=1.0, grade="ASSUMED",
                             source="D2D adapter / FDI clock of 1 GHz: the link-layer logic runs on it (a 2-slot "
                                    "frame per cycle, 2 x 547-bit records + header; 3.4 Tb/s of the 34.8 Tb/s raw)"),
        "phy_adapter_tx_rx_ns": dict(value=2.0, grade="normative",
                                     source="UCIe key metric 'Latency (Tx + Rx) < 2ns Includes D2D Adapter and PHY "
                                            "(FDI to bump and back)': D. Das Sharma et al., IEEE Trans. CPMT 12(9), "
                                            "2022, Table I (tools/sync_cost_table.py r-ucie-tcpmt)"),
        "phy_adapter_measured_ns": dict(value=3.5, grade="published",
                                        source="3.5 ns FDI-to-FDI measured, 3 nm CoWoS UCIe-A, IEEE JSSC 2026, "
                                               "doi:10.1109/JSSC.2026.3651425 (sensitivity)"),
        "static_latency_variation_ns": dict(value=0.5, grade="ASSUMED",
                                            source="half an FDI cycle of training-dependent PHY/adapter latency"),
        "wander_ns": dict(value=0.05, grade="ASSUMED", source="supply/temperature drift over a run"),
        "wire_stages_v41": dict(value=22, grade="floorplan",
                                source="results/floorplan/v41_pack_expanded_woa.json latency_crossings "
                                       "'COLLECTIVE -> farthest UCIe module' 19,183 um, re-derived at 0.76 ps/um "
                                       "(tools/uarch_model.WIRE_PS_PER_UM_LOADED) and 0.92 ns: "
                                       "tools/uarch_model.wire_cycles(19183.4, 1/0.92e-9, 0.76) = 22"),
        "wire_stages_qwen": dict(value=17, grade="floorplan",
                                 source="tools/uarch_model.QWEN_WIRE ucie_wire_per_token (13 stages each way, W5) "
                                        "scaled by the loaded-channel ratio wscale = 1.29 (qwen_eval)"),
    },
    "board_112g": {
        "what": "112G PAM4 board SerDes between the two packages of a TP-4 group, 13 lanes per die pair, light "
                "RS(272,257) FEC",
        "lanes": dict(value=13, grade="derived",
                      source="rtl/rom/ot_rom_oneshot_px.sv header ('T1 links (13 lanes per die pair)'); "
                             "configs/hardware/technology.json links.rom_board_serdes"),
        "lane_gbps": dict(value=112.0, grade="published",
                          source="112G PAM4 SerDes class (technology.json links.rom_board_serdes.bytes_s source)"),
        "codeword_bits": dict(value=2720, grade="normative",
                              source="RS(272,257) over GF(2^10): 272 x 10 bits; payload 257 x 10 = 2,570 bits "
                                     "(Ethernet Technology Consortium LL-FEC Specification 1.0, 2018)"),
        "codeword_ns": dict(value=2720 / (13 * 112.0), grade="derived", source="2,720 bits / (13 x 112 Gb/s)"),
        "pcs_clock_ns": dict(value=2720 / (13 * 112.0) / 2, grade="derived",
                             source="PCS datapath at twice the codeword rate: a frame (codeword payload) is 2 "
                                    "cycles x 2 slots = 4 records of 547 bits + header + CRC-32 = 2,300 of 2,570 "
                                    "payload bits"),
        "tx_pcs_fec_encode_ns": dict(value=4.0, grade="ASSUMED",
                                     source="PCS + RS encoder + gearbox; 4 PCS-clock register stages"),
        "tx_analog_ns": dict(value=3.0, grade="ASSUMED", source="serializer, FFE and driver"),
        "flight_ns": dict(value=2.0, grade="derived",
                          source="0.3 m of board trace at ~6.7 ns/m (technology.json rom_board_serdes channel "
                                 "decomposition; TI SCAA082A stripline 7.15 ps/mm)"),
        "rx_afe_dsp_ns": dict(value=50.0, grade="ASSUMED",
                              source="ADC-DSP receiver (CDR, FFE/DFE): technology.json rom_board_serdes names "
                                     "~40-60 ns; mid value"),
        "rx_deskew_align_ns": dict(value=10.0, grade="ASSUMED", source="PCS lane alignment and deskew FIFO"),
        "rs272_decode_ns": dict(value=45.0, grade="published",
                                source="RS(272,257) '~99ns' total at 50 Gb/s lanes (P. Sun, IEEE 802.3 50GE ad "
                                       "hoc, 2016) of which the 51 ns codeword store is lane-rate bound; the "
                                       "~48 ns processing is kept, the store is the 1.87 ns 13-lane codeword "
                                       "time here (tools/sync_cost_table.py r-sun3cd, r-gustlin3ck)"),
        "static_latency_variation_ns": dict(value=3.0, grade="ASSUMED",
                                            source="PMA/PCS gearbox and deskew-FIFO pointer placement differ per "
                                                   "link training (IEEE P802.3cd brown_3cd_03_1116 'skew "
                                                   "variation'); ~3 PCS cycles"),
        "wander_ns": dict(value=0.2, grade="ASSUMED", source="temperature/supply drift over a run"),
        "wire_stages_v41": dict(value=29, grade="floorplan",
                                source="results/floorplan/v41_pack_expanded_woa.json latency_crossings "
                                       "'COLLECTIVE -> farthest SerDes lane' 24,911 um at 0.76 ps/um and 0.92 ns: "
                                       "tools/uarch_model.wire_cycles(24911.3, 1/0.92e-9, 0.76) = 29"),
        "adopted_hop_ns": dict(value=130.0, grade="assumed (adopted)",
                               source="tools/arch_budget_v41.BASELINE board_hop_s (light-FEC package link, band "
                                      "100-170)"),
    },
}


def board_stages():
    b = LINKS["board_112g"]
    t = b["pcs_clock_ns"]["value"]
    enc = round(b["tx_pcs_fec_encode_ns"]["value"] / t)
    dec = round((b["rx_deskew_align_ns"]["value"] + b["rs272_decode_ns"]["value"]) / t)
    chan = b["tx_analog_ns"]["value"] + b["flight_ns"]["value"] + b["rx_afe_dsp_ns"]["value"] + b["codeword_ns"]["value"]
    return dict(T=t, enc=enc, dec=dec, chan_ns=chan)


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------------------------
# Qwen TP-2 fixture
# ---------------------------------------------------------------------------------------------------------------
def qwen_fixture(outdir: Path, lanes: int, H: int, seed: int = 20260929) -> dict:
    import hdc_golden as G
    outdir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    # FP32 matvec-output-like partials: magnitudes over ~12 binades, 1/8 near-cancelling pairs, exact ties
    mag = np.exp2(rng.uniform(-8, 4, size=H)).astype(np.float32)
    p0 = (mag * rng.choice([-1, 1], size=H)).astype(np.float32)
    p1 = (np.exp2(rng.uniform(-8, 4, size=H)) * rng.choice([-1, 1], size=H)).astype(np.float32)
    canc = rng.random(H) < 0.125
    p1[canc] = (-p0[canc] * (1 + rng.integers(-4, 5, size=canc.sum()) * 2.0 ** -23)).astype(np.float32)
    p0[:4] = np.array([1e10, 1.0, 2.0 ** 24, -0.0], dtype=np.float32)      # absorption, tie, signed zero
    p1[:4] = np.array([1.0, 2.0 ** -24, 1.0, 0.0], dtype=np.float32)
    parts = [p0, p1]
    exp = np.array([G.bits(G.fold([p0[i], p1[i]])).item() for i in range(H)], dtype=np.uint32)
    fw = lanes
    wpe = -(-H // fw)

    def words(arr):
        a = np.zeros(wpe * fw, dtype=np.uint32)
        a[:len(arr)] = arr
        return ["".join(f"{int(x):08x}" for x in row[::-1]) for row in a.reshape(wpe, fw)]
    with (outdir / "part.hex").open("w") as f:
        for p in parts:
            f.write("\n".join(words(G.bits(p))) + "\n")
    (outdir / "exp.hex").write_text("\n".join(words(exp)) + "\n")
    gat = [np.full(fw, 0x3F800000 + d * 0x1234 + 7, dtype=np.uint32) for d in range(2)]   # {logit, id}-like words
    (outdir / "gather.hex").write_text("\n".join("".join(f"{int(x):08x}" for x in g[::-1]) for g in gat) + "\n")
    meta = dict(schema="w15_qwen_tp2_fixture_v1", lanes=lanes, H=H, seed=seed, words_per_exchange=wpe,
                reference="tools/hdc_golden.fold([p0, p1]) = add(p0, p1), FP32 RNE, +0 canonical",
                images_sha256={p: sha(outdir / p) for p in ("part.hex", "exp.hex", "gather.hex")},
                golden_sha256=sha(ROOT / "tools/hdc_golden.py"))
    (outdir / "manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


# ---------------------------------------------------------------------------------------------------------------
# Benches: build, run, parse
# ---------------------------------------------------------------------------------------------------------------
BUILD = Path(os.environ.get("W15_BUILD", "/tmp/claude-1000/w15b"))
VEC = Path(os.environ.get("W15_VEC", "/tmp/claude-1000/w15v"))
LINK_SRC = ["rtl/link/ot_link_afifo.sv", "rtl/link/ot_link_crc32.sv", "rtl/link/ot_link_tx.sv", "rtl/link/ot_link_rx.sv",
            "rtl/link/ot_link_chan_model.sv"]
SRAM_SRC = ["rtl/link/ot_fifo_sram_fwft.sv",
            "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
            "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v",
            "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"]
TB_SRC = {
    "tb_w15_v41_tp4": ["rtl/test/tb_w15_v41_tp4.sv", *LINK_SRC, "rtl/chip/ot_chip_v41x_coll_dma.sv",
                       "rtl/chip/ot_chip_v41x_coll_transpose.sv", "rtl/rom/ot_rom_oneshot_px.sv",
                       "rtl/hdc/ot_hdc_fastfp.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv", *SRAM_SRC],
    "tb_w15_qwen_tp2": ["rtl/test/tb_w15_qwen_tp2.sv", *LINK_SRC, "rtl/rom/ot_rom_oneshot_allreduce.sv",
                        "rtl/proto/ot_fp32_add_rne_pipe.sv", *SRAM_SRC],
    "tb_w15_link_unit": ["rtl/test/tb_w15_link_unit.sv", *LINK_SRC],
    "tb_w15_crc32": ["rtl/test/tb_w15_crc32.sv", "rtl/link/ot_link_crc32.sv"],
    "tb_w15_v41_hbm_nvls": ["rtl/test/tb_w15_v41_hbm_nvls.sv", *LINK_SRC, "rtl/link/ot_link_nvls_switch.sv",
                            "rtl/hdc/ot_hdc_fastfp.sv"],
}
UNIT = {   # name -> (top, -G overrides): the link direction alone, both link classes; the CRC equivalence
    "unit_ucie": ("tb_w15_link_unit", dict(WIRE_TX=22, WIRE_RX=22, DREL=58, AW_TX=6)),
    "unit_board": ("tb_w15_link_unit", dict(FRAME_CYCLES=2, ENC_STAGES=4, DEC_STAGES=59, T_LINK=0.93407,
                                            DLY_NS=56.868, JSTATIC_NS=3.0, WANDER_NS=0.2, WIRE_TX=29, WIRE_RX=29,
                                            DREL=199, AW_TX=6)),
    "crc_par": ("tb_w15_crc32", dict(W=2300)),
    "crc_ser": ("tb_w15_crc32", dict(W=2300, MASK_MAX_W=16)),
}


def unit_checks():
    out = {}
    for name, (top, gen) in UNIT.items():
        d = BUILD / name
        subprocess.run(["rm", "-rf", str(d)], check=True)
        r = subprocess.run([str(VERILATOR), *VFLAGS, "-j", "8", "--top-module", top, "-Mdir", str(d),
                            *[f"-G{k}={v}" for k, v in gen.items()], *TB_SRC[top]], cwd=ROOT, capture_output=True,
                           text=True)
        assert r.returncode == 0, r.stderr[-2000:]
        exe = str(d / f"V{top}")
        if top == "tb_w15_crc32":
            out[name] = dict(parameters=gen, line=[l for l in subprocess.run([exe], capture_output=True, text=True)
                                                   .stdout.splitlines() if "CRCCHK" in l][0])
            continue
        lines = []
        for seed in range(1, 9):
            lines += [l for l in subprocess.run([exe, f"+SEED={seed}"], capture_output=True, text=True)
                      .stdout.splitlines() if l.startswith("LINKUNIT")]
        flip = [l for l in subprocess.run([exe, "+SEED=3", "+FLIP=500"], capture_output=True, text=True)
                .stdout.splitlines() if l.startswith("LINKUNIT")]
        dig = {re.search(r"digest=(\w+)", l)[1] for l in lines}
        out[name] = dict(parameters=gen, runs=lines, distinct_digests=len(dig),
                         all_pass=all(l.endswith("PASS") for l in lines), crc_flip=flip)
    return out

VFLAGS = ["--binary", "--timing", "-CFLAGS", "-O0", "-Wno-fatal", "-Wno-WIDTH", "-Wno-TIMESCALEMOD", "-Wno-lint",
          "-Wno-style", "-Wno-MULTIDRIVEN"]
# ---------------------------------------------------------------------------------------------------------------
# V4.1 HBM comparator: TP-96 (48 two-die packages) through one NVLink-class switch tier with in-switch reduction
# ---------------------------------------------------------------------------------------------------------------
HBM_T_CORE = 1 / 1.0339e9            # the HBM die clock (results/floorplan/hbm_gpu/v41_hbm_die.json clock_hz)
HBM_SWITCH = {
    "switch_core_ns": dict(value=250.0, grade="published (upper bound, used as the value)",
                           source="Broadcom Scale-Up Ethernet Framework Spec RM104 (2025) Appendix A Fig. 22: 'Switch "
                                  "Tx+Rx Latency <250ns' (tools/sync_cost_table.py r-sue); the comparator's alpha = "
                                  "2 x 209 + 250 = 668 ns (tools/arch_hbm_switched_v41.py)"),
    "in_switch_reduction": dict(value="fixed pairwise tree over the port (package) index, binary32 RNE",
                                grade="ASSUMED (deterministic order)",
                                source="NVLS / SHARP in-network reduction is the comparator's headline "
                                       "(arch_hbm_switched_v41 nvl_0p9_nvls); a FIXED-order tree is our requirement "
                                       "for bit-identical results, not a published NVSwitch property"),
    "switch_clock_ns": dict(value=HBM_T_CORE * 1e9, grade="ASSUMED", source="switch core at the die clock"),
    "link": dict(value="112G PAM4, full RS(544,514) KP4 over <= 0.8 m rack cable, 68 lanes (0.9 TB/s payload)",
                 grade="derived", source="configs/hardware/technology.json links.rom_rack_cable_serdes (hop 209 ns: "
                 "channel 200 + CDC 4 + endpoint 5); 0.9 TB/s per package per direction (arch_hbm_switched_v41)"),
    "kp4_codeword_ns": dict(value=5440 / (68 * 112.0), grade="derived", source="5,440 bits / (68 x 112 Gb/s)"),
    "channel_components_ns": dict(value=dict(tx_pcs_fec_encode=4.0, tx_analog=3.0, flight_0p8m=3.7, rx_afe_dsp=50.0,
                                              codeword=round(5440 / (68 * 112.0), 3), rx_deskew=10.0,
                                              rs544_decode=round(200 - 4 - 3 - 3.7 - 50 - 5440 / (68 * 112.0) - 10, 2)),
                                  grade="ASSUMED split of the 200 ns channel",
                                  source="flight: 4.6 ns/m twinax (Broadcom SUE); RS544 decode the remainder "
                                         "(IEEE P802.3ck gustlin_3ck_01_1118: 50-100 ns processing + interleave)"),
    "wire_stages": dict(value=16, grade="floorplan",
                        source="results/floorplan/hbm_gpu/v41_hbm_die.json crossings tp_root_to_ucie (14.7 mm, 16 "
                               "cycles); the SerDes edge is ASSUMED at the same distance"),
}


def hbm_params(P):
    t = HBM_T_CORE * 1e9
    xt = HBM_SWITCH["kp4_codeword_ns"]["value"]
    c = HBM_SWITCH["channel_components_ns"]["value"]
    L = math.ceil(math.log2(P))
    core = round(HBM_SWITCH["switch_core_ns"]["value"] / t)
    return dict(P=P, T_CORE=t, T_SW=t, X_T=round(xt, 5), X_ENC=round(c["tx_pcs_fec_encode"] / xt),
                X_DEC=round((c["rx_deskew"] + c["rs544_decode"]) / xt), SW_PIPE=core - (2 + 3 * L),
                )


def hbm_x_dly():
    c = HBM_SWITCH["channel_components_ns"]["value"]
    return round(c["tx_analog"] + c["flight_0p8m"] + c["rx_afe_dsp"] + c["codeword"], 3)


HBM_WORDS = (1, 2, 4, 8)


def hbm_fixture(outdir: Path, P: int, seed: int = 96) -> dict:
    import hdc_golden as G
    outdir.mkdir(parents=True, exist_ok=True)
    N, MAXW, LANES = 2 * P, 8, 16
    ops = [dict(mode=0, words=w) for w in HBM_WORDS] + [dict(mode=1, words=w) for w in HBM_WORDS]
    rng = np.random.default_rng(seed)
    part = np.zeros((len(ops), N, MAXW, LANES), dtype=np.uint32)
    exp = np.zeros((len(ops), MAXW, LANES), dtype=np.uint32)
    for oi, o in enumerate(ops):
        v = (np.exp2(rng.uniform(-6, 6, size=(N, MAXW, LANES))) * rng.choice([-1, 1], size=(N, MAXW, LANES))
             ).astype(np.float32)
        v[1::7] = -v[0::7][:len(v[1::7])]                     # exact cancellations across dies
        part[oi] = G.bits(v)
        if o["mode"] == 0:
            for k in range(o["words"]):
                for ln in range(LANES):
                    s = [G.add(v[2 * q, k, ln], v[2 * q + 1, k, ln]) for q in range(P)]   # in-package d0 + d1
                    while len(s) > 1:                                                   # the switch's tree
                        s = [G.add(s[2 * i], s[2 * i + 1]) for i in range(len(s) // 2)] + ([s[-1]] if len(s) % 2 else [])
                    exp[oi, k, ln] = G.bits(s[0]).item()

    def wr(path, arr):
        with path.open("w") as f:
            for lanes in arr.reshape(-1, LANES):
                f.write("".join(f"{int(x):08x}" for x in lanes[::-1]) + "\n")
    wr(outdir / "part.hex", part)
    wr(outdir / "expected.hex", exp)
    (outdir / "desc.hex").write_text("".join(f"{(o['mode'] << 31) | (i << 15) | o['words']:08x}\n"
                                             for i, o in enumerate(ops)))
    meta = dict(schema="w15_v41_hbm_nvls_fixture_v1", P=P, dies=N, ops=ops, seed=seed,
                reference="in-package d_2p + d_2p+1, then the switch's pairwise tree over packages (odd element "
                          "passes), tools/hdc_golden.add (binary32 RNE, +0 canonical)",
                images_sha256={p: sha(outdir / p) for p in ("part.hex", "expected.hex", "desc.hex")},
                golden_sha256=sha(ROOT / "tools/hdc_golden.py"))
    (outdir / "manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


# bench configurations: name -> (top, verilator -G overrides, fixture)
CONFIGS = {
    # V4.1 TP-4: the adopted engine contract (RELAY 1, receive depth 256) and the levers
    "v41_r1d256": ("tb_w15_v41_tp4", dict(RELAY=1, DEPTH=256), "l0"),
    "v41_r0d256": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=256), "l0"),
    "v41_r1d1024": ("tb_w15_v41_tp4", dict(RELAY=1, DEPTH=1024), "l0"),
    "v41_r0d1024": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=1024), "l0"),
    # PROPOSED placement (W3 die assembly rung 5, claude/w3-v41-die-assembly 01ef74dc, docs/V41_DIE_ASSEMBLY_RUNG5.md:
    # one collective at the transport-channel crossing; collective <-> UCIe / SerDes 14.62 mm): 17 stages at the
    # model's loaded 0.76 ps/um, 14 at W3's measured loaded corridor reach (1.06-1.10 mm/cycle); RELAY=0 uses
    # the direct T1 link to every partner-package die (option (b) is a full mesh)
    "v41p17_r0d256": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=256, U_WIRE=17, X_WIRE=17), "l0"),
    "v41p17_r1d256": ("tb_w15_v41_tp4", dict(RELAY=1, DEPTH=256, U_WIRE=17, X_WIRE=17), "l0"),
    "v41p17_r0d1024": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=1024, U_WIRE=17, X_WIRE=17), "l0"),
    "v41p14_r0d256": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=256, U_WIRE=14, X_WIRE=14), "l0"),
    "v41p17_r0d256_sweep": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=256, U_WIRE=17, X_WIRE=17), "sweep"),
    "v41p17_r0d1024_sweep": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=1024, U_WIRE=17, X_WIRE=17), "sweep"),
    # 2x engine: 32 FP32 lanes (128 B records), adopted placement / direct T1 / depth 1,024 (in 128 B words: 512)
    "v41p17_r0d512_w32": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=512, U_WIRE=17, X_WIRE=17, LANES=32, X_NL=1),
                          "l0w32"),
    "v41p17_r0d512_w32_sweep": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=512, U_WIRE=17, X_WIRE=17, LANES=32,
                                                       X_NL=1), "sweepw32"),
    "v41p17_r0d1024_even_sweep": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=1024, U_WIRE=17, X_WIRE=17), "sweep_even"),
    # receive FIFOs in 1R1W SRAM macros (root 2026-09-29): must reproduce the flop configs' cycles and results
    "v41p17_r0d512_w32_sram": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=512, U_WIRE=17, X_WIRE=17, LANES=32, X_NL=1,
                                                      FIFO_SRAM=1, SRAM_MACRO=1), "l0w32"),
    "v41p17_r0d512_w32_sram_sweep": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=512, U_WIRE=17, X_WIRE=17, LANES=32,
                                                            X_NL=1, FIFO_SRAM=1, SRAM_MACRO=1), "sweepw32"),
    # payload sweep (bandwidth and the latency fit) on the same binaries
    "v41_r1d256_sweep": ("tb_w15_v41_tp4", dict(RELAY=1, DEPTH=256), "sweep"),
    "v41_r0d256_sweep": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=256), "sweep"),
    "v41_r1d1024_sweep": ("tb_w15_v41_tp4", dict(RELAY=1, DEPTH=1024), "sweep"),
    "v41_r0d1024_sweep": ("tb_w15_v41_tp4", dict(RELAY=0, DEPTH=1024), "sweep"),
    # Qwen TP-2: the host binding's engine (16 lanes, depth 16) and wider / deeper engines
    "q16d16": ("tb_w15_qwen_tp2", dict(LANES=16, DEPTH=16), "q16"),
    "q16d128": ("tb_w15_qwen_tp2", dict(LANES=16, DEPTH=128), "q16"),
    "q256d64": ("tb_w15_qwen_tp2", dict(LANES=256, DEPTH=64), "q256"),
    "q256d16": ("tb_w15_qwen_tp2", dict(LANES=256, DEPTH=16), "q256"),
    "q256d128": ("tb_w15_qwen_tp2", dict(LANES=256, DEPTH=128), "q256"),
    "hbm_p48": ("tb_w15_v41_hbm_nvls", dict(hbm_params(48), X_WIRE=16, U_WIRE=16), "hbm48"),
    "hbm_p6": ("tb_w15_v41_hbm_nvls", dict(hbm_params(6), X_WIRE=16, U_WIRE=16), "hbm6"),
    "q256d64_sram": ("tb_w15_qwen_tp2", dict(LANES=256, DEPTH=64, FIFO_SRAM=1, SRAM_MACRO=0), "q256"),
    "q1024": ("tb_w15_qwen_tp2", dict(LANES=1024, DEPTH=16, U_NL=1, U_T=0.95), "q1024"),
}


def verilator_version():
    return subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip()


def binary_name(name):
    if name.endswith("_even_sweep"):
        return name[:-len("_even_sweep")]
    return name[:-len("_sweep")] if name.endswith("_sweep") else name


def build(name: str, force=False) -> Path:
    name = binary_name(name)
    top, gen, _ = CONFIGS[name] if name in CONFIGS else (name, {}, None)
    d = BUILD / name
    exe = d / f"V{top}"
    stamp = d / "w15_sources.json"
    pins = {p: sha(ROOT / p) for p in TB_SRC[top]}
    if exe.exists() and stamp.exists() and not force and json.loads(stamp.read_text()) == dict(pins=pins, gen=gen):
        return exe
    subprocess.run(["rm", "-rf", str(d)], check=True)
    cmd = [str(VERILATOR), *VFLAGS, "-j", "8", "--top-module", top, "-Mdir", str(d),
           *[f"-G{k}={v}" for k, v in gen.items()], *TB_SRC[top]]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"build {name} failed:\n{r.stderr[-3000:]}")
    stamp.write_text(json.dumps(dict(pins=pins, gen=gen)))
    return exe


OPL = re.compile(r"OP op=(\d+) die=(\d+) mode=(\d+) words=(\d+) issue=(-?\d+) first_tx=(-?\d+) last_tx=(-?\d+) "
                 r"first_vm=(-?\d+) last_vm=(-?\d+) done=(-?\d+) writes=(\d+) expect=(\d+)")
QXL = re.compile(r"QX ex=(\d+) die=(\d+) issue=(-?\d+) last_in=(-?\d+) first_out=(-?\d+) last_out=(-?\d+)")
LKL = re.compile(r"LINK src=(\d+) dst=(\d+) class=(\w+) age_min=(\d+) age_max=(\d+) wait_max=(\d+) wire=(\d+) "
                 r"faults=(\d)(\d)(\d)(\d)")
QDL = re.compile(r"W15QDONE seed=(-?\d+) faults=(\d+) link_faults=(\d+) engine_faults=(\d+) out_err=(\d+) "
                 r"min_age=(\d+)/(\d+) max_age=(\d+)/(\d+)")


def run(name: str, seed: int, det: int, drel: dict, extra: dict | None = None) -> dict:
    top, gen, fix = CONFIGS[name]
    exe = build(name)
    out = BUILD / "runs" / name / f"s{seed}_d{det}_{'_'.join(f'{k}{v}' for k, v in sorted(drel.items()))}" \
        f"{'_' + '_'.join(f'{k}{v}' for k, v in sorted((extra or {}).items())) if extra else ''}"
    out.mkdir(parents=True, exist_ok=True)
    args = [str(exe), f"+SEED={seed}", f"+VEC={VEC / fix}", f"+DET={det}", f"+OUT={out / 'vm.hex'}"]
    args += [f"+{k}={v}" for k, v in drel.items()] + [f"+{k}={v}" for k, v in (extra or {}).items()]
    r = subprocess.run(args, capture_output=True, text=True, timeout=3600)
    log = r.stdout + r.stderr
    (out / "log.txt").write_text(log)
    res = dict(seed=seed, det=det, drel=drel, extra=extra or {}, fatal=("%Fatal" in log) or ("%Error" in log))
    if top in ("tb_w15_v41_tp4", "tb_w15_v41_hbm_nvls"):
        ops = [dict(zip(("op", "die", "mode", "words", "issue", "first_tx", "last_tx", "first_vm", "last_vm",
                         "done", "writes", "expect"), map(int, m.groups()))) for m in OPL.finditer(log)]
        links = [dict(src=int(m[1]), dst=int(m[2]), cls=m[3], age_min=int(m[4]), age_max=int(m[5]),
                      wait_max=int(m[6]), wire=int(m[7]), faults=[int(m[8]), int(m[9]), int(m[10]), int(m[11])])
                 for m in LKL.finditer(log)]
        done = re.search(r"W15DONE seed=(-?\d+) det=(\d+) u_drel=(\d+) x_drel=(\d+) faults=(\d+)", log)
        vm = out / "vm.hex"
        res.update(ops=ops, links=links, completed=bool(done), faults=int(done[5]) if done else None,
                   final_mismatch=log.count("W15FINALMISMATCH"),
                   vm_sha256=sha(vm) if vm.exists() else None,
                   timing_sha256=hashlib.sha256(json.dumps(ops, sort_keys=True).encode()).hexdigest())
    else:
        ex = [dict(zip(("ex", "die", "issue", "last_in", "first_out", "last_out"), map(int, m.groups())))
              for m in QXL.finditer(log)]
        d = QDL.search(log)
        res.update(exchanges=ex, completed=bool(d), faults=int(d[2]) if d else None,
                   link_age_min=[int(d[6]), int(d[7])] if d else None,
                   link_age_max=[int(d[8]), int(d[9])] if d else None,
                   timing_sha256=hashlib.sha256(json.dumps(ex, sort_keys=True).encode()).hexdigest(),
                   vm_sha256=None)
    res["passed"] = bool(res["completed"]) and res["faults"] == 0 and not res["fatal"] and \
        res.get("final_mismatch", 0) == 0
    return res


GUARD = 1                  # cycles of release margin beyond the worst arrival seen over the sweep and its corners
CLASS_KEYS = {"ucie": ("U_DREL", "U_DLY", "U_JS"), "board": ("X_DREL", "X_DLY", "X_JS")}
CHAN_DEFAULT = {"U_DLY": LINKS["ucie_a"]["phy_adapter_tx_rx_ns"]["value"],
                "U_JS": LINKS["ucie_a"]["static_latency_variation_ns"]["value"],
                "X_DLY": round(board_stages()["chan_ns"], 3),
                "X_JS": LINKS["board_112g"]["static_latency_variation_ns"]["value"]}


def corners(classes, top=None):
    """Static latency pinned at the bottom and at the top of its range (the seeds draw the inside)."""
    lo = {}
    hi = {}
    cd = dict(CHAN_DEFAULT, **({"X_DLY": hbm_x_dly()} if top == "tb_w15_v41_hbm_nvls" else {}))
    for c in classes:
        _, dk, jk = CLASS_KEYS[c]
        lo.update({dk: cd[dk], jk: 0.0})
        hi.update({dk: round(cd[dk] + cd[jk], 4), jk: 0.0})
    return [lo, hi]


def arrivals(res, classes):
    """Hub-to-hub arrival latency (edge age + edge-to-hub wire) per link class, from a det=0 run."""
    out = {}
    if "links" in res:
        for l in res["links"]:
            a = out.setdefault(l["cls"], [10 ** 9, 0])
            a[0] = min(a[0], l["age_min"] + l["wire"])
            a[1] = max(a[1], l["age_max"] + l["wire"])
    else:
        w = QWEN_WIRE
        out["ucie"] = [min(res["link_age_min"]) + w, max(res["link_age_max"]) + w]
    return out


QWEN_WIRE = LINKS["ucie_a"]["wire_stages_qwen"]["value"]


def seeds(n):
    return list(range(1, n + 1))


def campaign_config(name, ncal=24, nmeas=12, jobs=16):
    from concurrent.futures import ThreadPoolExecutor
    top = CONFIGS[name][0]
    classes = ["ucie", "board"] if top in ("tb_w15_v41_tp4", "tb_w15_v41_hbm_nvls") else ["ucie"]
    build(name)
    big = {k[0]: 4000 for k in (CLASS_KEYS[c] for c in classes)}          # release far beyond any arrival
    cal_jobs = [(s, 0, big, None) for s in seeds(ncal)] + \
        [(1000 + i, 0, big, c) for i, c in enumerate(corners(classes, top))]
    with ThreadPoolExecutor(jobs) as ex:
        cal = list(ex.map(lambda a: run(name, *a), cal_jobs))
    arr = {}
    for r in cal:
        for c, (lo, hi) in arrivals(r, classes).items():
            a = arr.setdefault(c, [10 ** 9, 0])
            a[0], a[1] = min(a[0], lo), max(a[1], hi)
    drel = {CLASS_KEYS[c][0]: arr[c][1] + GUARD for c in classes}
    meas_jobs = [(s, 1, drel, None) for s in seeds(nmeas)] + \
        [(2000 + i, 1, drel, c) for i, c in enumerate(corners(classes, top))]
    with ThreadPoolExecutor(jobs) as ex:
        meas = list(ex.map(lambda a: run(name, *a), meas_jobs))
    return dict(name=name, classes=classes, calibration=cal, arrival_cycles=arr, drel=drel, measured=meas)


def summarize_v41(runs, clock_hz):
    """Per-op latency (issue -> last VM commit, the slowest die) and delivered bandwidth from one run."""
    ops = {}
    for o in runs["ops"]:
        ops.setdefault(o["op"], []).append(o)
    rows = []
    for k in sorted(ops):
        four = ops[k]
        issue = min(o["issue"] for o in four)
        last_vm = max(o["last_vm"] for o in four)
        first_vm = min(o["first_vm"] for o in four)
        lat = last_vm - issue + 1
        words = four[0]["words"]
        recv_bytes = four[0]["writes"] * 64                                # per die, result words committed
        rows.append(dict(op=k, mode="all_gather" if four[0]["mode"] else "all_reduce", words_per_rank=words,
                         issue_to_last_commit_cycles=lat,
                         issue_to_last_commit_ns=round(lat / clock_hz * 1e9, 1),
                         issue_to_first_commit_cycles=first_vm - issue + 1,
                         per_die_issue_to_last_commit=[o["last_vm"] - o["issue"] + 1 for o in four],
                         bytes_committed_per_die=recv_bytes,
                         effective_GBps_per_die=round(recv_bytes / (lat / clock_hz) / 1e9, 1)))
    return rows


def fit(rows):
    """Least-squares latency = fixed + per_word x words, per collective mode."""
    out = {}
    for mode in ("all_gather", "all_reduce"):
        pts = [(r["words_per_rank"], r["issue_to_last_commit_cycles"]) for r in rows if r["mode"] == mode]
        if len({x for x, _ in pts}) >= 2:
            x = np.array([p[0] for p in pts], float)
            y = np.array([p[1] for p in pts], float)
            b, a = np.polyfit(x, y, 1)
            out[mode] = dict(fixed_cycles=round(float(a), 2), cycles_per_word=round(float(b), 4), points=pts)
        elif pts:
            out[mode] = dict(points=pts)
    return out


SWEEP_WORDS = (1, 8, 36, 80, 160, 320)


def v41_sweep_fixture(outdir: Path, sweep_words=SWEEP_WORDS) -> dict:
    """12 descriptors for the payload sweep: all-gathers and all-reduces of 1..320 words per rank, operands and
    golden built exactly as tools/rtl_v41_tp_layer0_collectives.prepare builds the layer-0 fixture (pairwise
    ((r0+r1)+(r2+r3)) FP32 RNE, BF16 RNE on rnd)."""
    import hdc_golden as G
    import rtl_v41_tp_layer0_collectives as L0
    outdir.mkdir(parents=True, exist_ok=True)
    ds = [dict(mode=1, rnd=0, words=w) for w in sweep_words] + [dict(mode=0, rnd=1, words=w) for w in sweep_words]
    OPS, RANKS, MAXW, LANES = 12, 4, L0.MAXW, L0.LANES
    part = np.zeros((OPS, RANKS, MAXW, LANES), dtype=np.uint32)
    exp = np.zeros((OPS, RANKS * MAXW, LANES), dtype=np.uint32)
    words = []
    for oi, d in enumerate(ds):
        n, red = d["words"], d["mode"] == 0
        words.append((d["mode"] << 31) | (d["rnd"] << 30) | (oi << 15) | n)
        for rank in range(RANKS):
            for k in range(n):
                for lane in range(LANES):
                    if red:
                        v = np.float32([1e10, 1.0, -1e10, 1.0][rank] * (1 + ((k * LANES + lane) % 13) / 64))
                    else:
                        v = L0.operand(oi, rank, k, lane, False)
                    part[oi, rank, k, lane] = G.bits(v).item()
        for k in range(n):
            for lane in range(LANES):
                if red:
                    v = [G.from_bits(part[oi, r, k, lane]).item() for r in range(RANKS)]
                    x = G.add(G.add(v[0], v[1]), G.add(v[2], v[3]))
                    exp[oi, k, lane] = G.bits(G.to_bf16(x) if d["rnd"] else x).item()
                else:
                    for r in range(RANKS):
                        exp[oi, r * n + k, lane] = part[oi, r, k, lane]

    def wr(path, arr):
        with path.open("w") as f:
            for lanes in arr.reshape(-1, LANES):
                f.write("".join(f"{int(x):08x}" for x in lanes[::-1]) + "\n")
    wr(outdir / "part.hex", part)
    wr(outdir / "expected.hex", exp)
    (outdir / "desc.hex").write_text("".join(f"{x:08x}\n" for x in words))
    meta = dict(schema="w15_v41_sweep_fixture_v1", descriptors=ds,
                images_sha256={p: sha(outdir / p) for p in ("part.hex", "expected.hex", "desc.hex")},
                golden_sha256=sha(ROOT / "tools/hdc_golden.py"),
                operands="tools/rtl_v41_tp_layer0_collectives.operand (gathers); cancellation +-1e10 partials "
                         "(reduces: pairwise and rank-linear folds differ)")
    (outdir / "manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def summarize_qwen(res, clock_hz):
    ex = {}
    for e in res["exchanges"]:
        ex.setdefault(e["ex"], []).append(e)
    rows = []
    for k in sorted(ex):
        two = ex[k]
        issue = min(e["issue"] for e in two)
        lat = max(e["last_out"] for e in two) - issue + 1
        rows.append(dict(ex=k, issue_to_last_result_cycles=lat,
                         issue_to_first_result_cycles=min(e["first_out"] for e in two) - issue + 1))
    ar = [r["issue_to_last_result_cycles"] for r in rows[:-1]]
    return dict(allreduce_cycles_mean=round(float(np.mean(ar)), 2), allreduce_cycles_min=min(ar),
                allreduce_cycles_max=max(ar), allreduce_ns_mean=round(float(np.mean(ar)) / clock_hz * 1e9, 1),
                argmax_gather_cycles=rows[-1]["issue_to_last_result_cycles"],
                first_result_cycles=rows[1]["issue_to_first_result_cycles"],
                token_exchange_cycles=sum(r["issue_to_last_result_cycles"] for r in rows),
                exchanges=len(rows))


CLOCK = {"tb_w15_v41_tp4": 1 / 0.92e-9, "tb_w15_qwen_tp2": 1 / 0.9102e-9, "tb_w15_v41_hbm_nvls": 1.0339e9}


def config_record(c):
    name = c["name"]
    top, gen, fix = CONFIGS[name]
    clock = CLOCK[top]
    cal, meas = c["calibration"], c["measured"]
    rec = dict(top=top, parameters=gen, fixture=fix, record_bytes=4 * gen.get("LANES", 16), fixture_manifest_sha256=sha(VEC / fix / "manifest.json"),
               binary=binary_name(name), clock_hz=clock, release_guard_cycles=GUARD,
               arrival_hub_to_hub_cycles={k: dict(min=v[0], max=v[1]) for k, v in c["arrival_cycles"].items()},
               release_delay_cycles=c["drel"],
               free_running=dict(det=0, runs=len(cal), all_passed=all(r["passed"] for r in cal),
                                 distinct_timings=len({r["timing_sha256"] for r in cal}),
                                 distinct_results=len({r["vm_sha256"] for r in cal}) if top != "tb_w15_qwen_tp2" else None,
                                 seeds=[r["seed"] for r in cal], corner_channels=[r["extra"] for r in cal if r["extra"]]),
               deterministic=dict(det=1, runs=len(meas), all_passed=all(r["passed"] for r in meas),
                                  distinct_timings=len({r["timing_sha256"] for r in meas}),
                                  distinct_results=len({r["vm_sha256"] for r in meas}) if top != "tb_w15_qwen_tp2" else None,
                                  timing_sha256=meas[0]["timing_sha256"], result_sha256=meas[0]["vm_sha256"],
                                  late_faults=sum(1 for r in meas for l in r.get("links", []) if l["faults"][2]),
                                  seeds=[r["seed"] for r in meas],
                                  corner_channels=[r["extra"] for r in meas if r["extra"]]))
    if top in ("tb_w15_v41_tp4", "tb_w15_v41_hbm_nvls"):
        rows = summarize_v41(meas[0], clock)
        rec["collectives"] = rows
        rec["fit"] = fit(rows)
        rec["sum_issue_to_last_commit_cycles"] = sum(r["issue_to_last_commit_cycles"] for r in rows)
        # the free-running spread of each op's latency
        spread = {}
        for r in cal:
            for row in summarize_v41(r, clock):
                spread.setdefault(row["op"], []).append(row["issue_to_last_commit_cycles"])
        rec["free_running_latency_range"] = {k: [min(v), max(v)] for k, v in spread.items()}
    else:
        rec["exchanges"] = summarize_qwen(meas[0], clock)
        fr = [summarize_qwen(r, clock)["allreduce_cycles_mean"] for r in cal]
        rec["free_running_allreduce_mean_range"] = [min(fr), max(fr)]
    return rec


def pins():
    files = sorted({*LINK_SRC, "rtl/link/ot_link_port_harden.sv", *[p for v in TB_SRC.values() for p in v],
                    "tools/w15_collectives.py", "tools/rtl_v41_tp_layer0_collectives.py", "tools/hdc_golden.py",
                    "results/rtl/hdc_v41x_fullshape_program_bind.json", "configs/hardware/technology.json",
                    "results/floorplan/v41_pack_expanded_woa.json", "tools/uarch_model.py"})
    return {p: sha(ROOT / p) for p in files}


def git_state():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
    return dict(head=head, dirty=[d for d in dirty if d.strip()])


def campaign(names, ncal, nmeas, out: Path):
    old = json.loads(out.read_text()) if out.exists() else {}
    cfgs = dict(old.get("configs", {}))
    for n in names:
        c = campaign_config(n, ncal, nmeas)
        cfgs[n] = config_record(c)
        print(n, json.dumps({k: cfgs[n][k] for k in ("release_delay_cycles", "arrival_hub_to_hub_cycles")}),
              "det timings", cfgs[n]["deterministic"]["distinct_timings"], "free timings",
              cfgs[n]["free_running"]["distinct_timings"], flush=True)
    rec = dict(schema="w15_collectives_v1",
               claim_boundary="Cycle-accurate RTL simulation (Verilator 5.050, --timing) of the die-side collective "
                              "engines, DMA, behavioural VM and a synthesizable link layer (framing, CRC-32, credit "
                              "return, Gray-code CDC FIFOs, deterministic release) on per-die clocks; the analog "
                              "PHY, channel and the PHY's PCS/FEC pipelines are timing models whose constants are "
                              "cited or ASSUMED in `links`.  Layer-0 collective descriptors are the emitted program; "
                              "operands are the synthetic arithmetic stress fixture, not a model token.",
               git=git_state(), source_sha256=pins(), verilator=verilator_version(), verilator_flags=VFLAGS,
               links=dict(LINKS, board_stages=board_stages()), configs=cfgs)
    for k in ("model_feed", "physical", "unit_checks", "unit_checks_source_sha256", "fixed_floor"):
        if k in old:
            rec[k] = old[k]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str) + "\n")
    return rec


SWEEP_WORDS_EVEN = (2, 8, 36, 80, 160, 320)


def widen_fixture(src: Path, dst: Path, k: int = 2) -> dict:
    """The same operands and golden images for a k-times wider engine: k consecutive 16-lane words (64 B) of a rank
    become one 16k-lane word (element e keeps its value: lane l of wide word w is element (w*k*16 + l)), descriptor
    word counts divide by k.  Every count in the source must be a multiple of k."""
    dst.mkdir(parents=True, exist_ok=True)
    desc = [int(x, 16) for x in (src / "desc.hex").read_text().split()]
    OPS, RANKS, MAXW = 12, 4, 320
    new_desc = []
    for d in desc:
        n = d & 0x7FFF
        assert n % k == 0, (d, k)
        new_desc.append((d & ~0x7FFF) | (n // k))
    (dst / "desc.hex").write_text("".join(f"{x:08x}\n" for x in new_desc))
    for name in ("part.hex", "expected.hex"):
        lines = (src / name).read_text().split()
        assert len(lines) == OPS * RANKS * MAXW
        out = []
        # part: one MAXW block per (op, rank); expected: one contiguous RANKS x MAXW region per op
        bs = MAXW if name == "part.hex" else RANKS * MAXW
        for blk in range(OPS * RANKS * MAXW // bs):
            b = lines[blk * bs:(blk + 1) * bs]
            w = ["".join(b[i * k + j] for j in reversed(range(k))) for i in range(bs // k)]
            out += w + ["0" * len(w[0])] * (bs - len(w))
        (dst / name).write_text("\n".join(out) + "\n")
    meta = dict(schema="w15_v41_widened_fixture_v1", widen=k, source_manifest_sha256=sha(src / "manifest.json"),
                images_sha256={p: sha(dst / p) for p in ("part.hex", "expected.hex", "desc.hex")},
                note="element values and golden identical to the source fixture; only the word packing changes")
    (dst / "manifest.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("qwen-fixture")
    q.add_argument("dir", type=Path)
    q.add_argument("--lanes", type=int, default=16)
    q.add_argument("--h", type=int, default=4096)
    sub.add_parser("links")
    sf = sub.add_parser("sweep-fixture")
    sf.add_argument("dir", type=Path)
    cp = sub.add_parser("campaign")
    cp.add_argument("--config", action="append")
    cp.add_argument("--ncal", type=int, default=24)
    cp.add_argument("--nmeas", type=int, default=12)
    cp.add_argument("--out", type=Path, default=OUT)
    uc = sub.add_parser("unit")
    uc.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    if a.cmd == "qwen-fixture":
        print(json.dumps(qwen_fixture(a.dir, a.lanes, a.h), indent=1))
    elif a.cmd == "sweep-fixture":
        print(json.dumps(v41_sweep_fixture(a.dir)["images_sha256"]))
    elif a.cmd == "campaign":
        campaign(a.config or list(CONFIGS), a.ncal, a.nmeas, a.out)
    elif a.cmd == "unit":
        rec = json.loads(a.out.read_text())
        rec["unit_checks"] = unit_checks()
        rec["unit_checks_source_sha256"] = {p: sha(ROOT / p) for p in sorted({*TB_SRC["tb_w15_link_unit"],
                                                                             *TB_SRC["tb_w15_crc32"]})}
        a.out.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str) + "\n")
        print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "runs"} for k, v in rec["unit_checks"].items()},
                         indent=1))
    elif a.cmd == "links":
        print(json.dumps(dict(LINKS, board_stages=board_stages()), indent=1))


if __name__ == "__main__":
    main()
