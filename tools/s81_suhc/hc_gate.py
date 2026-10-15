#!/usr/bin/env python3
"""Exact gate + throughput bench of the S81 HC die master dsfd_sp_hc (stream s81-suhc-1011, 2026-10-11).

One RUN drives the master through its dsfd_sp_ctrl engine adapter (controller-clock command pulses, QD 8 credits,
the stage sequencer's decoupled issue) with a 20-job program over two job slots (two users' layers interleaved):

    GAIN_LOAD x4 (attn / ffn gain of each chain)
    H_LOAD   slot 0, slot 1               (stage entry: h from the VM, BF16 packed)
    COEF + NORM(QUANT) attn, slot 0 / 1   (hc_pre -> RMSNorm -> FP8 act-quant = attn.quant)
    POST attn, slot 0 / 1                 (hc_post in place, y on the direct collective bus)
    COEF + NORM(QUANT + Y) ffn, slot 0 / 1(= ffn.norm.scale + ffn.quant)
    POST ffn, slot 0 / 1
    H_STORE slot 0 / 1                    (stage exit)

The expected VM image is the CPU golden (tools/hdc_golden_v41: hc_pre mix, rmsnorm_bf16, quant_fp8 / qdq_fp8 through
rtl_hdc_v41_blockdot_campaign.aq_expect, the hc_post lowering order of tools/dsrom_su_hcpost.golden) chained across
the two blocks: the FFN block reads the h the attention hc_post produced, and H_STORE returns the h of the next
layer.  Golden runs use the 1M token's real operands (su_cases pickle: L0 / L2 attn + ffn hc_pre_norm and hc_post
cases; the chain replay is asserted equal to every check the pickle holds); stress runs use random operands with
signed zeros, subnormals and wide exponents.

    python3 tools/s81_suhc/hc_gate.py prep --cases su_cases.pkl --out DIR [--ng 256]
    python3 tools/s81_suhc/hc_gate.py run  --out DIR [--ng 256] [--mut M] [--amut A] [--fp dpi|rtl]
    python3 tools/s81_suhc/hc_gate.py record --out DIR --rec results/rtl/s81_suhc_20261011/hc_gate.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pickle
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
F = np.float32
D, HC = 5120, 4
K_HLOAD, K_HSTORE, K_COEF, K_POST, K_NORM, K_GAIN = 0, 1, 2, 3, 4, 5
# VM map (rows)
G_BASE, H_BASE, C_BASE, O_BASE, S_BASE = 0, 1280, 2560, 3072, 6144
HROWS = HC * D * 16 // 512          # 640
GROWS = D // 16                     # 320

RTL = ["rtl/dsrom_sys/s81_suhc/ot_s81_hc_core.sv", "rtl/dsrom_sys/s81_suhc/dsfd_sp_hc.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cpin.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_comb.sv", "rtl/link/ot_fifo_sram_fwft.sv",
       "physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v",
       "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_croot.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crooty.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crootr.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_stree.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_hroot.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cseq.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crx.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_caq.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cntree.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ccr.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cpad.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ccf.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ctile.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv",
       "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_pad_split.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ntree.sv",
       "rtl/dsrom_sys/s81_ctrl/ot_s81_engine_adapter.sv", "rtl/lib/ot_async_fifo.sv", "rtl/lib/ot_reset_sync.sv",
       "rtl/lib/ot_skid_buffer.sv",
       "rtl/hdc/v41x/ot_dsrom_su_hcpost.sv", "rtl/hdc/v41x/ot_dsrom_su_add6.sv", "rtl/hdc/v41x/ot_dsrom_su_norm.sv",
       "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv",
       "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_fastfp_lat_f12.sv", "rtl/hdc/v41/ot_hdc_fsqrt.sv",
       "rtl/hdc/v41/ot_hdc_fdiv.sv", "rtl/hdc/v41/ot_hdc_softplus.sv", "rtl/hdc/v41x/ot_hdc_v41x_sfu.sv",
       "rtl/hdc/v41/ot_hdc_actquant.sv", "rtl/hdc/v41x/ot_dsrom_aq12.sv", "rtl/hdc/v41x/ot_dsrom_divc.sv"]
FP = dict(
    rtl=["rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv",
         "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv"],
    dpi=["rtl/test/sim_hdc_v41x_fastfp_dpi.sv", "rtl/test/sim_hdc_v41x_fastfp_wrap.sv",
         "rtl/test/sim_hdc_v41x_fastfp_dpi.cpp", "rtl/test/sim_hdc_fp32_f12_dpi_tops.sv",
         "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv", "rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp",
         "rtl/test/sim_hdc_fp32_lat_tops.sv", "rtl/test/sim_hdc_prefix_beh.sv", "rtl/test/sim_dsrom_fp32_add_l6_dpi.sv"])
TB = "rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_master.sv"
VL = Path(os.environ.get("OPENTALLAS_TOOLS_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
VERILATOR = str(VL) if VL.exists() else "verilator"


# ---- per-tile qualification of the hard HC leaves (s81hc-1013 r5) ---------------------------------------------------
# A hard tile with no golden of its own is qualified by the composition: the gate is built with a PROBE in the tile's
# module (an initial $display of every instance path and parameter tuple: the bench must elaborate the routed module at
# the routed parameters, TILES[..]["routed"]) and must pass bit-exact; the mutant is ONE edit inside that module's own
# text (TILES[..]["mut"]) and the same gate must then fail.  Both edits are made on a copy in the build directory; the
# tree is not touched.  --pad-hard defines OT_S81_HC_PAD_HARD: the pad leaves are then instantiated with their default
# (hardened) parameters and the parents $fatal unless the production tuple holds.
_CTNL_MUT = ("=fdx[O_D+rp*P_BITS+PBIT];", "=fdx[O_D+rp*P_BITS+PBIT]^(b==94);")
_PADS, _CTH, _CRY = ("rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_pad_split.sv", "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv",
                     "rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crooty.sv")
TILES = {
    "ot_s81_hc_pad_f8":    dict(src=_PADS, routed=[{}], mut=(".D(DEPTH)) u_d", ".D(DEPTH-1)) u_d")),
    "ot_s81_hc_pad_f5r1":  dict(src=_PADS, routed=[{}], mut=(".D(DEPTH)) u_d", ".D(DEPTH-1)) u_d")),
    "ot_s81_hc_pad_r6":    dict(src=_PADS, routed=[{}], mut=(".D(DEPTH)) u_d", ".D(DEPTH-1)) u_d")),
    "ot_s81_hc_pad_r5":    dict(src=_PADS, routed=[{}], mut=(".D(DEPTH)) u_d", ".D(DEPTH-1)) u_d")),
    "ot_s81_hc_pad_meta2": dict(src=_PADS, routed=[{}], mut=(".D(DEPTH),.RESET(1))u_v", ".D(DEPTH-1),.RESET(1))u_v")),
    "ot_s81_hc_ctnl_l0":   dict(src=_CTH, routed=[dict(PIN_STAGE=1, CHAIN_STEP=6)], mut=_CTNL_MUT),
    "ot_s81_hc_ctnl_l1":   dict(src=_CTH, routed=[dict(PIN_STAGE=1, CHAIN_STEP=6)], mut=_CTNL_MUT),
    "ot_s81_hc_ctnl_l2":   dict(src=_CTH, routed=[dict(PIN_STAGE=1, CHAIN_STEP=6)], mut=_CTNL_MUT),
    "ot_s81_hc_ctnl_l3":   dict(src=_CTH, routed=[dict(PIN_STAGE=1, CHAIN_STEP=6)], mut=_CTNL_MUT),
    "ot_s81_hc_crooty_w":  dict(src=_CRY, routed=[dict(C=0), dict(C=2)],
                                mut=("wq_row[14 * s +: 14] <= w_c[WSL * s + 1 +: 14];",
                                     "wq_row[14 * s +: 14] <= w_c[WSL * s + 1 +: 14] ^ 14'd1;")),
}
# ---- the other closed HC tiles (s81hc-1013 r6): same method.  "routed" = the closed kit's tuple (kit.env PARAMS over the
# module defaults); a parameter the module body never uses (tile_inert) is left out of the comparison and reported.
_H = "rtl/dsrom_sys/s81_suhc/hier/"
_H2 = dict(HALF=1, RLY=2, RF=4, DW=6)                    # the *h2 kits (crxh2 / cseqh2 / cntreeh2; ccr: module defaults)
_BIT = lambda w, at: "({{(%s-1){1'b0}}, 1'b1} << (%s))" % (w, at)
_CR = _H + "ot_s81_hc_crootr.sv"
# cseq published views predate PIPE: bind their actual behavior explicitly.
# Current RTL defaults may change, but cannot requalify a changed physical master.
TILES.update({
    "ot_s81_hc_cpin":     dict(src=_H + "ot_s81_hc_cpin.sv", routed=[{}], mut=("rq_row <= n_rq_row;", "rq_row <= n_rq_row ^ 14'd1;")),
    "ot_s81_hc_caq":      dict(src=_H + "ot_s81_hc_caq.sv", routed=[{}], mut=("x_q <= rdd;", "x_q <= rdd ^ 512'h8000;")),
    "ot_s81_hc_crx":      dict(src=_H + "ot_s81_hc_crx.sv", routed=[_H2], mut=("jb <= j_base;", "jb <= j_base ^ 14'd1;")),
    "ot_s81_hc_ccr":      dict(src=_H + "ot_s81_hc_ccr.sv", routed=[{}], mut=("crd <= ch_rd;", "crd <= ch_rd ^ " + _BIT("RDW", "P_D + 15") + ";")),
    "ot_s81_hc_cseq":     dict(src=_H + "ot_s81_hc_cseq.sv", routed=[dict(_H2, PIPE=0, PD=40)], mut=("ssq <= t_ss;", "ssq <= t_ss ^ 32'h00800000;")),
    "ot_s81_hc_cntree":   dict(src=_H + "ot_s81_hc_cntree.sv", routed=[_H2], mut=("ss <= nv_[1];", "ss <= nv_[1] ^ 32'h00800000;")),
    "ot_s81_hc_ctfn":     dict(src=_CTH, routed=[{}], mut=("fd <= fd_in;", "fd <= fd_in ^ " + _BIT("FDW", "O_D + 15") + ";")),
    "ot_s81_hc_ctfx":     dict(src=_CTH, routed=[{}], mut=("fdx <= fd_in;", "fdx <= fd_in ^ " + _BIT("FXW", "O_D + 15") + ";")),
    "ot_s81_hc_ctfx_cap": dict(src=_CTH, routed=[{}], mut=("else fv_local <= fv;", "else fv_local <= 0;")),
    "ot_s81_hc_ctfs":     dict(src=_CTH, routed=[{}], mut=("fd_out <= fdm_d;", "fd_out <= fdm_d ^ " + _BIT("FDW", "O_D + 15") + ";")),
    "ot_s81_hc_ctpl":     dict(src=_CTH, routed=[dict(PIN_STAGE=1)], mut=("x_d <= b_d;", "x_d <= b_d ^ 160'h00800000;")),
    "ot_s81_hc_ctra": dict(src=_CTH, routed=[dict(CHAIN_STEP=6, READ_STAGE=1)], mut=("assign rq_q_c1 = rq_q;", "assign rq_q_c1 = rq_q ^ " + _BIT("16*S_RT", "5") + ";")),
    "ot_s81_hc_ctrb": dict(src=_CTH, routed=[dict(CHAIN_STEP=6, READ_STAGE=1)], mut=("assign rdm = rdm_w[RDW-1 -: 512 * SH];", "assign rdm = rdm_w[RDW-1 -: 512 * SH] ^ " + _BIT("512 * SH", "15") + ";")),
    "ot_s81_hc_ctrn":     dict(src=_CTH, routed=[{}], mut=("rd_out <= rd_out_d;", "rd_out <= rd_out_d ^ " + _BIT("RDW", "123") + ";")),
    "ot_s81_hc_crootr_t": dict(src=_CR, routed=[dict(C=0), dict(C=2)], mut=("s_ex <= ex_r;", "s_ex <= ex_r ^ 32'h00800000;")),
    "ot_s81_hc_crootr_f": dict(src=_CR, routed=[dict(C=0), dict(C=2)], mut=(".D(RF)) u_rfd", ".D(RF - 1)) u_rfd")),
    "ot_s81_hc_crootr_r": dict(src=_CR, routed=[dict(C=0), dict(C=2)], mut=("s_rd <= rd_r;", "s_rd <= rd_r ^ " + _BIT("RDW", "P_D + 15") + ";")),
    "ot_s81_hc_crootr_w": dict(src=_CR, routed=[dict(C=0), dict(C=2)], mut=("p_w <= w_r;", "p_w <= w_r ^ 2'd2;")),
    "ot_s81_hc_ccf":      dict(src=_H + "ot_s81_hc_ccf.sv", routed=[dict(HALF=1, RLY=2, RF=5, DW=6, FIFO_SLICE=512, KEEP_POP=1, Y_RELAY=1)],
                               mut=("ty[YS1-1:0] = yf_head;", "ty[YS1-1:0] = yf_head ^ " + _BIT("YS1", "30") + ";")),
    # r8: the y path is 11 slice leaves a column root (ot_s81_hc_crooty YLEAF 1); ot_s81_hc_crooty_y (11 SRAM macros, never
    # closed) is the lockstep reference only (tools/s81_suhc/cryy_split_bench.sh) and is not elaborated in production
    "ot_s81_hc_cryys":    dict(src=_CRY, routed=[{}], mut=("p_y <= yh;", "p_y <= yh ^ " + _BIT("W", "30") + ";")),
})
# ---- NORM tree variant tiles (el1014-s81-norm-tree, hier/ot_s81_hc_ntree.sv; probed / mutated only with --ntree 1)
_NT = _H + "ot_s81_hc_ntree.sv"
TILES.update({
    "ot_s81_hc_ctfx_nt": dict(src=_NT, routed=[dict(CHAIN_STEP=6)], mut=("if (!rst_in) v <= 0; else v <= fv;", "if (!rst_in) v <= 0; else v <= 0;")),
    "ot_s81_hc_ctfs_nt": dict(src=_NT, routed=[{}], mut=("else dl_out <= dl_in;", "else dl_out <= dl_in ^ (275'd1 << 40);")),
    "ot_s81_hc_cncla":   dict(src=_NT, routed=[dict(C=0), dict(C=1), dict(C=2)], mut=("pi <= {5'd0, i_q}; ex <= ex_w;", "pi <= {5'd0, i_q}; ex <= ex_w ^ (1 << 29);")),
    "ot_s81_hc_cnclb":   dict(src=_NT, routed=[dict(C=0), dict(C=1), dict(C=2)], mut=("always @(posedge sk) ex <= ex_w;", "always @(posedge sk) ex <= ex_w ^ (1 << 29);")),
    "ot_s81_hc_cnrsq":   dict(src=_NT, routed=[{}], mut=("else ngo <= f_fv[S_RD + 1];", "else ngo <= 1'b0;")),
})
TILE_RE = re.compile(r"^HCTILE (\w+) (\S+) ?(.*)$", re.M)


def tile_block(text, mod):
    """(start, end) of module `mod` in text, `module` .. `endmodule` inclusive"""
    m = re.search(r"(?m)^module\s+%s\b" % re.escape(mod), text)
    if not m:
        sys.exit(f"tile {mod}: module not found")
    e = text.index("endmodule", m.start())
    return m.start(), e + len("endmodule")


def _tile_head(text, mod):
    """(parameter header text, rest of the module) with comments removed; a module without #( .. ) has an empty header"""
    a, b = tile_block(text, mod)
    blk = re.sub(r"//[^\n]*", "", text[a:b])
    m = re.match(r"module\s+\w+\s*#\(", blk)
    if not m:
        return "", blk
    depth, i = 1, m.end()
    while depth:
        depth += {"(": 1, ")": -1}.get(blk[i], 0)
        i += 1
    return blk[m.end():i - 1], blk[i:]


