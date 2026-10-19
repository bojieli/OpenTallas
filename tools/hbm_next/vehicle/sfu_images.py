#!/usr/bin/env python3
"""VEH-FMT-COLL2/SFU (10-18): col_sfu_SW row payloads (the SFU half of the FUSED records) for the d4g SW slice (GEN2).

RTL of record (sw2 cut bundle, slice.v):
  col_sfu_SW  ot_hbm_static_cfg_collar #(PAGE_W 3, NS 2, NPR 1, NREC 0, NGO 1, NB 2, NF 1, XSER 0), tgt 116, on hleaf_SW a
  sfup_SW     ot_hgi_sfu_programme_store_r10 #(PAGE_AW 1): space 0 = compiler-control programme (8 stripes x 2048 rows,
              cfg_stripe = pw_addr[13:11]), space 1 = IO programme (3 stripes x 2048 rows, io_cfg_stripe = pw_addr[12:11]);
              prm[10:0]/[22:11]/[38:23] = control base/limit/loops, prm[49:39]/[61:50]/[77:62] = IO base/limit/loops,
              io_start_v = collar start_v (launch); the control programme starts from IO word bit 470 (arithmetic_start,
              IO stripe 2 bit 26, store p_sv_q).
  sfucore_SW  ot_hgi_sfu_core_split3: compiler_control 1742 b (ot_hgi_sfu_arithmetic_grid, 16 ot_su12_sfu lanes, element-
              wise) + io_word 471 b (VM prefetch / scalar / drain through ot_hgi_sfu_vm_static_bridge -> sfr_SW* relays ->
              sfu_SW0..3 tap leaves, granted by calendar_SW lg_local_read/write [9:8]).
Collar ABI (ot_hbm_static_cfg_collar.sv): cfg row ca[11]=0 -> programme row lin = {page[sel] 3, ca[10:0]}; it is accepted
ONLY when lin == hwm[sel] (or lin == 0, which restarts the space); ca = 0xE00 {page 3 @8, space @0} selects; 0xE01 {need[s]
15 b @32s, wait_mask @128}; 0x800 = prm row; launch needs need_set, prm loaded, hwm[s] >= need[s].
FINDING (format): the store's stripe IS the collar page (high address bits), and hwm is strictly sequential, so stripe k of
a space can be written only after stripes 0..k-1 are filled to 2048 rows: an N-row programme costs 7 x 2048 + N control rows
+ 2 x 2048 + L IO rows, ~0.7 M edges at the measured ingress rate (40 edges / row).  The programmes must therefore be
RESIDENT (installed once per model, all FUSED programmes of a layer at distinct bases), and a FUSED record's per-token
SFU payload is the prm row + descriptor + launch only.  A compact install (stripe k at k x 2048 without the padding) faults
the collar (witness tb_sfu_collar mutant 'compact').
Lowering status of the FUSED records (exact golden, hdc_golden_v41 / hgi_sim machine):
  HC_PRE_NORM  to_bf16(seqsum_j pre_j x_j) then RMSNorm (split_sum of squares, rsqrt, gain): needs the cross-element
               reduction + rsqrt (not an elementwise grid op; tools/hbm_static/sfu_vector_calendar refuses reductions) and
               the hc_SW / hc_eng mix -> lowering_open.
  HC_POST      to_bf16(post_k y + seqsum_j comb_jk res_j): elementwise, but the 20 coefficients are run-time VM data (HC_MIX
               output) -> needs the IO scalar path (prefetch_scalar / scalar_addr / scalar_enable) and a multi-pass lowering
               in the golden order; no compiler for io_word rows exists -> lowering_open.
  QDQ_FP8      per-32 block amax -> UE8M0 scale -> FP8 grid -> BF16: block max reduction is not a grid op -> lowering_open.
What IS qualified here: the transport / store format (resident image install, prm, need, select, descriptor, launch) and
the programme-store replay of a compiled programme (tools/hbm_static/sfu_vector_calendar at the HC_POST output shape) on the
real collar + store RTL (tb_sfu_collar.sv): compiler_control and io_word reproduce the image bit-exactly, every edge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hbm_static"))

from sfu_control_image import WIDTH as CTL_W, encode  # noqa: E402
from sfu_program_pages import encode_planes  # noqa: E402
from sfu_vector_calendar import compile_vector  # noqa: E402

SFU_TGT = 116
# measured on the real collar + store (tb_sfu_collar, sw2 masters, Verilator 5.050, results/.../slice_sw/sfu/precheck):
# collar launch pin edge -> first io_word edge 12, io_word -> compiler_control 7 (add hleaf_SW CFG_LAT 2 in the slice)
LAUNCH_TO_IO, IO_TO_CTL = 12, 7
ROWS = 2048                                  # store r10 PAGE_AW 1: rows per stripe
CTL_STRIPES, IO_STRIPES = 8, 3
IO_W = 471
PCLO = 223                                   # stripe word: {c7a1 16, 0 6, pc 11 @223, payload 222}
CHUNK = 222
IO_FIELDS = (('prefetch_v', 8), ('prefetch_scalar', 8), ('prefetch_sector', 128), ('prefetch_group', 16),
             ('prefetch_local_addr', 120), ('prefetch_word', 24), ('scalar_addr', 96), ('scalar_enable', 4),
             ('drain_v', 2), ('drain_addr', 30), ('drain_vm_sector', 32), ('drain_round_bf16', 2),
             ('arithmetic_start', 1))       # LSB first (ot_hgi_sfu_core_split2 io unpack)
assert sum(w for _, w in IO_FIELDS) == IO_W


def pack_io(fields):
    unk = set(fields) - {n for n, _ in IO_FIELDS}
    if unk:
        raise ValueError(f"unknown IO fields {sorted(unk)}")
    v, sh = 0, 0
    for n, w in IO_FIELDS:
        x = fields.get(n, 0)
        if not 0 <= x < 1 << w:
            raise ValueError(f"{n} does not fit {w} b")
        v |= x << sh
        sh += w
    return v


def io_planes(words):
    if not words or len(words) > ROWS:
        raise ValueError("IO programme must fit 2048 rows")
    planes = [[] for _ in range(IO_STRIPES)]
    for pc, w in enumerate(words):
        assert 0 <= w < 1 << IO_W
        for s in range(IO_STRIPES):
            planes[s].append((0xc7a1 << 240) | (pc << PCLO) | ((w >> (CHUNK * s)) & ((1 << CHUNK) - 1)))
    return planes


def ctl_planes(words):
    return encode_planes(words, 1)["planes"]


def prm_row(ctl_base, ctl_n, io_base, io_n, ctl_loops=1, io_loops=1):
    assert 0 <= ctl_base and ctl_base + ctl_n <= ROWS and 0 <= io_base and io_base + io_n <= ROWS
    return (ctl_base | (ctl_base + ctl_n) << 11 | ctl_loops << 23 |
            io_base << 39 | (io_base + io_n) << 50 | io_loops << 62)


def collar_install(ctl, io, compact=False):
    """resident image install frames [(cfg_addr, data)] in collar order.  ctl / io: stripe planes (rows each).
    compact=True omits the stripe padding (mutant: the collar must fault)."""
    fr = []
    need = []
    for space, planes in ((0, ctl), (1, io)):
        n = len(planes[0])
        for s, rows in enumerate(planes):
            fr.append((0xE00, (s << 8) | space))
            pad = [] if (compact or s == len(planes) - 1) else [0] * (ROWS - n)
            for j, w in enumerate(rows + pad):
                fr.append((j, w))
        need.append((len(planes) - 1) * ROWS + n)
    fr.append((0xE01, need[0] | need[1] << 32))
    return fr, need


def fused_lowering_table(fdirs):
    """per FUSED record of the fixtures: the SFU payload status with exact reasons."""
    why = {"HC_PRE_NORM": ["mix seqsum + RMSNorm reduction (split_sum x^2, rsqrt) is not an elementwise grid op",
                           "hc_SW / hc_eng half: sibling VEH-FMT-COLL2/HC",
                           "no io_word (prefetch/scalar/drain) compiler exists"],
           "HC_POST": ["20 coefficients are run-time VM data: needs the IO scalar path, no io_word compiler exists",
                       "multi-pass lowering in the golden order (seqsum_j comb_jk res_j, + post_k y, BF16) not written"],
           "QDQ_FP8": ["per-32 block amax (UE8M0 scale) is a reduction, not an elementwise grid op",
                       "no io_word compiler exists"]}
    out = []
    for fd in fdirs:
        r = json.loads((Path(fd) / "records.json").read_text())
        for _, recs in sorted(r["records"].items()):
            for x in recs:
                if not x["op"].startswith("FUSED."):
                    continue
                op = x["op"].split(".", 1)[1]
                out.append(dict(layer=x["layer"], k=x["k"], op=x["op"], tag=x["tag"],
                                priced=[dict(i=p["i"], start=p["start"], end=p["end"]) for p in x["priced"]],
                                cp_targets=[dict(instance="col_sfu_SW", tgt=SFU_TGT), dict(instance="hc_SW", tgt=108)],
                                status="lowering_open", reasons=why.get(op, ["unknown FUSED op"]),
                                per_token_sfu_payload="prm row 0x800 + desc + launch (programme resident)"))
    return out


def tb_events(frames, t0=8, gap=1, prm=None, launch=True):
    """tb_sfu_collar.sv event file: '<cyc> <kind> <addr> <data>' kind 1 cfg, 2 desc, 3 launch (hex fields)."""
    lines, c = [], t0
    for a, d in frames + ([(0x800, prm)] if prm is not None else []):
        lines.append(f"{c:x} 1 {a:x} {d:x}")
        c += gap
    lines.append(f"{c:x} 2 0 0")
    c += 4
    if launch:
        lines.append(f"{c:x} 3 0 0")
    return lines, c


def hex_rows(words, width):
    return "".join(f"{w:0{-(-width // 4)}x}\n" for w in words)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", nargs="*", default=[])
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--pre", type=Path, help="write tb_sfu_collar inputs (positive + mutants) here")
    a = ap.parse_args()
    # format vehicle programme: elementwise vector at the HC_POST output shape (20480 FP32), compiled by the existing
    # sfu_vector_calendar (immediates 1.0: a FORMAT check, not the record's arithmetic)
    prog = compile_vector(words=20480, bases=(0, 20480, 40960, 61440, 81920), m1=3, ad=3)
    ctl = encode(prog)
    io = [pack_io(dict(arithmetic_start=1))] + [0] * 3
    cp, ip = ctl_planes(ctl), io_planes(io)
    frames, need = collar_install(cp, ip)
    prm = prm_row(0, len(ctl), 0, len(io))
    man = dict(schema="opentallas.hbm_sfu_images.v1", target=dict(instance="col_sfu_SW", tgt=SFU_TGT),
               format_vehicle=dict(ctl_rows=len(ctl), io_rows=len(io), need=need, install_frames=len(frames),
                                   install_edges_at_ingress=len(frames) * 40 + 5 * 3,
                                   ctl_sha256=hashlib.sha256(hex_rows(ctl, CTL_W).encode()).hexdigest()),
               measured=dict(launch_to_io_edges=LAUNCH_TO_IO, io_to_ctl_edges=IO_TO_CTL, bench="tb_sfu_collar.sv"),
               records=fused_lowering_table(a.fixtures))
    if a.pre:
        a.pre.mkdir(parents=True, exist_ok=True)
        (a.pre / "ctl.hex").write_text(hex_rows(ctl, CTL_W))
        (a.pre / "io.hex").write_text(hex_rows(io, IO_W))
        (a.pre / "len.txt").write_text(f"{len(ctl)} {len(io)}\n")
        for name, fr, pr in (("pos", frames, prm), ("mut_compact", collar_install(cp, ip, compact=True)[0], prm)):
            ln, _ = tb_events(fr, prm=pr)
            (a.pre / f"{name}.events.txt").write_text("\n".join(ln) + "\n")
        # mutant: one control payload bit flipped in stripe 3 row 100 (word_ok holds; the image must mismatch)
        cp2 = [list(p) for p in cp]
        cp2[3][100] ^= 1 << 17
        ln, _ = tb_events(collar_install(cp2, ip)[0], prm=prm)
        (a.pre / "mut_bit.events.txt").write_text("\n".join(ln) + "\n")
    if a.manifest:
        a.manifest.parent.mkdir(parents=True, exist_ok=True)
        a.manifest.write_text(json.dumps(man, indent=1) + "\n")
    print(json.dumps(dict(man["format_vehicle"], records=len(man["records"]))))


if __name__ == "__main__":
    main()
