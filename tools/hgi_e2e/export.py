#!/usr/bin/env python3
"""hgi-e2e golden export: one layer of a model on ONE die (rank 0) through the HGI-1 simulator, as the die-level RTL
harness (rtl/hbm_accel/generic/e2e/tb_hgi_e2e.sv) consumes it.

    python3 -m hgi_e2e.export qwen --snapshot SNAP --cache QIMG --layer 0 --position 8191 --out DIR   (from tools/)
    python3 -m hgi_e2e.export ds --refs REFS --layer 0 --out DIR

The simulator runs the bit-exact program on every die of the group (Qwen TP4: 4 dies; DS TP96: 96 dies); this export
keeps rank 0's view:
  meta.json      program (image, model descriptor, doorbell), one entry per DISPATCHED record (program order = the
                 in-order CP's dispatch order): unit / op / tag, header, the effective base / n of every operand (what
                 the CP must hand the unit), the simulator's unit cost and S2 schedule (start / end / dispatch), the
                 offsets of its golden VM / HBM writes, and for COLL records every rank's contribution file
  image.bin      the program image (placed at image_base in HBM)
  vm0.bin        rank 0's VM at the doorbell (262,144 x u32)
  vm_final.bin   rank 0's VM after the last record
  hbm.bin        the HBM byte ranges any record reads or writes (SM weights excluded unless --sm-weights), as
                 {u64 addr, u64 len, bytes} entries at the doorbell
  vmw.bin        per record: {u32 addr, u32 value} for every VM word the record writes (diff U output footprint)
  hbmw.bin       per record: {u64 addr, u64 len, bytes} for every HBM range the record changes
  coll_<k>.bin   per COLL record: every rank's A operand as FP32 words, rank-major (the collective model's peers)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import time
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import hbm_generic_iface as HGI  # noqa: E402

from hgi_sim import machine as MC  # noqa: E402
from hgi_sim.records import encode_program, decode_program, OPND  # noqa: E402

IMAGE_PAGE = 0x10                     # image at HBM byte 0x10000 (free in both models' maps)
ESZ = MC.ESIZE


def md_words(vocab, ctx_max, group, image_bytes):
    md = dict(magic=HGI.MAGIC, ver_minor=HGI.D_VERSION[1], ver_major=HGI.D_VERSION[0], n_words=HGI.NWORDS,
              cp_vocab=vocab, cp_ctx_max=ctx_max, coll_group_size=group, entry_ar=0, image_base=IMAGE_PAGE,
              image_pages=-(-image_bytes // 4096) + 1)
    w = HGI.d_pack(md)
    assert HGI.d_hw_check(w) == 0
    return w


def hbm_span(M, d, die, L):
    base, n, m, st, ist = M.eff(d, die, L)
    es = ESZ[d.fmt]
    if m == 0 or n == 0:
        return None
    span = (m - 1) * st + ((n - 1) * ist + 1) * es
    return (base, base + max(span, es))


class Capture:
    """Wraps every unit function: rank 0's effective operands before, its VM / HBM writes after."""

    def __init__(self, M, die0, sm_weights=False):
        self.M, self.die0, self.sm_weights = M, die0, sm_weights
        self.recs = []
        self.vmw = bytearray()
        self.hbmw = bytearray()
        self.touch = []                      # HBM byte intervals read or written by rank 0
        self.coll = {}

    def wrap(self, key, fn):
        def run(M, r, L):
            die0 = self.die0
            if die0 not in M.dies:
                return fn(M, r, L)
            r0 = M.rec_of(die0, r)
            M.cur = r0 if M.die_recs is None else r
            dies_save = M.dies
            try:
                M.dies = [die0]
                M.cur = r0
                eff = {}
                for nm in OPND:
                    d = r0.desc.get(nm)
                    if d is None:
                        continue
                    b, n, m, st, ist = M.eff(d, die0, L)
                    eff[nm] = [int(b), int(n), int(m), int(st), int(ist), d.space, d.fmt]
                    if d.space == "HBM" and (r0.unit != "SM" or nm != "B" or self.sm_weights):
                        sp = hbm_span(M, d, die0, L)
                        if sp:
                            self.touch.append(sp)
                    elif d.space == "HBM" and r0.unit == "SM":
                        pass
                coll_parts = None
                if r0.unit == "COLL":
                    coll_parts = []
                    for dd in dies_save:
                        rr = M.rec_of(dd, r)
                        M.dies, M.cur = [dd], rr
                        a = rr.desc["A"]
                        coll_parts.append(np.asarray(M.read(a, dd, L), dtype=np.float32).view(np.uint32).copy()
                                          if a.space == "VM" else np.zeros(0, np.uint32))
                # footprint of the VM outputs
                M.dies, M.cur = [die0], r0
                fp = []
                for nm in ("O", "R", "D"):
                    d = r0.desc.get(nm)
                    if d is not None and d.space == "VM" and not (r0.unit == "SU" and nm == "D") \
                            and not (r0.unit == "IDX" and nm == "D" and not (r0.param >> 12) & 1):
                        try:
                            fp.append(M.vm_addrs(d, die0, L))
                        except MC.Fault:
                            pass
                vm_pre = die0.vm.copy()
                hb_pre = [(b, dat.copy()) for b, dat, nm_ in die0.hbm.regions if dat.size <= (1 << 28)]
            finally:
                M.dies = dies_save
                M.cur = r
            fn(M, r, L)
            ch = np.nonzero(die0.vm != vm_pre)[0]
            addrs = np.unique(np.concatenate([ch] + fp)).astype(np.uint32) if (len(ch) or fp) else np.zeros(0, np.uint32)
            vals = die0.vm[addrs]
            off_vm = len(self.vmw)
            self.vmw += np.stack([addrs, vals], axis=1).astype("<u4").tobytes()
            off_h = len(self.hbmw)
            nh = 0
            for (b, pre), (b2, dat, nm_) in zip(hb_pre, [x for x in die0.hbm.regions if x[1].size <= (1 << 28)]):
                assert b == b2
                diff = np.nonzero(pre != dat)[0]
                if len(diff):
                    lo, hi = int(diff[0]) & ~31, (int(diff[-1]) + 32) & ~31
                    hi = min(hi, dat.size)
                    self.hbmw += struct.pack("<QQ", b + lo, hi - lo) + dat[lo:hi].tobytes()
                    self.touch.append((b + lo, b + hi))
                    nh += 1
            k = len(self.recs)
            if coll_parts is not None:
                self.coll[k] = coll_parts
            self.recs.append(dict(k=k, unit=r0.unit, op=r0.op, tag=getattr(r0, "tag", ""), L=int(L),
                                  hdr=f"{r0.encode()[:16][::-1].hex()}", eff=eff, vm_off=off_vm // 8,
                                  vm_n=int(len(addrs)), hbm_off=off_h, hbm_n=nh))
        return run