def tile_params(text, mod):
    """{name: default} of the module's header parameters, in order; a default may be an expression of earlier ones"""
    head, _ = _tile_head(text, mod)
    out = {}
    for name, expr in re.findall(r"(\w+)\s*=\s*([^,]+?)\s*(?:,|$)", re.sub(r"parameter\s+integer", "", head).strip()):
        out[name] = int(eval(expr, {"__builtins__": {}}, dict(out)))
    return out


def tile_inert(text, mod):
    """header parameters the module cannot depend on: not named in the ports / body, nor (transitively) in a localparam
    statement that defines a name the ports / body use.  Conservative: a whole localparam statement is one group."""
    head, rest = _tile_head(text, mod)
    ident = lambda s: set(re.findall(r"[A-Za-z_]\w*", s))
    groups = [(set(re.findall(r"(\w+)\s*(?<![<>=!])=(?!=)", g)), ident(g)) for g in re.findall(r"\blocalparam\b[^;]*;", rest)]
    live = ident(re.sub(r"\blocalparam\b[^;]*;", "", rest))
    grew = True
    while grew:
        grew = False
        for defs, used in groups:
            if defs & live and not used <= live:
                live |= used
                grew = True
    return [p for p in tile_params(text, mod) if p not in live]


def tile_sha(text, mod):
    a, b = tile_block(text, mod)
    return hashlib.sha256(text[a:b].encode()).hexdigest()


