#!/usr/bin/env python3
"""HGI-1 program listing: decode a program image into a human-readable listing with every encoded field.

Per record: index, byte offset, tag (trace only, not encoded), unit.op, wait mask (unit names), predicate, slot, param
(raw and decoded per unit.op, spec 6.7), imm_a / imm_b (hex, U32 and FP32 readings), the SU template (SUT) fields when
present, and per operand slot (A, B, C, D, O, R, I) every MDESC field (space, fmt, base, n, m, stride, istride,
lstride, l1stride, dyn_sel / dyn_mul, n_sel, ibcast, indexed), plus the record's raw hex split at the 16 B header,
the 32 B template and each 32 B descriptor.  Optionally the effective operands of a simulator trace.

Field positions come from records.py (hence from tools/hbm_generic_iface.py's D_* tables), so the listing follows the
spec.  `records_from_listing` rebuilds the records from the machine-readable listing; `check_roundtrip` proves that
image -> listing -> records -> encode_program reproduces the image byte for byte.

    python3 -m hgi_sim.listing --qwen [--dflash B] [--ds-program PROG.json] [--ds-per-die FILE --rank R]
                               --out-dir DIR            (from tools/)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import hbm_generic_iface as HGI  # noqa: E402
import hdc_isa_v41 as I  # noqa: E402

from hgi_sim.records import OPND, MDesc, Rec, decode_one, encode_program, rec_bytes  # noqa: E402

UNITS = HGI.D_UNITS
DYN_NAMES = list(HGI.D_DYN) + [
    (f"DS:{k}" if isinstance(k, str) else f"DS:{k[0]}({k[1]}/{k[2]})") for k in I.FULL_DYN]
DYN_NAMES += [f"DS_FULL_DYN[{i}]" for i in range(len(DYN_NAMES) - 16, 47)] + ["N_FROM_VM"]
assert len(DYN_NAMES) == 64

# SUT enum readings (hdc_isa_v41 constant prefixes)
_ENUM_PREFIX = dict(a_src="SRC", b_src="SRC", c_src="SRC", d_src="SRC", a_ind="IND", m1="M1", m2="M2", qm="QM",
                    ad="AD", sfu="SFU", e1="E1", e2="E2", dst="DST", red="RED", su_vec="VEC")
_ENUMS = {}
for f, p in _ENUM_PREFIX.items():
    _ENUMS[f] = {v: k[len(p) + 1:] for k, v in vars(I).items() if k.startswith(p + "_") and isinstance(v, int)
                 and k.isupper() and not k.startswith(p + "_LANES")}


def f32(u):
    return struct.unpack("<f", struct.pack("<I", u & 0xFFFFFFFF))[0]


def imm_text(u):
    u &= 0xFFFFFFFF
    if u == 0:
        return "0"
    f = f32(u)
    s = f"0x{u:08x} (u32 {u}"
    if u < (1 << 24):
        return s + ")"
    return s + f", f32 {f:.9g})"


def wait_units(w):
    return [UNITS[b] for b in range(16) if w >> b & 1]


def param_fields(r: Rec):
    """param decoded per unit.op (spec 6.7); {} when the op defines no param fields"""
    p, u, op = r.param, r.unit, r.op
    if u == "CTL" and op == "LOOP":
        return dict(count=p & 0xFFFF, level=(p >> 16) & 1)
    if u == "SM" and op == "MATVEC":
        return dict(format=["BF16", "FP8 block-dot", "FP4 block-dot", "INT8"][p & 3], positions=((p >> 2) & 7) + 1)
    if u == "FUSED" and op == "ROW_NORM":
        return dict(d_units=p & 0x3F, seg=(p >> 6) & 0xFF)
    if u == "FUSED" and op == "SOFTMAX":
        return dict(multipass=p & 1)
    if u == "FUSED" and op == "QDQ_FP4_E4M3":
        return dict(block=p & 0xFF)
    if u == "ATT":
        lanes = p & 0xF
        return dict(head_lanes=lanes or 16, slices_64=((p >> 4) & 0xF) + 1, ring=(p >> 8) & 1)
    if u == "COLL" and op in ("GROUP_REDUCE_MCAST",):
        return dict(subgroup=p & 0xFF)
    if u == "COLL" and op == "ROW_GATHER":
        return dict(owner_block=p & 0xFF)
    if u == "IDX" and op == "OWNED":
        return dict(owner_block=p & 0xFF, group=(p >> 8) & 0xFF)
    if u == "IDX" and op == "MERGE":
        return dict(k=p & 0xFFF, key=(p >> 12) & 1)
    if u == "IDX" and op == "INDEX":
        return dict(k=p & 0xFFF, cand_en=(p >> 12) & 1, keep_en=(p >> 13) & 1)
    if u == "IDX" and op == "TOPK":
        return dict(k=p & 0xFFF, order=["descending score", "ascending id"][(p >> 12) & 1])
    if u == "IDX" and op == "EHASH":
        return dict(engram_layer=p & 7)
    if u == "SIMT":
        return dict(entry_pc=p & 0x3FFF)
    return {}


def sut_text(t: dict):
    out = []
    for name, _, width in HGI.D_SUT_LAYOUT:
        v = t.get(name, 0)
        if name.startswith("imm"):
            out.append(f"{name}={imm_text(v)}")
        elif name in _ENUMS and v in _ENUMS[name]:
            out.append(f"{name}={_ENUMS[name][v]}")
        else:
            out.append(f"{name}={v}")
    return out


def desc_dict(d: MDesc):
    return dict(space=d.space, fmt=d.fmt, base=d.base, n=d.n, m=d.m, stride=d.stride, istride=d.istride,
                lstride=d.lstride, l1stride=d.l1stride, dyn_sel=d.dyn_sel, dyn_mul=d.dyn_mul, n_sel=d.n_sel,
                ibcast=d.ibcast, indexed=d.indexed)


def record_entry(k, off, r: Rec, raw: bytes, tag=None, trace=None):
    """the machine-readable listing row of one record (every encoded field + raw hex)"""
    parts = [raw[:16].hex()]
    p = 16
    if r.sut is not None:
        parts.append(raw[p:p + 32].hex())
        p += 32
    for _ in r.descs_in_order():
        parts.append(raw[p:p + 32].hex())
        p += 32
    e = dict(index=k, offset=off, bytes=len(raw), tag=tag if tag is not None else r.tag, unit=r.unit, op=r.op,
             wait=r.wait, wait_units=wait_units(r.wait), pred=r.pred, slot=r.slot, param=r.param,
             param_fields=param_fields(r), imm_a=r.imm_a & 0xFFFFFFFF, imm_b=r.imm_b & 0xFFFFFFFF,
             sut=dict(r.sut) if r.sut is not None else None,
             opnd={k_: desc_dict(d) for k_, d in r.descs_in_order()}, hex=parts)
    if trace is not None:
        e["effective"] = trace
    return e


def listing(image: bytes, tags=None, traces=None):
    """image -> [record entry]; tags[k] names record k (trace only); traces: {k: effective operands}"""
    out, off, k = [], 0, 0
    while off < len(image):
        r, nxt = decode_one(image, off)
        out.append(record_entry(k, off, r, image[off:nxt], tag=(tags[k] if tags and k < len(tags) else ""),
                                trace=(traces or {}).get(k)))
        off, k = nxt, k + 1
    return out


def records_from_listing(entries):
    recs = []
    for e in entries:
        r = Rec(unit=e["unit"], op=e["op"], wait=e["wait"], pred=e["pred"], slot=e["slot"], param=e["param"],
                imm_a=e["imm_a"], imm_b=e["imm_b"], sut=dict(e["sut"]) if e["sut"] is not None else None,
                tag=e.get("tag", ""))
        for s in OPND:
            if s in e["opnd"]:
                r.desc[s] = MDesc(**e["opnd"][s])
        recs.append(r)
    return recs


def check_roundtrip(image: bytes, entries):
    """image -> listing -> records -> encode_program == image, byte for byte; and each entry's hex is its slice"""
    again = encode_program(records_from_listing(entries))
    assert again == image, "listing does not round-trip"
    for e in entries:
        assert "".join(e["hex"]) == image[e["offset"]:e["offset"] + e["bytes"]].hex()
    return True