def merge(iv):
    iv = sorted((a & ~31, (b + 31) & ~31) for a, b in iv)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def write_out(out, cap, M_dies, die0, image, words, dyn, meta, hbm_pre):
    out.mkdir(parents=True, exist_ok=True)
    (out / "image.bin").write_bytes(image)
    (out / "vmw.bin").write_bytes(bytes(cap.vmw))
    (out / "hbmw.bin").write_bytes(bytes(cap.hbmw))
    (out / "vm_final.bin").write_bytes(die0.vm.astype("<u4").tobytes())
    for k, parts in cap.coll.items():
        (out / f"coll_{k}.bin").write_bytes(b"".join(p.astype("<u4").tobytes() for p in parts))
    meta.update(md_words=words, dyn=dyn, records=cap.recs, image_bytes=len(image),
                image_sha256=hashlib.sha256(image).hexdigest(), image_base_bytes=IMAGE_PAGE * 4096)
    (out / "meta.json").write_text(json.dumps(meta, indent=1, default=int) + "\n")
    with open(out / "hbm.bin", "wb") as f:
        for a, b in merge(cap.touch):
            f.write(struct.pack("<QQ", a, b - a) + hbm_pre(a, b - a))


# ------------------------------------------------------------------------------------------------------------- Qwen
def export_qwen(a):
    import qwen_r25_golden as R
    from hgi_sim import qwen_compiler as QC
    from hgi_sim import timing as T
    from hgi_sim.machine import UNITS, Die, Machine
    model = R.QwenR25(a.snapshot, a.cache)
    cfg = model.ck.cfg
    layer, pos = a.layer, a.position
    g = QC.Geometry(cfg, 8192)
    md = QC.qwen_params(cfg)
    Kc, Vc = R.synthetic_kv(model, layer, pos)
    x = R.synthetic_x(model, layer)
    tr = {}
    x_out = model.layer(layer, x, pos, Kc.copy(), Vc.copy(), tr)
    hbms, _ = QC.build_images(model, g, [layer], kv_state={layer: (Kc, Vc)}.get)
    recs = QC.program(g, md, 1, parts=("layers",))
    image = encode_program(recs)
    dies = [Die(d, hbms[d]) for d in range(QC.TP)]
    words = md_words(cfg["vocab_size"], 40960, QC.TP, len(image))
    M = Machine(dies, dict(UNITS))
    assert M.cfg_commit(list(words)) == 0
    for d in dies:
        d.vm[g.vm["X"]:g.vm["X"] + g.H] = np.asarray(x, np.float32).view(np.uint32)
    die0 = dies[0]
    snapshot = {id(dat): dat.copy() for b, dat, nm in die0.hbm.regions if dat.size <= (1 << 28)}
    regions = list(die0.hbm.regions)
    vm0 = die0.vm.copy()
    cap = Capture(M, die0, a.sm_weights)
    M.units = {k: cap.wrap(k, fn) for k, fn in M.units.items()}
    dr = decode_program(image)
    for r, r0 in zip(dr, recs):
        r.tag, r.family = r0.tag, r0.family
    t0 = time.time()
    tok, trace = M.run(image, 0, pos, hash_bufs=False, recs=dr)
    wall = time.time() - t0
    # golden check: the layer output on rank 0 equals qwen_r25
    xo = die0.vm[g.vm["X"]:g.vm["X"] + g.H]
    ok = bool(np.array_equal(xo, np.asarray(x_out, np.float32).view(np.uint32)))
    sch = T.schedule(recs, pos, "S2")
    sch_nw = T.schedule(recs, pos, "S2", wires=False)
    ex = sch["ex"]
    j = 0
    for i, (k, L, L1) in enumerate(ex):
        if recs[k].unit == "CTL":
            continue
        e = cap.recs[j]
        assert e["unit"] == recs[k].unit and e["op"] == recs[k].op, (e, recs[k].unit)
        e.update(cost=round(float(sch["costs"][i][0]), 1), cost_how=sch["costs"][i][2],
                 s2_disp=round(sch["disp"][i], 1), s2_start=round(sch["start"][i], 1), s2_end=round(sch["end"][i], 1))
        j += 1
    assert j == len(cap.recs)

    def hbm_pre(addr, n):
        for b, dat, nm in regions:
            if b <= addr and addr + n <= b + dat.size:
                src = snapshot.get(id(dat), dat)
                return src[addr - b:addr - b + n].tobytes()
        raise SystemExit(f"HBM range {addr:#x}+{n} outside the regions")
    vm0_path = a.out / "vm0.bin"
    a.out.mkdir(parents=True, exist_ok=True)
    vm0_path.write_bytes(vm0.astype("<u4").tobytes())
    meta = dict(schema="opentallas.hgi_e2e.export.v1", model="Qwen3-8B", vehicle=f"qwen_L{layer}_P{pos}", layer=layer,
                position=pos, rank=0, group=QC.TP, token=0, layer_out_exact_vs_qwen_r25=ok,
                layer_out_vm=[g.vm["X"], g.H], sim_wall_s=round(wall, 1),
                s2_cycles=round(sch["total_cycles"], 1), s2_no_wires_cycles=round(sch_nw["total_cycles"], 1),
                timing_grade="hgi_sim.timing S2 (calibration.json; SM / SU / HBM first access measured, rest estimates)",
                golden="qwen_r25 (released Qwen3-8B, INT8 image, permuted RoPE), synthetic format-valid KV at the position",
                source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                    "hgi_sim/machine.py", "hgi_sim/qwen_compiler.py", "hgi_sim/records.py", "hgi_sim/lib.py",
                    "hgi_sim/timing.py", "qwen_r25_golden.py", "hgi_e2e/export.py")})
    write_out(a.out, cap, dies, die0, image, words, [0, pos, pos + 1, 0, 0, 0, 0, pos], meta, hbm_pre)
    print(f"qwen L{layer} P{pos}: {len(cap.recs)} dispatched records, layer out exact {ok}, S2 {sch['total_cycles']:.0f}")
    return 0 if ok else 1


