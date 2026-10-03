#!/usr/bin/env python3
"""Lever item 1: SAME-X PHASE MERGE (default-off emitter option + matching die images, no new RTL).

The exact-TP V4.1 emitter (tools/hdc_replay_v41.py ShapeBuilder: project_gate_up :781-793, attention :641-642)
issues w1 then w3 of every expert and wq_a then wkv as TWO QE LINQ ops = two ROM-field phases each, although
both ops of a pair read the same x and the field runs a multi-matrix phase natively (one x load, one stream;
ot_v41_spine header).  This tool is a wrapper around the unchanged emitter and image tools:

  merge_program(fields, merge)      the emitter option: OFF returns the program unchanged; ON replaces each
                                    adjacent same-x LINQ pair (same xbase/nb/fp4/ind/ibase/unrounded/pred, the
                                    second's output directly after the first's) by ONE op: the first op's key
                                    (weight base; the adapter's phase CAM key), nout = n1 + n2, tiles re-derived,
                                    union of its read/write sets.  The ROM-field adapter (rtl/v41die/
                                    ot_v41_rom_adapt.sv) takes rows from the phase ROM, so the merged phase's
                                    rows land at obase + row tag, i.e. exactly where the two split ops wrote.
  emit_layer(layer, merge)          the bound emitter path (R.build_tp_layer) with the option.

Subcommands
  program  --prog IN.hex --out OUT.hex [--merge]     encoded 2048-bit program (FULL profile) in/out
  emitter  --layer L                                 option off == original emitter; pairs found at ON
  images   --src IMGROOT --out OUTROOT --snapshot S [--merge] [--ranks 0,1,2,3]
           die image set: prog.hex merged, weights.json merged (a merged entry carries "mats"), field images
           regenerated with the same field tool/params as the source set (tools/v41_die_images_w17w10
           add_phase with both matrices in one phase), spine_keys; every other file hard-linked unchanged.
           OFF regenerates the field and must reproduce the source set's field files byte for byte.
  ab       --off RUN --on RUN --src IMGROOT --merged OUTROOT --out RECORD.json
           read two runtime-die runs (tools/w17 fastpp v41_die_rt host: progress.log, run.log, vm<d>.hex)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_isa_v41 as I  # noqa: E402

PAIR_KEYS = ("qe_xbase", "qe_nb", "qe_fp4", "qe_ind", "qe_ibase", "qe_unrounded", "pred", "qe_mode",
             "qe_d_obase", "qe_istride")


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cdiv(a, b):
    return -(-a // b)


def _g(f, k):
    return f.get(k, 0)


def mergeable(f1: dict, f2: dict) -> bool:
    if _g(f1, "unit") != I.UNIT_QE or _g(f2, "unit") != I.UNIT_QE:
        return False
    if _g(f1, "qe_mode") != I.QE_LINQ or _g(f2, "qe_mode") != I.QE_LINQ:
        return False
    if any(_g(f1, k) != _g(f2, k) for k in PAIR_KEYS if k != "qe_istride"):
        return False
    if _g(f1, "qe_ind") and _g(f1, "qe_istride") != _g(f2, "qe_istride"):
        return False
    # the second op may not wait on anything the first did not (its own unit is QE: no QE drain needed)
    if _g(f2, "wait") & ~_g(f1, "wait") & ~(1 << (I.UNIT_QE - 1)):
        return False
    # second output directly after the first: one contiguous row block at obase + row tag
    if _g(f2, "qe_obase") != _g(f1, "qe_obase") + _g(f1, "qe_nout"):
        return False
    # the first op must not overwrite the shared x
    x0, x1 = _g(f1, "qe_xbase"), _g(f1, "qe_xbase") + 32 * _g(f1, "qe_nb")
    o0, o1 = _g(f1, "qe_obase"), _g(f1, "qe_obase") + _g(f1, "qe_nout")
    return o1 <= x0 or x1 <= o0


def merge_program(prog: list[dict], merge: bool) -> tuple[list[dict], list[dict]]:
    """The emitter option.  Returns (program, merges); merges: [{pc_first, pc_second, new_pc, rows: [n1, n2]}]."""
    if not merge:
        return list(prog), []
    out, merges, pc = [], [], 0
    while pc < len(prog):
        f1 = prog[pc]
        if pc + 1 < len(prog) and mergeable(f1, prog[pc + 1]):
            f2 = prog[pc + 1]
            m = dict(f1)
            n = _g(f1, "qe_nout") + _g(f2, "qe_nout")
            m["qe_nout"] = n
            m["qe_tiles"] = cdiv(n, I.BL * I.INTERLEAVE)
            if "_reads" in f1 or "_reads" in f2:
                m["_reads"] = set(f1.get("_reads", ())) | set(f2.get("_reads", ()))
                m["_writes"] = set(f1.get("_writes", ())) | set(f2.get("_writes", ()))
            if "_macs" in f1:
                m["_macs"] = f1["_macs"] + f2.get("_macs", 0)
            m["_merged"] = (pc, pc + 1)
            merges.append(dict(pc_first=pc, pc_second=pc + 1, new_pc=len(out), rows=[_g(f1, "qe_nout"), _g(f2, "qe_nout")],
                               wbase=[_g(f1, "qe_wbase"), _g(f2, "qe_wbase")], tag=f1.get("_tag")))
            out.append(m)
            pc += 2
        else:
            out.append(f1)
            pc += 1
    return out, merges


def emit_layer(layer: int, merge: bool):
    import hdc_replay_v41 as R
    prog = R.build_tp_layer(layer)
    return merge_program(prog, merge)


# -- encoded programs ----------------------------------------------------------------------------------------------
def read_prog(p: Path) -> tuple[list[dict], int]:
    lines = p.read_text().split()
    return [I.decode(int(w, 16), full_shape=True) for w in lines], len(lines[0])


def write_prog(prog: list[dict], p: Path, ndig: int):
    words = []
    for f in prog:
        w = I.encode(full_shape=True, **{k: v for k, v in f.items() if not k.startswith("_")})
        d = I.decode(w, full_shape=True)
        assert all(d[k] == v for k, v in f.items() if not k.startswith("_")), "field does not encode"
        words.append(f"{w:0{ndig}x}\n")
    p.write_text("".join(words))


def cmd_program(a):
    prog, nd = read_prog(a.prog)
    out, merges = merge_program(prog, a.merge)
    write_prog(out, a.out, nd)
    same = a.out.read_bytes() == a.prog.read_bytes()
    print(json.dumps(dict(ops_in=len(prog), ops_out=len(out), merges=merges, byte_identical=same), indent=1))
    return 0


def cmd_emitter(a):
    import hdc_replay_v41 as R
    rec = {}
    for L in a.layer:
        orig = R.build_tp_layer(L)
        off, _ = emit_layer(L, False)
        on, merges = emit_layer(L, True)
        strip = lambda p: [{k: v for k, v in f.items() if not k.startswith("_")} for f in p]  # noqa: E731
        rec[L] = dict(ops=len(orig), off_identical=strip(off) == strip(orig), ops_merged=len(on),
                      merges=[dict(m, tag=m["tag"]) for m in merges])
    print(json.dumps(rec, indent=1, default=str))
    if a.out:
        a.out.write_text(json.dumps(rec, indent=1, default=str) + "\n")
    return 0


# -- die images ----------------------------------------------------------------------------------------------------
FIELD_FILES = ("field.txt", "spine_phase.hex", "spine_stream.hex", "spine_keys.hex")


def merge_weights(ops: list[dict], merges: list[dict]) -> list[dict]:
    by_pc = {o["pc"]: o for o in ops}
    drop, out = set(), []
    first = {m["pc_first"]: m for m in merges}
    newpc = {}
    for m in merges:
        newpc[m["pc_first"]] = m["new_pc"]
    for o in ops:
        if o["pc"] in drop:
            continue
        if o["pc"] in first:
            m = first[o["pc"]]
            o2 = by_pc[m["pc_second"]]
            assert o["kind"] == o2["kind"] == "qe" and o["fmt"] == o2["fmt"] and o["cols"] == o2["cols"] \
                and o["out"] == o2["out"], ("weights.json pair mismatch", o, o2)
            assert o["rows"][1] - o["rows"][0] == m["rows"][0] and o2["rows"][1] - o2["rows"][0] == m["rows"][1]
            e = dict(o, mats=[{k: o[k] for k in ("tensor", "fmt", "rows", "cols")},
                              {k: o2[k] for k in ("tensor", "fmt", "rows", "cols")}],
                     merged_pcs=[o["pc"], o2["pc"]], merged_keys=[o["key"], o2["key"]])
            drop.add(o2["pc"])
            out.append(e)
        else:
            out.append(dict(o))
    return out


def build_field(ops, out: Path, snapshot: Path, params: dict):
    """tools/w17_current_fastpp_die_field.py main (source 4e38326d6), with one phase per entry: an entry with
    "mats" places every matrix in ONE phase."""
    import numpy as np  # noqa: F401
    import v41_die_images_w17w10 as F
    from rtl_v41_rom_array import Ckpt, Mat

    def mat(ck, name, fmt, rows, K, r0, k0):
        dt = ck.raw(name + ".weight")[0]
        if fmt == "bf16" and dt == "F8_E4M3":
            import numpy as np
            q = Mat(ck, name, "fp8", rows, K, r0=r0, k0=k0)
            v = np.ldexp(q.w.q, np.repeat(q.w.e, 32, axis=1)).astype(np.float32)
            b = v.view(np.uint32)
            assert np.all((b & 0xFFFF) == 0)
            m = Mat.__new__(Mat)
            m.name, m.fmt, m.rows, m.K, m.r0, m.k0, m.phase = name, "bf16", rows, K, r0, k0, "wo_a"
            m.u16 = (b >> 16).astype(np.uint16)
            m.wf = v
            return m
        return Mat(ck, name, fmt, rows, K, r0=r0, k0=k0)

    t0 = time.time()
    ck = Ckpt(snapshot)
    fld = F.Field(params["np"], params["regions"], params["nbf"], depth=params["depth"], active=params["active"],
                  fast=bool(params["FAST"]), pp=bool(params["PP"]))
    keys = []
    for op in ops:
        ms = []
        for mm in op.get("mats", [op]):
            (r0, r1), (c0, c1) = mm["rows"], mm["cols"]
            name = mm["tensor"][:-len(".weight")] if mm["tensor"].endswith(".weight") else mm["tensor"]
            ms.append(mat(ck, name, mm["fmt"], r1 - r0, c1 - c0, r0, c0))
        fp32 = op["out"] == "fp32"
        ph = F.add_phase(fld, ms, (fp32, fp32), 0)
        ph.update(pc=op["pc"], kind=op["kind"], key=op["key"])
        keys.append((1 << 31) | ((1 if op["kind"] == "me" else 0) << 30) | (int(op["key"]) & ((1 << 30) - 1)))
        print(f"phase {ph['index']} pc {op['pc']} {[m.name for m in ms]} rows {ph['nrows']} beats {ph['nbeat']} "
              f"t_phase {ph['t_phase_model']}", flush=True)
    assert len(fld.phases) <= (1 << params["phw"]) and len(set(keys)) == len(keys)
    F.write_field(fld, out, params["phw"], flat_viamaps=False)
    (out / "spine_keys.hex").write_text("".join(f"{k:08x}\n" for k in keys + [0] * ((1 << params["phw"]) - len(keys))))
    rec = dict(schema="opentallas.rtl.w17_die_field_images.v1", weights=str(out / "weights.json"),
               weights_sha256=sha(out / "weights.json"), params=params, rom_fill_max_words=int(fld.fill.max()),
               stream_words=len(fld.stream), phases=fld.phases, checkpoint_header_sha256=ck.pins,
               source_sha256={str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / "tools/v41_die_images_w17w10.py",
                                                                         ROOT / "tools/v41_rom_ksplit_bankmap.py",
                                                                         ROOT / "tools/rtl_v41_rom_array.py")},
               wall_s=round(time.time() - t0, 1), lever="dsrom_lever_phase_merge")
    (out / "field_phases.json").write_text(json.dumps(rec, indent=1, default=int) + "\n")
    return rec


def cmd_images(a):
    report = {}
    for r in a.ranks:
        src, dst = a.src / f"r{r}", a.out / f"r{r}"
        dst.mkdir(parents=True, exist_ok=True)
        prog, nd = read_prog(src / "prog.hex")
        newp, merges = merge_program(prog, a.merge)
        ops = json.loads((src / "weights.json").read_text())
        wops = merge_weights(ops, merges)
        params = json.loads((src / "field_phases.json").read_text())["params"]
        for p in src.iterdir():
            if p.name in FIELD_FILES + ("prog.hex", "weights.json", "field_phases.json") or \
                    re.fullmatch(r"e\d+b?\.(words|cfg)\.hex", p.name):
                continue
            q = dst / p.name
            if not q.exists():
                os.link(p, q)
        write_prog(newp, dst / "prog.hex", nd)
        (dst / "weights.json").write_text(json.dumps(wops, indent=1) + "\n")
        rec = build_field(wops, dst, a.snapshot, params)
        ident = {}
        if not a.merge:
            names = sorted(set(FIELD_FILES) | {p.name for p in src.glob("e*.hex")})
            ident = {n: (dst / n).exists() and sha(dst / n) == sha(src / n) for n in names}
            for n in ("prog.hex", "weights.json"):
                ident[n] = sha(dst / n) == sha(src / n)
        report[r] = dict(ops=len(prog), ops_out=len(newp), phases=len(rec["phases"]), merges=merges,
                         field_files_identical_to_source=(all(ident.values()) if ident else None),
                         nonidentical=[k for k, v in ident.items() if not v][:20],
                         phase_model=[dict(pc=p["pc"], key=p["key"], nrows=p["nrows"], nbeat=p["nbeat"],
                                           t_phase_model=p["t_phase_model"]) for p in rec["phases"]])
        print(f"rank {r}: {len(prog)} -> {len(newp)} ops, {len(rec['phases'])} phases, identical={report[r]['field_files_identical_to_source']}",
              flush=True)
    (a.out / "lever_images.json").write_text(json.dumps(dict(merge=a.merge, src=str(a.src), ranks=report), indent=1,
                                                        default=int) + "\n")
    return 0


# -- A/B of two runtime-die runs ---------------------------------------------------------------------------------------
def parse_run(d: Path) -> dict:
    log = (d / "run.log").read_text() if (d / "run.log").exists() else ""
    prog = [tuple(map(int, m)) for m in re.findall(r"CYC (\d+) wall [\d.]+ s pc (\d+) (\d+) (\d+) (\d+)",
                                                     (d / "progress.log").read_text())]
    end = re.search(r"(END|TIMEOUT) cycles=(\d+)", log)
    wd = re.search(r"WATCHDOG no PC change for (\d+) cycles at cyc (\d+)", log)
    pcs = re.findall(r"die (\d) pc (\d+) unit_busy", log)
    return dict(progress=prog, end=end.group(1) if end else None, cycles=int(end.group(2)) if end else None,
                watchdog=dict(wd=int(wd.group(1)), at=int(wd.group(2))) if wd else None,
                final_pc={int(k): int(v) for k, v in pcs}, faults=re.findall(r"FAULT die=.*", log)[:4])


def cmd_ab(a):
    off, on = parse_run(a.off), parse_run(a.on)
    lev = json.loads((a.merged / "lever_images.json").read_text())
    merges = lev["ranks"]["0"]["merges"]
    vm = {}
    for dd in range(4):
        fo, fn = a.off / f"vm{dd}.hex", a.on / f"vm{dd}.hex"
        vm[dd] = fo.exists() and fn.exists() and sha(fo) == sha(fn)
    # stall point of each arm: the last PC change = watchdog cycle - WD
    # rows of every merged pair the ON run executed (its new PC precedes the ON stall PC) against the golden-derived
    # expected VM of each rank (expect_vm.hex: the TP-4 ISA executor's final VM, itself bit-exact to the golden)
    rows = {}
    stall_on = min(on["final_pc"].values()) if on["final_pc"] else None
    prog0, _ = read_prog(a.merged / "r0" / "prog.hex")
    for dd in range(4):
        exp = (a.src / f"r{dd}" / "expect_vm.hex").read_text().split()
        got = {k: (a.__dict__[k] / f"vm{dd}.hex").read_text().split() for k in ("off", "on")
               if (a.__dict__[k] / f"vm{dd}.hex").exists()}
        for m in merges:
            if stall_on is None or m["new_pc"] >= stall_on:
                continue
            f = prog0[m["new_pc"]]
            ob, n = f["qe_obase"], f["qe_nout"]
            # QE writes BF16 rows into FP32 containers at element addresses (one element per VM word here)
            key = f"r{dd}.pc{m['pc_first']}"
            rows[key] = {k: dict(rows=n, obase=ob,
                                 mismatches_vs_expect=sum(v[ob + i] != exp[ob + i] for i in range(n)))
                         for k, v in got.items()}
    rec = dict(off=off, on=on, vm_bit_identical_off_vs_on=vm, merges=merges, merged_rows_vs_expect_vm=rows)
    if off["watchdog"] and on["watchdog"]:
        lo = off["watchdog"]["at"] - off["watchdog"]["wd"]
        ln = on["watchdog"]["at"] - on["watchdog"]["wd"]
        rec["last_pc_change"] = dict(off=lo, on=ln, saved=lo - ln)
    # first 200-cycle progress sample at which die 0 shows each PC, ON pcs mapped back to the original numbering
    def first_seen(prog, remap):
        out = {}
        for cyc, p0, *_ in prog:
            q = remap(p0)
            if q not in out:
                out[q] = cyc
        return out
    new_first = sorted(m["new_pc"] for m in merges)
    to_orig = lambda n: n + sum(1 for x in new_first if x < n)  # noqa: E731
    fo, fn = first_seen(off["progress"], lambda n: n), first_seen(on["progress"], to_orig)
    rec["pc_first_seen_die0_200cyc"] = {str(k): dict(off=fo.get(k), on=fn.get(k),
                                                     saved=(fo[k] - fn[k]) if k in fo and k in fn else None)
                                        for k in sorted(set(fo) | set(fn))}
    print(json.dumps({k: v for k, v in rec.items() if k not in ("off", "on")}, indent=1))
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    return 0


# -- critical-path attribution on the program timing model ------------------------------------------------------------
def field_costs(flat: list[dict], die_off: Path, die_on: Path, rank: int = 0) -> dict:
    """Per weight-op ROM-field phase cost (cycles) for the OFF and ON programs of the die's layer:
    a merged-pair op = its flat-RTL measured wall cycles (dsrom_lever_phase_merge_flat score) + (die stream beats -
    flat stream beats); any other weight op = the measured mean fixed cost of a split phase + its die stream beats."""
    pairs = {tuple(p["pc"]): p for p in flat}
    fixed = [w - b for p in flat for w, b in zip(p["split_wall_cycles"], p["stream_beats_split"])]
    F = sum(fixed) / len(fixed)
    off_ph = {p["pc"]: p for p in json.loads((die_off / f"r{rank}" / "field_phases.json").read_text())["phases"]}
    on_ph = {p["pc"]: p for p in json.loads((die_on / f"r{rank}" / "field_phases.json").read_text())["phases"]}
    off, on = {}, {}
    for pc, ph in off_ph.items():
        off[pc] = F + ph["nbeat"]
    for (a, b), p in pairs.items():
        off[a] = p["split_wall_cycles"][0] + off_ph[a]["nbeat"] - p["stream_beats_split"][0]
        off[b] = p["split_wall_cycles"][1] + off_ph[b]["nbeat"] - p["stream_beats_split"][1]
    for pc, ph in on_ph.items():    # on_ph is keyed by the ORIGINAL first pc (weights.json pc)
        if any(pc == a for a, _ in pairs):
            p = pairs[next(k for k in pairs if k[0] == pc)]
            on[pc] = p["merged_wall_cycles"] + ph["nbeat"] - p["stream_beats_merged"]
        else:
            on[pc] = F + ph["nbeat"]
    return dict(fixed_mean=F, off=off, on=on)


def simulate_field(prog: list[dict], cost_by_pc: dict, chaining: bool, pos: int = 8191):
    """tools/hdc_timing_v41x.simulate_new with every ROM-field weight op (each op whose original pc has a die field
    phase) priced as one serial field phase: unit QE, occupancy = the phase cost, depth 0, output not chainable (the
    spine returns a phase's rows at its drain).  Collectives keep the model's XU price; CTL ops are not priced.
    chaining=False is the as-built in-order wait-mask sequencer."""
    import dataclasses
    import hdc_replay_v41 as R
    import hdc_timing_v41x as T
    orig = T.cost_new
    cmap = {id(f): cost_by_pc[f["_pc0"]] for f in prog if f.get("_pc0") in cost_by_pc}

    def cost(f0, f, D, sp, clock, vmap):
        c = cmap.get(id(f0))
        if c is None:
            return orig(f0, f, D, sp, clock, vmap)
        return "QE", max(1, round(c)), 0, None, False, "field"
    # CTL ops (rope prefetch / release) share unit code 0 with END, which stops simulate_new: drop them (unpriced)
    prog = [f for f in prog if not (f.get("unit", 0) == 0 and f.get("ctl", 0))]
    T.cost_new = cost
    try:
        st = {}
        cyc = T.simulate_new(prog, pos, R.SHIPPED, dataclasses.replace(T.Spec(), chaining=chaining), st)
    finally:
        T.cost_new = orig
    return cyc, st


def cmd_model(a):
    flat = [p for f in a.flat for p in json.loads(f.read_text())["pairs"]]
    by_rank = {}
    for f in a.flat:
        r = json.loads(f.read_text())
        by_rank[r["rank"]] = r["pairs"]
    rec = dict(schema="opentallas.dsrom_sys.lever.phase_merge_model.v1", layer=a.layer, pos=a.pos, ranks={})
    for rank, pairs in sorted(by_rank.items()):
        fc = field_costs(pairs, a.die_off, a.die_on, rank)
        base = emit_layer(a.layer, False)[0]
        for i, f in enumerate(base):
            f["_pc0"] = i
        _, merges = merge_program(base, True)
        out = dict(fixed_phase_cost_mean=fc["fixed_mean"])
        for chaining in (False, True):
            key = "inorder_waitmask" if not chaining else "chained_dataflow"
            c_off, st_off = simulate_field(base, fc["off"], chaining, a.pos)
            on, _ = merge_program(base, True)
            c_on, st_on = simulate_field(on, fc["on"], chaining, a.pos)
            per = []
            for m in merges:      # only this pair merged: its marginal (critical-path) saving
                one = list(base[:m["pc_first"]]) + [merge_program(base[m["pc_first"]:m["pc_first"] + 2], True)[0][0]] \
                    + list(base[m["pc_first"] + 2:])
                cost = dict(fc["off"])
                cost[m["pc_first"]] = fc["on"][m["pc_first"]]
                c1, _ = simulate_field(one, cost, chaining, a.pos)
                phase_saving = fc["off"][m["pc_first"]] + fc["off"][m["pc_second"]] - fc["on"][m["pc_first"]]
                per.append(dict(pc=[m["pc_first"], m["pc_second"]], tag=m["tag"], phase_saving=round(phase_saving, 1),
                                critical_path_saving=c_off - c1,
                                exposed_fraction=round((c_off - c1) / phase_saving, 3) if phase_saving else None))
            out[key] = dict(cycles_off=c_off, cycles_on=c_on, saved=c_off - c_on,
                            phase_saving_sum=round(sum(p["phase_saving"] for p in per), 1), per_pair=per,
                            critical_path_off={k: v for k, v in list(st_off["path"].items())[:8]},
                            critical_path_on={k: v for k, v in list(st_on["path"].items())[:8]})
        rec["ranks"][rank] = out
        print(rank, {k: (v["cycles_off"], v["cycles_on"], v["saved"], v["phase_saving_sum"]) for k, v in out.items()
                     if isinstance(v, dict)}, flush=True)
    if a.out:
        a.out.write_text(json.dumps(rec, indent=1, default=str) + "\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("program")
    p.add_argument("--prog", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--merge", action="store_true")
    p = sp.add_parser("emitter")
    p.add_argument("--layer", type=int, action="append", required=True)
    p.add_argument("--out", type=Path)
    p = sp.add_parser("images")
    p.add_argument("--src", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--merge", action="store_true")
    p.add_argument("--ranks", type=lambda s: [int(x) for x in s.split(",")], default=[0, 1, 2, 3])
    p = sp.add_parser("ab")
    p.add_argument("--off", type=Path, required=True)
    p.add_argument("--on", type=Path, required=True)
    p.add_argument("--merged", type=Path, required=True)
    p.add_argument("--src", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sp.add_parser("model")
    p.add_argument("--flat", type=Path, action="append", required=True, help="dsrom_lever_phase_merge_flat score record")
    p.add_argument("--die-off", type=Path, required=True)
    p.add_argument("--die-on", type=Path, required=True)
    p.add_argument("--layer", type=int, default=0)
    p.add_argument("--pos", type=int, default=8191)
    p.add_argument("--out", type=Path)
    a = ap.parse_args()
    return dict(program=cmd_program, emitter=cmd_emitter, images=cmd_images, ab=cmd_ab, model=cmd_model)[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