# ------------------------------------------------------------------------------------------------ text rendering
def _base(d):
    return f"0x{d['base']:x}" if d["space"] == "HBM" else str(d["base"])


def dyn_name(c):
    return DYN_NAMES[c] if 0 <= c < 64 else str(c)


COLS = ("slot", "space", "fmt", "base", "n", "m", "stride", "istride", "lstride", "l1stride", "dyn_sel*dyn_mul",
        "n_sel", "ibcast", "indexed")


def text(entries, title=None, indent=""):
    """fixed-width listing; every field of every record"""
    L = []
    if title:
        L.append(indent + title)
    for e in entries:
        pf = e["param_fields"]
        pft = (" {" + ", ".join(f"{k}={v}" for k, v in pf.items()) + "}") if pf else ""
        L.append(indent + f"[{e['index']:04d}] @{e['offset']:#07x} {e['unit']}.{e['op']}  tag={e['tag'] or '-'}")
        L.append(indent + f"       wait={e['wait']:#06x} {{{','.join(e['wait_units']) or '-'}}}  pred={e['pred']}  "
                 f"slot={e['slot']}  param={e['param']:#x}{pft}  imm_a={imm_text(e['imm_a'])}  "
                 f"imm_b={imm_text(e['imm_b'])}")
        if e["sut"] is not None:
            f = sut_text(e["sut"])
            L.append(indent + "       SUT  " + " ".join(f[:15]))
            L.append(indent + "            " + " ".join(f[15:26]))
            L.append(indent + "            " + " ".join(f[26:]))
        if e["opnd"]:
            rows = [COLS]
            for s, d in e["opnd"].items():
                rows.append((s, d["space"], d["fmt"], _base(d), str(d["n"]), str(d["m"]), str(d["stride"]),
                             str(d["istride"]), str(d["lstride"]), str(d["l1stride"]),
                             f"{dyn_name(d['dyn_sel'])}*{d['dyn_mul']}", dyn_name(d["n_sel"]) if d["n_sel"] else "0",
                             str(d["ibcast"]), str(d["indexed"])))
            w = [max(len(r_[i]) for r_ in rows) for i in range(len(COLS))]
            for r_ in rows:
                L.append(indent + "       " + "  ".join(c.rjust(w[i]) if i >= 3 and c[:1].isdigit() or c[:1] == "-"
                                                        else c.ljust(w[i]) for i, c in enumerate(r_)).rstrip())
        if e.get("effective"):
            eff = "  ".join(f"{s}=[{v[5]} {v[6]} base {v[0]:#x} n {v[1]} m {v[2]} stride {v[3]}]"
                            for s, v in e["effective"].items())
            L.append(indent + "       effective: " + eff)
        hx = e["hex"]
        L.append(indent + "       hex  UOP " + hx[0] + (" SUT " + hx[1] if e["sut"] is not None else ""))
        rest = hx[2:] if e["sut"] is not None else hx[1:]
        for s, h in zip(e["opnd"], rest):
            L.append(indent + f"            {s:<3} " + h)
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ program sources
QCFG = ROOT / "compiler/models/qwen3-8b/config.json"
DCFG = ROOT / "compiler/models/qwen3-8b-dflash-b16/config.json"