def tile_edit(srcs, obj, probes, tmut):
    """source list with the probed / mutated files replaced by edited copies under obj"""
    edits = {}
    for mod in probes:
        edits.setdefault(TILES[mod]["src"], []).append(("probe", mod))
    if tmut:
        edits.setdefault(TILES[tmut]["src"], []).append(("mut", tmut))
    for rel, ops in edits.items():
        text = (ROOT / rel).read_text()
        for op, mod in ops:
            a, b = tile_block(text, mod)
            blk = text[a:b]
            if op == "mut":
                old, new = TILES[mod]["mut"]
                if blk.count(old) < 1:
                    sys.exit(f"tile mutant {mod}: site not found")
                blk = blk.replace(old, new)
            else:
                names = list(tile_params(text, mod))
                fmt = " ".join(f"{n}=%0d" for n in names)
                blk = blk[:-len("endmodule")] + f'    initial $display("HCTILE {mod} %m {fmt}"{"".join(", " + n for n in names)});\nendmodule'
            text = text[:a] + blk + text[b:]
        dst = obj / ("tileedit_" + Path(rel).name)
        dst.write_text(text)
        srcs = [dst if Path(x) == ROOT / rel else x for x in srcs]
    return srcs


def tile_check(stdout, probes):
    """per probed tile: the instances the bench elaborated, and whether each is a routed parameter tuple (all seen).
    Parameters the module body cannot depend on (tile_inert) are not compared; they are listed with the values seen."""
    seen = {}
    for mod, path, kv in TILE_RE.findall(stdout):
        seen.setdefault(mod, []).append((path, {k: int(v) for k, v in (x.split("=") for x in kv.split())}))
    rep = {}
    for mod in probes:
        text = (ROOT / TILES[mod]["src"]).read_text()
        dflt = tile_params(text, mod)
        inert = tile_inert(text, mod)
        cut = lambda q: {k: v for k, v in q.items() if k not in inert}
        want = [dict(dflt, **o) for o in TILES[mod]["routed"]]
        inst = seen.get(mod, [])
        hit = lambda q: any(cut(q) == cut(p) for p in want)
        rep[mod] = dict(instances=len(inst), routed_params=want, params_seen=[p for p in want if any(cut(q) == cut(p) for _, q in inst)],
                        foreign=[dict(path=a, params=q) for a, q in inst if not hit(q)][:4],
                        inert_params=inert,
                        inert_differing=sorted({f"{k}={q[k]} (routed {p[k]})" for _, q in inst for p in want if cut(q) == cut(p) for k in inert if q[k] != p[k]}),
                        example=inst[0][0] if inst else None, example_params=inst[0][1] if inst else None,
                        module_sha256=tile_sha(text, mod),
                        ok=bool(inst) and all(hit(q) for _, q in inst) and all(any(cut(q) == cut(p) for _, q in inst) for p in want))
    return rep