# --------------------------------------------------------------------------------------------------------------- DS
def export_ds(a):
    from hgi_sim import ds_native as DN
    from hgi_sim import timing as T
    from hgi_sim.ds_native_timing import NativeCost
    from hgi_sim.records import decode_one
    st = {}
    orig = DN.run_per_die

    def run_per_die(Mach, progs, units, pos, token, hook=None, trace=None):
        die0 = next(d for d in Mach.dies if d.rank == 0)
        regions = list(die0.hbm.regions)
        st.update(vm0=die0.vm.copy(), regions=regions,
                  snap={id(dat): dat.copy() for b, dat, nm in regions if dat.size <= (1 << 28)},
                  image=encode_program(progs[0]), pos=pos, token=token, die0=die0)
        cap = Capture(Mach, die0, a.sm_weights)
        wrapped = {k: cap.wrap(k, fn) for k, fn in units.items()}
        st["cap"] = cap
        t0 = time.time()
        orig(Mach, progs, wrapped, pos, token, hook, trace)
        st["wall"] = time.time() - t0
    DN.run_per_die = run_per_die
    prog = a.out / "ds_program.json"
    a.out.mkdir(parents=True, exist_ok=True)
    argv = ["ds_native", "--layers", str(a.layer), "--refs", str(a.refs), "--out", str(a.out / "ds_native_run.json"),
            "--program-out", str(prog)]
    sys.argv = argv
    rc = DN.main()
    run = json.loads((a.out / "ds_native_run.json").read_text())
    cap, die0 = st["cap"], st["die0"]
    d = json.loads(prog.read_text())
    lay = d["layers"][0]
    recs = []
    for x in lay["records"]:
        r, _ = decode_one(bytes.fromhex(x["hex"]), 0)
        r.tag, r.family, r.reads, r.writes = x["tag"], x["family"], x["reads"], x["writes"]
        r.src_key = None if not x["src"] else f"{x['src'][0]}:{x['src'][1]}"
        r.src_extra = [f"{x['src'][0]}:{e}" for e in x["src"][2]] if x["src"] and len(x["src"]) > 2 else []
        r.layer = lay["layer"]
        recs.append(r)
    assert encode_program(recs) == st["image"], "program dump != rank 0 image"
    cf = NativeCost(d["ops"], recs)
    sch = T.schedule(recs, st["pos"], "S2", cost_fn=cf)
    sch_nw = T.schedule(recs, st["pos"], "S2", cost_fn=cf, wires=False)
    j = 0
    for i, (k, L, L1) in enumerate(sch["ex"]):
        if recs[k].unit == "CTL":
            continue
        e = cap.recs[j]
        assert e["unit"] == recs[k].unit and e["op"] == recs[k].op
        e.update(cost=round(float(sch["costs"][i][0]), 1), cost_how=sch["costs"][i][2],
                 s2_disp=round(sch["disp"][i], 1), s2_start=round(sch["start"][i], 1), s2_end=round(sch["end"][i], 1))
        j += 1
    assert j == len(cap.recs), (j, len(cap.recs))
    image = st["image"]
    # the program ends without CTL.END: the harness appends one (END reads a token word the export plants in VM)
    words = md_words(129280, 1 << 20, 96, len(image) + 64)

    def hbm_pre(addr, n):
        for b, dat, nm in st["regions"]:
            if b <= addr and addr + n <= b + dat.size:
                src = st["snap"].get(id(dat), dat)
                return src[addr - b:addr - b + n].tobytes()
        raise SystemExit(f"HBM range {addr:#x}+{n} outside the regions")
    (a.out / "vm0.bin").write_bytes(st["vm0"].astype("<u4").tobytes())
    res = run["results"][0]
    meta = dict(schema="opentallas.hgi_e2e.export.v1", model="DeepSeek-V4.1-Flash", vehicle=f"ds_L{a.layer}_1M",
                layer=a.layer, position=st["pos"], rank=0, group=96, token=int(st["token"]),
                layer_verdict_sim_vs_golden=res["verdict"], sim_regions=[(x.get("region"), x.get("bit_exact"))
                                                                         for x in res.get("regions", [])],
                sim_wall_s=round(st["wall"], 1), s2_cycles=round(sch["total_cycles"], 1),
                s2_no_wires_cycles=round(sch_nw["total_cycles"], 1), needs_end=True,
                timing_grade="hgi_sim.ds_native_timing NativeCost (walk prices, SU depth model) S2 for this layer alone",
                golden="ds_native vs the released-checkpoint golden shards (ctx 1,048,576)",
                source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest() for p in (
                    "hgi_sim/machine.py", "hgi_sim/ds_native.py", "hgi_sim/records.py", "hgi_sim/lib.py",
                    "hgi_sim/timing.py", "hgi_sim/ds_native_timing.py", "hgi_e2e/export.py")})
    write_out(a.out, cap, None, die0, image, words, [0, st["pos"], st["pos"] + 1, int(st["token"]), 0, 0, 0, st["pos"]],
              meta, hbm_pre)
    print(f"ds L{a.layer}: {len(cap.recs)} dispatched records, sim {res['verdict']}, S2 {sch['total_cycles']:.0f}")
    return rc


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("model", choices=("qwen", "ds"))
    ap.add_argument("--snapshot", type=Path)
    ap.add_argument("--cache", type=Path)
    ap.add_argument("--refs", type=Path)
    ap.add_argument("--layer", type=int, default=0)
    ap.add_argument("--position", type=int, default=8191)
    ap.add_argument("--sm-weights", action="store_true", help="also export the SM weight bytes (real SM runs)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    return export_qwen(a) if a.model == "qwen" else export_ds(a)


if __name__ == "__main__":
    raise SystemExit(main())