def qwen_program():
    from hgi_sim import qwen_compiler as QC
    cfg = json.loads(QCFG.read_text())
    recs = QC.program(QC.Geometry(cfg, 8192), QC.qwen_params(cfg), cfg["num_hidden_layers"])
    return recs, dict(model="Qwen3-8B", tp=4, context=8192, layers=cfg["num_hidden_layers"],
                      compiler="tools/hgi_sim/qwen_compiler.py program(Geometry(cfg, 8192), qwen_params(cfg), 36)")


def dflash_program(B=16):
    from hgi_sim import dflash as DF
    from hgi_sim import dflash_timing as DFT
    from hgi_sim import qwen_compiler as QC
    cfg = json.loads(QCFG.read_text())
    dcfg = json.loads(DFT.DCFG.read_text())
    g = DF.DGeom(cfg, dcfg, 8192, B)
    recs = DF.step_program(g, QC.qwen_params(cfg), timing_pos=8192 - B)
    return recs, dict(model="Qwen3-8B + z-lab/Qwen3-8B-DFlash-b16", tp=4, context=8192, block=B,
                      compiler=f"tools/hgi_sim/dflash.py step_program(DGeom(cfg, dcfg, 8192, {B}), timing_pos={8192 - B})")


def ds_program(path):
    """rank-0 full-token record stream (hgi_sim.ds_native --program-out)"""
    d = json.loads(Path(path).read_text())
    recs, layer_of = [], []
    for lay in d["layers"]:
        for x in lay["records"]:
            r, _ = decode_one(bytes.fromhex(x["hex"]), 0)
            r.tag, r.family = x["tag"], x["family"]
            r.reads, r.writes = x["reads"], x["writes"]
            r.src_key = None if not x["src"] else f"{x['src'][0]}:{x['src'][1]}"
            r.src_extra = [f"{x['src'][0]}:{e}" for e in x["src"][2]] if x["src"] and len(x["src"]) > 2 else []
            r.layer = lay["layer"]
            recs.append(r)
            layer_of.append(lay["layer"])
    return d, recs