def dpi_rest(obj):
    """The RTL helpers the DPI float models do not replace (f12 cuts / l6 / l7 variants, lzc / ksa / mul24 rows):
    rtl/hdc/ot_hdc_fp32_f12.sv and rtl/hdc/ot_hdc_fastfp.sv minus every module a DPI source defines."""
    dpi_mods = set()
    for s_ in FP["dpi"]:
        if s_.endswith(".sv"):
            dpi_mods |= set(re.findall(r"^module\s+(\w+)", (ROOT / s_).read_text(), re.M))
    out = []
    for src in ("rtl/hdc/ot_hdc_fp32_f12.sv", "rtl/hdc/ot_hdc_fastfp.sv"):
        keep = []
        for blk in re.split(r"(?m)^(?=module\s)", (ROOT / src).read_text()):
            m_ = re.match(r"module\s+(\w+)", blk)
            if not m_ or m_.group(1) not in dpi_mods:
                keep.append(blk)
        f = obj / ("rest_" + Path(src).name)
        f.write_text("".join(keep))
        out.append(f)
    return out


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def u32(x):
    return np.asarray(x, F).view(np.uint32)


def f32(b):
    return np.asarray(b, np.uint32).view(F)


def bf16bits(x):
    return (u32(x) >> 16).astype(np.int64)


def pack(vals, width):
    acc = 0
    for i, v in enumerate(vals):
        acc |= (int(v) & ((1 << width) - 1)) << (width * i)
    return acc


# ---------------------------------------------------------------------------------------------------------------- golden
def g_norm(h, pre, w, eps):
    import hdc_golden_v41 as V
    x = V.to_bf16(V.seqsum([V.mul(F(pre[k]), h[k]) for k in range(HC)]))
    return V.rmsnorm_bf16(x, np.asarray(w, F), F(eps))


def g_post(res, y, comb, post):
    import dsrom_su_hcpost as P
    return P.golden(res, y, comb, post).reshape(HC, D)


def g_quant(y):
    import rtl_hdc_v41_blockdot_campaign as BC
    out = []
    for b in np.asarray(y, F).reshape(-1, 32):
        f_, e, codes, _yy = BC.aq_expect(b, False)
        assert f_ == 0
        out.append((e & 0x3FF, codes))
    return out


# ---------------------------------------------------------------------------------------------------------------- image
class Run:
    def __init__(self, ng):
        self.ng, self.n = ng, 4 * ng
        self.nv = D // self.n
        self.vm, self.exp, self.prog, self.y = {}, {}, [], []

    def h_rows(self, h):
        """BF16-packed h: row q = elements 8q .. 8q+7, copy k of element e at 16*((e%8)*4+k)."""
        hb = bf16bits(h)                                       # [4][D]
        assert np.array_equal((u32(h) & 0xFFFF), np.zeros_like(u32(h))), "h not BF16"
        return [pack([hb[k][e] for e in range(8 * q, 8 * q + 8) for k in range(HC)], 16) for q in range(HROWS)]

    def job(self, kind, slot, base, gsel=0, quant=0, yout=0):
        op = len(self.prog)
        arg = (kind << 20) | (gsel << 18) | (yout << 15) | (quant << 14) | base
        self.prog.append((slot << 83) | (arg << 7) | op)

    def norm_rows(self, base, y, quant, yout):
        n, nv = self.n, self.nv
        crows, erows, yrows = n // 64, (n + 1023) // 1024, n // 32
        q = g_quant(y) if quant else None
        for v in range(nv):
            if quant:
                blk = q[v * (n // 32):(v + 1) * (n // 32)]
                for r in range(crows):
                    self.exp[base + v * crows + r] = pack([c for b in blk[2 * r:2 * r + 2] for c in b[1]], 8)
                for r in range(erows):
                    self.exp[base + nv * crows + v * erows + r] = pack([b[0] for b in blk[32 * r:32 * r + 32]], 16)
            if yout:
                yb = bf16bits(y)
                off = base + (nv * (crows + erows) if quant else 0)
                for r in range(yrows):
                    self.exp[off + v * yrows + r] = pack(yb[v * n + 32 * r: v * n + 32 * r + 32], 16)

    def build(self, chains):
        """chains[c] = dict(h, attn=(pre, w, eps, comb, post, y), ffn=(...))"""
        ng = self.ng
        for c, ch in enumerate(chains):
            for b, blk in enumerate(("attn", "ffn")):
                w = u32(ch[blk][1])
                for r in range(GROWS):
                    self.vm[G_BASE + (2 * c + b) * GROWS + r] = pack(w[16 * r:16 * r + 16], 32)
                pre, _w, eps, comb, post, _y = ch[blk]
                self.vm[C_BASE + 4 * c + 2 * b] = pack(u32(np.asarray(comb, F).reshape(-1)), 32)
                self.vm[C_BASE + 4 * c + 2 * b + 1] = pack(list(u32(pre)) + list(u32(post)) + [int(u32([eps])[0])], 32)
            for q, row in enumerate(self.h_rows(ch["h"])):
                self.vm[H_BASE + c * HROWS + q] = row
        for g in range(4):
            self.job(K_GAIN, 0, G_BASE + g * GROWS, gsel=g)
        for c in range(len(chains)):
            self.job(K_HLOAD, c, H_BASE + c * HROWS)
        h = [np.asarray(ch["h"], F).reshape(HC, D) for ch in chains]
        for b, blk in enumerate(("attn", "ffn")):
            for c, ch in enumerate(chains):
                pre, w, eps, comb, post, y = ch[blk]
                quant, yout = 1, (1 if blk == "ffn" else 0)
                base = O_BASE + (2 * c + b) * 512
                self.job(K_COEF, c, C_BASE + 4 * c + 2 * b)
                self.job(K_NORM, c, base, gsel=2 * c + b, quant=quant, yout=yout)
                yn = g_norm(h[c], pre, w, eps)
                ch.setdefault("norm_out", {})[blk] = yn
                self.norm_rows(base, yn, quant, yout)
            for c, ch in enumerate(chains):
                pre, w, eps, comb, post, y = ch[blk]
                self.job(K_POST, c, 0)
                yv = u32(y)
                for bt in range(D // ng):
                    self.y.append(pack(yv[bt * ng:(bt + 1) * ng], 32))
                h[c] = g_post(h[c], np.asarray(y, F), np.asarray(comb, F).reshape(HC, HC), np.asarray(post, F))
                ch.setdefault("h_out", {})[blk] = h[c]
        for c in range(len(chains)):
            self.job(K_HSTORE, c, S_BASE + c * HROWS)
            for q, row in enumerate(self.h_rows(h[c])):
                self.exp[S_BASE + c * HROWS + q] = row

    def write(self, d: Path, meta):
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "vm.mem", "w") as f:
            for a in sorted(self.vm):
                f.write(f"@{a:x}\n{self.vm[a]:0128x}\n")
        with open(d / "expa.mem", "w") as fa, open(d / "expd.mem", "w") as fd:
            for a in sorted(self.exp):
                fa.write(f"{a:04x}\n")
                fd.write(f"{self.exp[a]:0128x}\n")
        (d / "prog.mem").write_text("".join(f"{p:021x}\n" for p in self.prog))
        (d / "y.mem").write_text("".join(f"{v:0{self.ng * 8}x}\n" for v in self.y))
        (d / "n.mem").write_text(f"{len(self.prog):08x}\n{len(self.exp):08x}\n{len(self.y):08x}\n")
        (d / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")


def chains_golden(cases):
    by = {c["name"]: c for c in cases["cases"]}
    out = []
    for L in ("L0", "L2"):
        pn = {b: by[f"{L}.hc_pre_norm.{b}"] for b in ("attn", "ffn")}
        hp = {b: by[f"{L}.hc_post.{b}"] for b in ("attn", "ffn")}
        h0 = dict(pn["attn"]["init"])[64].reshape(HC, D)
        ch = dict(h=h0, src=L)
        for b in ("attn", "ffn"):
            c = pn[b]
            img = dict(c["init"])
            pre = img[20544]
            ro_, so = c["ops"][3], c["ops"][4]
            eps = f32([ro_["imm2"]])[0]
            w = f32(c["cr_lo"][so["cbase"]:so["cbase"] + D])
            pimg = dict(hp[b]["init"])
            ch[b] = (pre, w, eps, pimg[25664].reshape(HC, HC), pimg[25680], pimg[20544])
            ch[b + "_checks"] = (c["checks"], hp[b]["checks"], img[64].reshape(HC, D), pimg[64].reshape(HC, D))
        out.append(ch)
    return out


def chains_stress(rng, kinds):
    import hdc_golden_v41 as V
    out = []
    for t in kinds:
        h = V.to_bf16((rng.standard_normal((HC, D)) * [1.0, 37.0, 1e-3, 0.5][t % 4]).astype(F))
        m = rng.random((HC, D))
        h[m < 0.04] = F(0.0)
        h[(m > 0.04) & (m < 0.06)] = F(-0.0)
        if t >= 2:
            h = V.to_bf16((h * F(2.0) ** rng.integers(-60, 40, size=(HC, D)).astype(F)).astype(F))
        ch = dict(h=h, src=f"stress{t}")
        for b in ("attn", "ffn"):
            pre = (rng.random(HC) * 1.5).astype(F)
            w = V.to_bf16((rng.standard_normal(D) * 0.3 + 1.0).astype(F))
            y = V.to_bf16((rng.standard_normal(D) * [0.5, 8.0, 0.01, 2.0][t % 4]).astype(F))
            y[rng.random(D) < 0.03] = F(-0.0)
            comb = rng.random((HC, HC)).astype(F)
            post = (rng.random(HC) * 2).astype(F)
            ch[b] = (pre, w, F(1e-6), comb, post, y)
        out.append(ch)
    return out


def cmd_prep(a):
    out = Path(a.out)
    rows = []
    cases = pickle.loads(Path(a.cases).read_bytes())
    gold = chains_golden(cases)
    runs = [("golden_L0_L2", gold)]
    rng = np.random.default_rng(20261011)
    runs += [(f"stress_{i}", chains_stress(rng, [2 * i, 2 * i + 1])) for i in range(2)]
    for name, chs in runs:
        r = Run(a.ng)
        r.build(chs)
        # golden runs: the chain replay equals every check the 1M case set holds
        checked = 0
        for ch in chs:
            if "attn_checks" not in ch:
                continue
            for b in ("attn", "ffn"):
                nck, pck, h_in_norm, h_in_post = ch[b + "_checks"]
                (_l, _a, bits, _k), = nck
                assert np.array_equal(u32(ch["norm_out"][b]), np.asarray(bits, np.uint32)), (ch["src"], b, "norm")
                (_l, _a, bits, _k), = pck
                assert np.array_equal(u32(ch["h_out"][b]).reshape(-1), np.asarray(bits, np.uint32)), (ch["src"], b, "post")
                checked += 2
            # the chain is the token's own: the ffn norm's h == the attn hc_post output, next layer's h == ffn output
            ch["chain_consistent_attn_to_ffn"] = bool(np.array_equal(u32(ch["h_out"]["attn"]), u32(ch["ffn_checks"][2])))
        meta = dict(run=name, ng=a.ng, jobs=len(r.prog), exp_rows=len(r.exp), y_beats=len(r.y), golden_checks=checked,
                    chains=[dict(src=c["src"], attn_to_ffn_consistent=c.get("chain_consistent_attn_to_ffn")) for c in chs],
                    cases_sha256=sha(a.cases))
        r.write(out / "runs" / name, meta)
        rows.append(meta)
        print(name, meta["jobs"], "jobs", meta["exp_rows"], "rows", "checks", checked, meta["chains"])
    (out / "runs.json").write_text(json.dumps(dict(runs=rows), indent=1) + "\n")
    return 0


# ---------------------------------------------------------------------------------------------------------------- run
HCG = re.compile(r"HCG jobs=(\d+) done=(\d+) err=(\d+) rows=(\d+) fault=(\d+) code=(\d+) cyc=(\d+) bad_tag=(\d+)")
JOB = re.compile(r"HCJ op=(\d+) kind=(\d+) start=(\d+) done=(\d+)")


def build(out: Path, ng, fp, mut, amut, lvm, hier=0, cnl_pin=0, chain_step=4, lane_specialize=0, pad_hard=0, probes=(), tmut=None, tmax=0, pipe=0, pipe_pd=40, ntree=0, nt_k=80, nt_dbg=0):
    # hier: 1 = root split + column chains of octet sub-tiles; 2 = the structural variant (half-octet sub-tiles, split
    # column roots)
    tag = f"ng{ng}_{fp}_m{mut}_a{amut}" + {0: "", 1: "_hier", 2: "_hier2", 3: "_hier3tail"}[hier]
    tag += f"_cp{cnl_pin}_cs{chain_step}_ls{lane_specialize}" + (f"_pipe{pipe_pd}" if pipe else "")
    tag += (f"_nt{nt_k}" if ntree else "") + ("_ntdbg" if nt_dbg else "")
    tag += ("_ph" if pad_hard else "") + ("_probe" if probes else "") + (f"_tm-{tmut}" if tmut else "")
    obj = out / f"build_{tag}"
    exe = obj / "Vtb_s81_hc_master"
    if not exe.exists():
        obj.mkdir(parents=True, exist_ok=True)
        srcs = [ROOT / s for s in FP[fp] + RTL + [TB]]
        if fp == "dpi":
            srcs = dpi_rest(obj) + srcs
        srcs = tile_edit(srcs, obj, probes, tmut)
        cmd = [VERILATOR, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH", "--top-module", "tb_s81_hc_master",
               "-Mdir", str(obj), "-j", "16", "--unroll-count", "4", "-fno-dfg", f"-GNG={ng}", f"-GMUT={mut}",
               *([f"-GPIPE={pipe}", f"-GPIPE_PD={pipe_pd}"] if pipe else []), *([f"-GNTREE=1", f"-GNT_K={nt_k}"] if ntree else []), *(["-GNT_DBG=1"] if nt_dbg else []), f"-GLANE_SPECIALIZE={lane_specialize}", f"-GCNL_PIN={cnl_pin}", f"-GCHAIN_STEP={chain_step}", f"-GAMUT={amut}", f"-GLVM={lvm}", f"-GHIER={min(hier, 1)}", f"-GHALF={int(hier >= 2)}", f"-GCSPLIT={int(hier >= 2)}", f"-GTAIL_SPLIT={2 if hier == 3 else 0}", f"-GHEAD_ROWS={10 if ng == 256 else 2}", *(["+define+OT_S81_HC_PAD_HARD"] if pad_hard else []), *([f"-GTMAX={tmax}"] if tmax else []), *map(str, srcs), "-CFLAGS", "-O1"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        (out / f"build_{tag}.log").write_text(" ".join(cmd) + "\n" + r.stdout + r.stderr)
        if r.returncode != 0:
            sys.exit(f"build failed: {out}/build_{tag}.log")
    return exe, tag


def cmd_run(a):
    out = Path(a.out)
    probes = [x for x in (a.tile_probe or "").split(",") if x]
    probes = list(TILES) if probes == ["all"] else probes
    for x in probes + ([a.tile_mut] if a.tile_mut else []):
        if x not in TILES:
            sys.exit(f"unknown tile {x}: {', '.join(TILES)}")
    exe, tag = build(out, a.ng, a.fp, a.mut, a.amut, a.lvm, a.hier, a.cnl_pin, a.chain_step, a.lane_specialize,
                     a.pad_hard, probes, a.tile_mut, a.tmax, a.pipe, a.pipe_pd, a.ntree, a.nt_k, a.nt_dbg)
    res = []
    tiles = None
    for meta in json.loads((out / "runs.json").read_text())["runs"]:
        d = out / "runs" / meta["run"]
        r = subprocess.run([str(exe)], cwd=d, capture_output=True, text=True)
        if probes and tiles is None:
            tiles = tile_check(r.stdout, probes)
        m = HCG.search(r.stdout)
        jobs = [dict(op=int(x[0]), kind=int(x[1]), start=int(x[2]), done=int(x[3])) for x in JOB.findall(r.stdout)]
        if not m:
            res.append(dict(run=meta["run"], ok=False, tail=(r.stdout + r.stderr)[-3000:]))
            print(meta["run"], "NO RESULT", flush=True)
            continue
        g = list(map(int, m.groups()))
        row = dict(run=meta["run"], jobs=g[0], done=g[1], err_rows=g[2], rows=g[3], fault=g[4], fault_code=g[5],
                   cycles=g[6], bad_tag=g[7], ok=("HCG PASS" in r.stdout), job_cycles=jobs,
                   mismatches=[x for x in r.stdout.splitlines() if "mismatch" in x][:5])
        res.append(row)
        print(meta["run"], "PASS" if row["ok"] else "FAIL", row["err_rows"], "/", row["rows"], "fault", row["fault"],
              "cyc", row["cycles"], flush=True)
    rec = dict(schema="opentallas.s81_suhc.hc_gate.run.v1", generated_utc=datetime.datetime.utcnow().isoformat() + "Z",
               ng=a.ng, fp=a.fp, mut=a.mut, amut=a.amut, lvm=a.lvm, hier=a.hier, cnl_pin=a.cnl_pin, chain_step=a.chain_step, lane_specialize=a.lane_specialize, pipe=a.pipe, pipe_pd=a.pipe_pd, ntree=a.ntree, nt_k=a.nt_k, runs=res,
               status="pass" if res and all(x["ok"] for x in res) and all(t["ok"] for t in (tiles or {}).values()) else "fail",
               pad_hard=a.pad_hard, tile_mut=a.tile_mut, tile_mut_edit=list(TILES[a.tile_mut]["mut"]) if a.tile_mut else None,
               tiles=tiles,
               simulator=subprocess.run([VERILATOR, "--version"], capture_output=True, text=True).stdout.strip(),
               source_sha256={s: sha(ROOT / s) for s in FP[a.fp] + RTL + [TB]})
    (out / f"run_{tag}.json").write_text(json.dumps(rec, indent=1) + "\n")
    for mod, t in (tiles or {}).items():
        print("TILE", mod, "ok" if t["ok"] else "PARAM-MISMATCH", "instances", t["instances"], "routed", t["params_seen"], flush=True)
    print("RUN", tag, rec["status"])
    return 0 if rec["status"] == "pass" else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prep")
    p.add_argument("--cases", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--ng", type=int, default=256)
    p = sp.add_parser("run")
    p.add_argument("--out", required=True)
    p.add_argument("--ng", type=int, default=256)
    p.add_argument("--fp", default="dpi")
    p.add_argument("--mut", type=int, default=0)
    p.add_argument("--amut", type=int, default=0)
    p.add_argument("--lvm", type=int, default=10)
    p.add_argument("--hier", type=int, default=0, help="1: hierarchical slab (root tile + 3 column chains of 1-octet sub-tiles)")
    p.add_argument("--cnl-pin", type=int, default=0)
    p.add_argument("--chain-step", type=int, default=4)
    p.add_argument("--lane-specialize", type=int, default=0)
    p.add_argument("--pipe", type=int, default=0, help="1: ot_s81_hc_cseq PIPE (POST issue-order done; hierarchical slab)")
    p.add_argument("--pipe-pd", type=int, default=40, help="PIPE guard cycles after the last y beat (0 = negative control: must fail)")
    p.add_argument("--ntree", type=int, default=0, help="1: NORM tree variant (hier/ot_s81_hc_ntree.sv, dsfd_sp_hc NTREE 1; --hier 2 / 3)")
    p.add_argument("--nt-k", type=int, default=67, help="NTREE: bottom collectors' fire offset NT_K")
    p.add_argument("--nt-dbg", type=int, default=0, help="NTREE: print the collectors' lane leaves / vector beats (NT_K calibration)")
    p.add_argument("--pad-hard", type=int, default=0, help="1: define OT_S81_HC_PAD_HARD (pad leaves at their hardened defaults)")
    p.add_argument("--tmax", type=int, default=0, help="testbench cycle cap (default: the bench's 400000); a mutant that hangs then fails in minutes")
    p.add_argument("--tile-probe", default="", help="comma list of TILES (or all): report every instance + parameters; the run fails unless all are routed tuples")
    p.add_argument("--tile-mut", default=None, help="one of TILES: build with that module's mutant (the run must fail)")
    a = ap.parse_args()
    return dict(prep=cmd_prep, run=cmd_run)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