def ds_per_die(path, rank):
    d = json.loads(Path(path).read_text())
    rk = next(x for x in d["ranks"] if x["rank"] == rank)
    image = bytes.fromhex(rk["image_hex"])
    assert hashlib.sha256(image).hexdigest() == rk["image_sha256"]
    traces = {t[0]: t[2] for t in rk["trace"]}
    return d, rk, image, traces


def write_listing(out_dir: Path, name, image, entries, meta):
    out_dir.mkdir(parents=True, exist_ok=True)
    check_roundtrip(image, entries)
    meta = dict(meta, schema="opentallas.hgi_program_listing.v1", records=len(entries), image_bytes=len(image),
                image_sha256=hashlib.sha256(image).hexdigest(), roundtrip="image -> listing -> records -> "
                "encode_program == image (byte for byte)", tool="tools/hgi_sim/listing.py",
                spec=f"HGI-1 {HGI.D_VERSION[0]}.{HGI.D_VERSION[1]}")
    (out_dir / f"{name}.json").write_text(json.dumps(dict(meta, records_listing=entries), indent=None,
                                                     separators=(",", ":")) + "\n")
    (out_dir / f"{name}.txt").write_text(f"# {name}: {json.dumps({k: v for k, v in meta.items()})}\n\n"
                                         + text(entries) + "\n")
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--qwen", action="store_true")
    ap.add_argument("--dflash", type=int, default=0, help="block size of the DFlash step to list (0 = none)")
    ap.add_argument("--ds-program", type=Path, help="rank-0 full-token program (ds_native --program-out)")
    ap.add_argument("--ds-per-die", type=Path, nargs="*", default=[], help="ds_v41_1M_L??_per_die.json exports")
    ap.add_argument("--ranks", default="0", help="ranks of the per-die exports to list (comma list or 'all')")
    a = ap.parse_args()
    if a.qwen:
        recs, meta = qwen_program()
        img = encode_program(recs)
        m = write_listing(a.out_dir, "qwen3_8b_tp4_token_P8191", img, listing(img, [r.tag for r in recs]), meta)
        print("qwen", m["records"], m["image_bytes"], m["image_sha256"][:16])
    if a.dflash:
        recs, meta = dflash_program(a.dflash)
        img = encode_program(recs)
        m = write_listing(a.out_dir, f"qwen3_8b_dflash_b{a.dflash}_step", img, listing(img, [r.tag for r in recs]), meta)
        print("dflash", m["records"], m["image_bytes"], m["image_sha256"][:16])
    if a.ds_program:
        d, recs = ds_program(a.ds_program)
        img = encode_program(recs)
        ents = listing(img, [r.tag for r in recs])
        for e, r in zip(ents, recs):
            e["layer"] = r.layer
            e["family"] = r.family
        m = write_listing(a.out_dir, "ds_v41_tp96_rank0_token_1M", img, ents, dict(
            model="DeepSeek-V4.1-Flash", tp=96, rank=d["rank"], position=1048575,
            source=str(a.ds_program.name), source_sha256=hashlib.sha256(a.ds_program.read_bytes()).hexdigest(),
            compiler="tools/hgi_sim/ds_native.py --program-out (rank 0, a head die)"))
        print("ds", m["records"], m["image_bytes"], m["image_sha256"][:16])
    for p in a.ds_per_die:
        dd = json.loads(p.read_text())
        ranks = [x["rank"] for x in dd["ranks"]] if a.ranks == "all" else [int(x) for x in a.ranks.split(",")]
        for rk in ranks:
            d, r_, img, tr = ds_per_die(p, rk)
            ents = listing(img, d["record_tags"], tr)
            m = write_listing(a.out_dir, f"ds_v41_tp96_L{d['layer']:02d}_rank{rk:02d}", img, ents, dict(
                model=d["model"], tp=d["tp"], layer=d["layer"], rank=rk, position=d["position"], dyn=r_["dyn"],
                token_in=d["token_in"], source=str(p.relative_to(ROOT)) if p.is_absolute() else str(p),
                note=d["note"]))
            print("ds per-die", d["layer"], rk, m["records"], m["image_bytes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
