#!/usr/bin/env python3
"""LB2-HBM-CQW (10-18): Qwen3-8B D4G8 layer-programme compiler -> per-unit images + SW-slice replay events.

The Qwen path of the d4g layer bench (layer_images.py is the DeepSeek path; the unit FORMATS are shared and imported
from it: su_record / QLine / Placement / column_image / vop_golden / SU constants -- not duplicated, not edited here).

Programme of record: the D4G8 compiled 8-die programme (tools/hgi_sim/qwen_compiler.py Geometry tp=8), the one the
accepted-cost ledger re-based to 948.8 tok/s (main 146248223) and qwen_d4g_proof.py ran bit-exact against the qwen_r25
golden (TP-4 order of record; down = whole TP-4 slice-j partial per row half + GROUP_REDUCE_MCAST s 4 in rank order;
the plain 8-way down split is NOT used -- it changes the golden rounding).  Its image program.hgi1 per stage is
committed (results/rtl/hbm_qwen_layer_tput_1018/fixtures/program/<stage>.hgi1, sha256 == fixtures/manifest_<stage>.json).
Schedule: static_schedule.json schedule.<variant>.d4g8.<stage> (variant landed = the GEN2 landed die; rows matched to
executed records by (programme record, layer) -- tags come from the schedule).

Operands are NOT placeholders: `snap` (fleet; the D4G8 fixtures -- HBM images, x_in, md words -- are on the fleet
only, verified against the committed manifests) runs the HGI-1 functional model (hgi_sim.machine) over the fixture,
which qwen_d4g_proof showed bit-exact to the golden, and takes for every SU record of ranks R the VM words it reads
(state before the record) and the words it must write (state after).  It also checks every expected.npz array of
ranks R appears exactly in the run (fixture integrity).  The VM words each emitted record touches go to
operands_<stage>.npz (committed); `emit` re-runs the compiler from that file locally (no fleet), byte-identical.

Per emitted SU record the expected O words = vop_golden(operands) (the image compiler's own lane model) AND are
checked equal to the HGI functional model's post-record VM (status golden_mismatch otherwise).  A chained operand
the slice would read from an earlier emitted record's drain but which a NON-replayed record (SM / ATT / COLL / FUSED
/ SFU / DMA) overwrote in between is flagged chain_stale (the slice cannot reproduce it; image load instead).

    PYTHONPATH=tools python3 -m hbm_layer_vehicle.qwen_layer_images snap --fix FIXDIR/<stage> --stage L0 --ranks 0,5 \
        --out OUTDIR            # fleet: writes OUTDIR/<stage>/r<rank>/{replay,manifest}.json + operands_<stage>.npz
    PYTHONPATH=tools python3 -m hbm_layer_vehicle.qwen_layer_images emit --stage L0 --ranks 0,5 \
        --operands results/rtl/hbm_qwen_layer_tput_1018/images/operands_L0.npz --out OUTDIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
ROOT = TOOLS.parent
for p in (TOOLS, TOOLS / "hbm_static", TOOLS / "hgi_adapters"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hbm_layer_vehicle import layer_images as LI  # noqa: E402

QREC = ROOT / "results/rtl/hbm_qwen_layer_tput_1018"
PROG_DIR = QREC / "fixtures/program"
SCHEDULE = QREC / "static_schedule.json"
BOUNDARY = ROOT / "results/rtl/hbm_ds_layer_tput_1018/slice_sw/boundary.json"
POS, VOCAB, CTXMAX, TP = 8191, 151936, 40960, 8
STAGES = ("L0", "chain", "head")


def sha(b):
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------------------------- programme / schedule
def programme(stage, prog=None):
    p = Path(prog) if prog else PROG_DIR / f"{stage}.hgi1"
    img = p.read_bytes()
    man = json.loads((QREC / f"fixtures/manifest_{stage}.json").read_text())
    want = man["files"]["program.hgi1"]["sha256"]
    if sha(img) != want:
        raise SystemExit(f"programme {p}: sha256 {sha(img)} != committed manifest {want}")
    return img, p


def dispatches(img, rank, vm=None):
    """the sequencer reference's (hgi_seq_vectors.Ref) dispatch trace of the D4G8 image for one rank, as
    [(program record index k, record, dispatch, layer L)] in execution order."""
    import su_bench as SB
    from hgi_sim import records as SR
    recs = SR.decode_program(img)
    words = [int.from_bytes(img[q:q + 16], "little") for q in range(0, len(img), 16)]
    ref = SB.C.SV.Ref(words, 0, 0, POS, rank, VOCAB, CTXMAX, vm or {})
    tr, cpl = ref.run()
    if getattr(ref, "fault", None):
        raise SystemExit(f"sequencer Ref fault rank {rank}: {ref.fault}")
    pc_of, pc = {}, 0
    for k, r in enumerate(recs):
        pc_of[pc] = k
        pc += SR.rec_bytes(r) // 16
    return [(pc_of[d["rec"]], recs[pc_of[d["rec"]]], d, d.get("L", 0)) for d in tr], recs


def schedule(stage, variant="landed"):
    s = json.loads(SCHEDULE.read_text())
    return s["schedule"][variant]["d4g8"][stage]


def align(stage, disp, variant="landed"):
    """schedule rows (CTL excluded) <-> executed dispatches, by (record, layer) in order; unit/op must agree."""
    rows = [r for r in schedule(stage, variant) if r["unit"] != "CTL"]
    if len(rows) != len(disp):
        raise SystemExit(f"{stage}: {len(rows)} scheduled non-CTL records vs {len(disp)} dispatches")
    out = []
    for r, (k, rec, d, L) in zip(rows, disp):
        if (r["rec"], r["L"]) != (k, L) or (r["unit"], r["op"]) != (rec.unit, rec.op):
            raise SystemExit(f"{stage}: schedule row {r['i']} {r['unit']}.{r['op']} rec {r['rec']} L {r['L']} != "
                             f"dispatch rec {k} L {L} {rec.unit}.{rec.op}")
        out.append((r, k, rec, d, L))
    return out


# ------------------------------------------------------------------------------------------------------- VM views
class VMData(dict):
    """su_record's operand dict: golden-chained values of emitted records first, else the functional model's VM
    state before this record (never a placeholder: every address is 'present')."""

    def __init__(self, chained, pre):
        super().__init__(chained)
        self.pre = pre

    def __contains__(self, a):
        return True

    def __missing__(self, a):
        return np.uint32(self.pre(int(a))).view(np.float32)


class SparseVM:
    """VM words from operands_<stage>.npz (rank, executed index j) -> {addr: word} before / after."""

    def __init__(self, npz, rank):
        z = np.load(npz)
        self.pre, self.post = {}, {}
        for key in z.files:
            kind, r, j = key.split("_")
            if int(r[1:]) != rank:
                continue
            a = z[key]
            tgt = self.pre if kind == "pre" else self.post
            tgt[int(j[1:])] = dict(zip(a[0].tolist(), a[1].tolist()))

    def before(self, j):
        d = self.pre.get(j, {})
        return lambda a: d[a]

    def after(self, j):
        d = self.post.get(j, {})
        return lambda a: d[a]


class FullVM:
    def __init__(self, pre, post):
        self.pre_, self.post_ = pre, post          # j -> np.uint32 array
        self.touched = {}                          # j -> (pre addrs, post addrs)

    def before(self, j):
        v = self.pre_[j]
        s = self.touched.setdefault(j, (set(), set()))[0]

        def f(a):
            s.add(a)
            return int(v[a])
        return f

    def after(self, j):
        v = self.post_[j]
        s = self.touched.setdefault(j, (set(), set()))[1]

        def f(a):
            s.add(a)
            return int(v[a])
        return f


# --------------------------------------------------------------------------------------------------------- compile
def compile_rank(stage, rank, vm, out, boundary=BOUNDARY, variant="landed", quarter=0, load_gap=16,
                 reload_gap=600, img=None, disp_raw=None):
    """emit replay.json + manifest.json for one rank of one stage.  vm: FullVM | SparseVM.  disp_raw: optional
    {j: raw hex} of the dispatches (the fleet run's Ref with the die's VM tables) to cross-check the local Ref."""
    import su_bench as SB
    img, prog_path = img or programme(stage)
    disp, _ = dispatches(img, rank)
    rows = align(stage, disp, variant)
    bnd = json.loads(Path(boundary).read_text())
    inports = {e["name"]: e for e in bnd["inputs"]}
    out.mkdir(parents=True, exist_ok=True)
    manifest, pending = [], []
    rng = np.random.default_rng(1018)
    place, chained = LI.Placement(quarter), {}
    for j, (r, k, rec, d, L) in enumerate(rows):
        unit = r["orig_op"].split(".")[0]
        ent = dict(i=r["i"], j=j, rec=k, L=L, unit=r["unit"], op=r["orig_op"], tag=r["tag"], start=r["start"],
                   end=r["end"], cls=r["cls"], blocked_by=[], reasons=[],
                   target_ports=[p for p in LI.UNIT_PORTS.get(unit, []) if p in inports])
        if unit != "SU":
            ent.update(status="format_open", reasons=[f"{unit} programme image format not emitted by v1 "
                                                      "(layer_images formats_open)"])
            manifest.append(ent)
            continue
        raw = SB.pack_rec(d)
        if disp_raw is not None and disp_raw.get(j) not in (None, f"{raw:x}"):
            ent["reasons"].append("local Ref dispatch differs from the fleet run's (VM-table dependent)")
        written0 = set(place.written)
        try:
            su = LI.su_record(raw, quarter, rng, data=VMData(chained, vm.before(j)), place=place,
                              tag=f"{r['tag']}@L{L}")
        except AssertionError as ex:
            place.written = written0
            ent.update(status="adapter_refused", reasons=[f"su_program_inventory.decode: {ex}"])
            manifest.append(ent)
            continue
        ent.update(status=su["status"], lowering=su.get("lowering"), inputs_placeholder=su.get("inputs_placeholder"))
        ent["reasons"] += su.get("reasons", [])
        if su["status"] == "emitted":
            post = vm.after(j)
            bad = [(a, v) for x in su["expect"] for a, v in zip(x["words"], x["value"]) if v is not None and v != post(a)]
            ent["golden_vs_hgi"] = dict(words=sum(v is not None for x in su["expect"] for v in x["value"]),
                                        mismatch=len(bad))
            if bad:
                ent["status"] = "golden_mismatch"
                ent["reasons"].append(f"vop_golden != HGI functional model on {len(bad)} words "
                                      f"(first addr {bad[0][0]})")
            pre = vm.before(j)
            stale = [a for ls_, _ in su["fills"] for a in range(8 * ls_, 8 * ls_ + 8) if a in chained and
                     int(np.float32(chained[a]).view(np.uint32)) != pre(a)]
            if stale:
                ent["status"] = "chain_stale"
                ent["reasons"].append(f"{len(stale)} chained operand words overwritten by a non-replayed record "
                                      f"(first addr {stale[0]})")
        if ent["status"] != "emitted":
            place.written = written0
        else:
            for x in su["expect"]:
                for a, v in zip(x["words"], x["value"]):
                    if v is not None:
                        chained[a] = np.uint32(v).view(np.float32)
            dd = out / "images" / f"r{r['i']:03d}_su"
            dd.mkdir(parents=True, exist_ok=True)
            ent.update(edges=len(su["lines"]), fill_sectors=su["fill_sectors"], drain_sectors=su["drain_sectors"])
            (dd / "record.json").write_text(json.dumps(dict(preload={str(a): v for a, v in su["preload"].items()},
                                                            expect=su["expect"], data=su["data"]), indent=0))
            pending.append((r, ent, su))
        manifest.append(ent)
    events, cfgs, t0 = pack(pending, out, quarter, load_gap, reload_gap)
    for p in {e["port"] for e in events if e["k"] == "D"}:
        assert p in inports, f"replay drives {p}, not a slice input port"
    pre_conf = preload_conflicts(events)
    layer_cyc = max(r["end"] for r in schedule(stage, variant))
    rep = dict(schema="opentallas.hbm_slice_replay.v1", slice=bnd.get("slice_top", "sw"), design="qwen",
               layer=stage, rank=rank, t0_serial=t0, priced_layer_cycles=layer_cyc,
               assumptions=["serial = ceil(3*stream/4)", "SU quarter VM placement quarter-packed (compiler's own)",
                            "VM operands as M preload events (no slice VM input port) = image load of the producers' "
                            "state from the HGI functional model run of the committed fixture",
                            f"start advance {LI.START_ADVANCE}, config lead {LI.CFG_LEAD} (pgcol.sv header)"],
               events=events)
    (out / "replay.json").write_text(json.dumps(rep) + "\n")
    man = dict(schema="opentallas.hbm_layer_images.v1", design="qwen", mapping="D4G8 (qwen_compiler Geometry tp=8)",
               stage=stage, rank=rank, schedule_variant=variant, programme=str(prog_path.relative_to(ROOT))
               if prog_path.is_relative_to(ROOT) else str(prog_path), programme_sha256=sha(img),
               boundary=str(Path(boundary).relative_to(ROOT)) if Path(boundary).is_relative_to(ROOT) else str(boundary),
               records=manifest, placement_conflicts=place.conflicts, preload_conflicts=pre_conf,
               placed_sectors=len(place.map), su_programmes=cfgs, t0_serial=t0, priced_layer_cycles=layer_cyc,
               counts={k: sum(1 for m in manifest if m["status"] == k) for k in sorted({m["status"] for m in manifest})})
    (out / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return man, rep


def preload_conflicts(events):
    """two M preloads of one physical sector with different words (all preloads are at cycle 0)."""
    seen, bad = {}, []
    for e in events:
        if e["k"] != "M":
            continue
        v = seen.setdefault(e["sector"], e["val"])
        if v != e["val"]:
            bad.append(dict(sector=e["sector"], rec=e["rec"]))
    return bad


def pack(pending, out, quarter, load_gap, reload_gap):
    """SU programme packing + replay events: the same rule as layer_images.main (adjacent SU records share one pgp
    programme when they fit EDGES and the gap is too short to reload; load while idle, CFG_LEAD before start)."""
    Q_W, QLine = LI.Q_W, LI.QLine
    progs = []
    for r, ent, su in pending:
        want0 = LI.serial(r["start"]) - su["setup_edge"]
        P = progs[-1] if progs else None
        if P is None or want0 - P["end"] >= reload_gap or want0 - P["base"] + len(su["lines"]) > LI.EDGES_MAX:
            P = dict(base=want0, end=want0, ql=QLine(), recs=[])
            progs.append(P)
        o = max(0, want0 - P["base"])
        while any((o + e) in P["ql"].f[fld] and (P["ql"].f[fld][o + e] & v) for fld in Q_W
                  for e, v in su["ql"].f[fld].items()):
            o += 1
        for fld in Q_W:
            for e, v in su["ql"].f[fld].items():
                P["ql"].f[fld][o + e] = P["ql"].f[fld].get(o + e, 0) | v
        P["end"] = max(P["end"], P["base"] + o + len(su["lines"]))
        P["recs"].append((r, ent, su, o))
    for k, P in enumerate(progs):
        lines = P["ql"].lines()
        man, cfg = LI.column_image(lines, out / "images" / f"su_prog{k:02d}")
        P.update(lines=lines, cfg=cfg, man=man)
    t0 = 3 + (len(progs[0]["cfg"]) if progs else 0) + LI.CFG_LEAD + LI.START_ADVANCE + load_gap
    events, cfgs, busy_until, shift, written_at = [], [], 3, 0, {}
    for k, P in enumerate(progs):
        line0 = t0 + P["base"] + shift
        s_edge = line0 - LI.START_ADVANCE
        load0 = s_edge - LI.CFG_LEAD - len(P["cfg"])
        note = None
        if load0 < busy_until:
            d = busy_until - load0
            note = f"load_window_conflict: programme {k} needs {len(P['cfg'])} idle edges, shifted +{d}"
            shift += d
            load0, s_edge, line0 = load0 + d, s_edge + d, line0 + d
        for j, (b, row, data) in enumerate(P["cfg"]):
            for port, val in (("su_prog__r_we", 1), ("su_prog__r_bank", b), ("su_prog__r_row", row),
                              ("su_prog__r_data", int(data, 16))):
                events.append(dict(k="D", dom="serial", cyc=load0 + j, port=port, val=f"{val:x}", src="image:SU",
                                   prog=k))
        events.append(dict(k="D", dom="serial", cyc=load0 + len(P["cfg"]), port="su_prog__r_we", val="0",
                           src="image:SU", prog=k))
        events.append(dict(k="D", dom="serial", cyc=s_edge, port="su_prog__r_len", val=f"{len(P['lines']):x}",
                           src="image:SU", prog=k))
        events.append(dict(k="D", dom="serial", cyc=s_edge, port="su_prog__r_start", val="1", src="image:SU", prog=k))
        events.append(dict(k="D", dom="serial", cyc=s_edge + 1, port="su_prog__r_start", val="0", src="image:SU",
                           prog=k))
        busy_until = line0 + len(P["lines"])
        img = out / "images" / f"su_prog{k:02d}/cols/config.mem"
        cfgs.append(dict(programme=k, records=[x[0]["i"] for x in P["recs"]], edges=len(P["lines"]),
                         config_writes=len(P["cfg"]), load_serial=load0, start_serial=s_edge,
                         image=str(img.relative_to(out)), image_sha256=sha(img.read_bytes()),
                         columns=P["man"]["columns"], note=note))
        for r, ent, su, o in P["recs"]:
            l0 = line0 + o
            for sec, words in su["preload"].items():
                events.append(dict(k="M", dom="stream", cyc=0, mem="vm", quarter=quarter, sector=sec, bank=sec % 8,
                                   row=(sec & 0x1fff) >> 3, val="".join(su["data"][str(w)] for w in reversed(words)),
                                   src="image:VM_preload", rec=r["i"]))
            for x in su["expect"]:
                val = "".join(f"{v or 0:08x}" for v in reversed(x["value"]))
                msk = "".join("ffffffff" if (x["mask"] >> b) & 1 and x["value"][b] is not None else "00000000"
                              for b in reversed(range(8)))
                events.append(dict(k="C", dom="serial", cyc=l0 + x["edge"], port=f"vm:{x['sector']:x}", val=val,
                                   mask=msk, src="golden:hdc_golden+hgi_sim", rec=r["i"]))
            for ls_, e in su["fills"]:
                w = written_at.get(ls_)
                if w is not None and l0 + e < w:
                    ent["reasons"].append(f"raw_hazard: sector {ls_} filled at {l0 + e} < commit {w}")
            for ls_, e in su["drains"]:
                written_at[ls_] = l0 + e
            ent.update(programme=k, line0_serial=l0, compiled_commit_serial=l0 + (su["last_commit"] or 0),
                       priced_end_serial=t0 + LI.serial(r["end"]))
            ent["commit_slack_edges"] = ent["priced_end_serial"] - ent["compiled_commit_serial"]
            if note:
                ent["reasons"].append(note)
    events.sort(key=lambda x: (x["dom"], x["cyc"], x["k"]))
    return events, cfgs, t0


# ------------------------------------------------------------------------------------------------------------ snap
def run_fixture(fix, stage, ranks):
    """HGI-1 functional model over the committed-manifest fixture: VM of each rank before / after every executed
    non-CTL record + the expected.npz integrity check."""
    import hbm_generic_iface as HGI
    from hgi_sim.machine import UNITS, Die, Hbm, Machine, e4m3_table
    from hgi_sim.records import decode_program
    fix = Path(fix)
    cman = json.loads((QREC / f"fixtures/manifest_{stage}.json").read_text())
    for name, f in cman["files"].items():
        a = np.fromfile(fix / name, dtype=f["dtype"])
        if a.nbytes != f["bytes"] or sha(a.tobytes()) != f["sha256"]:
            raise SystemExit(f"fixture {name}: does not match the committed manifest")
    img = (fix / "program.hgi1").read_bytes()
    words = np.fromfile(fix / "md_qwen3_8b_d4g.u32", dtype=np.uint32)
    hbms = [Hbm() for _ in range(TP)]
    for name in cman["files"]:
        if name.startswith("die") and ".hbm_" in name:
            d, rest = name.split(".hbm_")
            reg, base = rest[:-3].rsplit("_", 1)
            hbms[int(d[3:])].add(int(base, 16), np.fromfile(fix / name, dtype=np.uint8), reg)
    dies = [Die(d, hbms[d]) for d in range(TP)]
    M = Machine(dies, UNITS)
    err = M.cfg_commit([int(w) for w in words])
    if err:
        raise SystemExit(f"CFG commit refused: {HGI.ERR[err]}")
    if (fix / "x_in.f32").exists() and cman.get("layers"):
        x = np.fromfile(fix / "x_in.f32", dtype=np.uint32)
        for d in dies:
            d.vm[cman["vm_map_words"]["X"]:cman["vm_map_words"]["X"] + x.size] = x
    elif (fix / "x_in.f32").exists():
        x = np.fromfile(fix / "x_in.f32", dtype=np.uint32)
        for d in dies:
            d.vm[0:x.size] = x
    pre = {r: {} for r in ranks}
    post = {r: {} for r in ranks}
    last = {r: dies[r].vm.copy() for r in ranks}
    seq, streams = [], {r: [] for r in ranks}

    def hook(Mm, rec, L):
        j = len(seq)
        seq.append((rec.unit, rec.op, L))
        for r in ranks:
            pre[r][j] = last[r]
            last[r] = dies[r].vm.copy()
            post[r][j] = last[r]
            for v in dies[r].stream_seen.values():   # head: logits leave the SU on a STREAM, not into the VM
                streams[r].append(np.ascontiguousarray(v).view(np.uint32).reshape(-1).copy())
    tok, _ = M.run(img, 0, cman["position"], hash_bufs=False, hook=hook)
    # integrity: every expected array of ranks R occurs bit-exactly in the run, in the form qwen_d4g_proof checks it:
    #   VM (any word offset of some post-record VM; qknorm.k sits at QN + nq*HD, act at ACT + rank part), the SU STREAM
    #   (head logits), the die's HBM KV plane decoded through the E4M3 table (kv_append.K<h>/V<h>, FP8 rows at POS),
    #   or SC * attn_scale (attention_qk.scores*scale: the proof's derived view; SC rows of P = POS+1 per q head).
    exp = np.load(fix / "expected.npz")
    vmw = cman["vm_map_words"]
    tab = np.asarray(e4m3_table(), np.float32).view(np.uint32)
    hd, scale = 128, np.float32(1.0 / 128 ** 0.5)          # qwen_compiler md attn_scale = f32(1/sqrt(head_dim))

    def in_vm(v, e):
        pos_ = np.nonzero(v[:v.size - e.size + 1] == e[0])[0]
        return any(np.array_equal(v[p:p + e.size], e) for p in pos_)

    found, missing, where = 0, [], {}
    for key in exp.files:
        dk = key.split(".")[0]
        if not dk.startswith("d") or not dk[1:].isdigit() or int(dk[1:]) not in ranks:
            continue
        r = int(dk[1:])
        e = np.ascontiguousarray(exp[key]).view(np.uint32).reshape(-1)
        how = None
        if any(in_vm(v, e) for v in post[r].values()):
            how = "vm"
        elif any(np.array_equal(v, e) for v in streams[r]):
            how = "stream"
        elif ".kv_append." in key:
            kind, h = "KV".index(key.rsplit(".", 1)[1][0]), int(key.rsplit(".", 1)[1][1:])
            nl = max(1, len(cman.get("layers") or []))
            for b, d8, n in dies[r].hbm.regions:
                if n != "KV":
                    continue
                plane, layer_b = 8192 * hd, d8.size // nl            # Geometry.kv_plane (ctx 8192, FP8), kv_layer
                for j in range(nl):
                    o = j * layer_b + (h * 2 + kind) * plane + POS * hd
                    if o + hd <= d8.size and np.array_equal(tab[d8[o:o + hd]], e):
                        how = "hbm_kv_e4m3"
                        break
        elif key.endswith("attention_qk.scores*scale"):
            P = cman["position"] + 1
            nq = e.size // P
            ctx = (vmw["E"] - vmw["SC"]) // max(nq, 1)
            from hgi_sim import lib as A
            for v in post[r].values():
                sc = np.stack([v[vmw["SC"] + jj * ctx: vmw["SC"] + jj * ctx + P] for jj in range(nq)]).view(np.float32)
                if np.array_equal(np.asarray(A.mul(sc, scale), np.float32).view(np.uint32).reshape(-1), e):
                    how = "vm_sc_times_attn_scale"
                    break
        where[key] = how
        found += how is not None
        if how is None:
            missing.append(key)
    return img, seq, pre, post, dict(token=int(tok), expected_found=found, expected_missing=missing,
                                     expected_checked=found + len(missing), found_as=where)


def cmd_snap(a):
    ranks = [int(x) for x in a.ranks.split(",")]
    img, seq, pre, post, integ = run_fixture(a.fix, a.stage, ranks)
    programme(a.stage, prog=Path(a.fix) / "program.hgi1")
    summary = dict(stage=a.stage, ranks=ranks, executed=len(seq), integrity=integ, ranks_out={})
    store = {}
    for r in ranks:
        disp, _ = dispatches(img, r, vm={i: int(v) for i, v in enumerate(post[r][len(seq) - 1]) if v})
        disp_raw = {}
        import su_bench as SB
        for j, (k, rec, d, L) in enumerate(disp):
            if (rec.unit, rec.op, L) != seq[j]:
                raise SystemExit(f"Ref dispatch {j} {rec.unit}.{rec.op} L{L} != functional model {seq[j]}")
            disp_raw[j] = f"{SB.pack_rec(d):x}"
        vm = FullVM(pre[r], post[r])
        man, rep = compile_rank(a.stage, r, vm, a.out / a.stage / f"r{r}", boundary=a.boundary,
                                variant=a.variant, img=(img, Path(a.fix) / "program.hgi1"), disp_raw=disp_raw)
        for j, (sp, so) in vm.touched.items():
            sp, so = sorted(sp), sorted(so)
            store[f"pre_r{r}_j{j}"] = np.array([sp, [int(pre[r][j][x]) for x in sp]], dtype=np.int64)
            store[f"post_r{r}_j{j}"] = np.array([so, [int(post[r][j][x]) for x in so]], dtype=np.int64)
        (a.out / a.stage / f"r{r}" / "dispatch_raw.json").write_text(json.dumps(disp_raw) + "\n")
        summary["ranks_out"][r] = dict(counts=man["counts"], events=len(rep["events"]),
                                       replay_sha256=sha((a.out / a.stage / f"r{r}" / "replay.json").read_bytes()))
    np.savez_compressed(a.out / f"operands_{a.stage}.npz", **store)
    summary["operands_sha256"] = sha((a.out / f"operands_{a.stage}.npz").read_bytes())
    (a.out / f"snap_{a.stage}.json").write_text(json.dumps(summary, indent=1) + "\n")
    print("QWEN_LAYER_IMAGES", json.dumps(summary))


def cmd_emit(a):
    out = {}
    for r in [int(x) for x in a.ranks.split(",")]:
        draw = None
        dr = a.operands.parent / a.stage / f"r{r}" / "dispatch_raw.json"
        if dr.exists():
            draw = {int(k): v for k, v in json.loads(dr.read_text()).items()}
        man, rep = compile_rank(a.stage, r, SparseVM(a.operands, r), a.out / a.stage / f"r{r}",
                                boundary=a.boundary, variant=a.variant, disp_raw=draw)
        out[r] = dict(counts=man["counts"], events=len(rep["events"]),
                      replay_sha256=sha((a.out / a.stage / f"r{r}" / "replay.json").read_bytes()))
    print("QWEN_LAYER_IMAGES", json.dumps(dict(stage=a.stage, ranks_out=out)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("snap", "emit"):
        p = sub.add_parser(n)
        p.add_argument("--stage", choices=STAGES, required=True)
        p.add_argument("--ranks", default="0,5")
        p.add_argument("--variant", default="landed", choices=["landed", "base"])
        p.add_argument("--boundary", type=Path, default=BOUNDARY)
        p.add_argument("--out", type=Path, required=True)
        if n == "snap":
            p.add_argument("--fix", type=Path, required=True, help="fixture dir of the stage (program.hgi1, die*.u8...)")
        else:
            p.add_argument("--operands", type=Path, required=True)
    a = ap.parse_args()
    cmd_snap(a) if a.cmd == "snap" else cmd_emit(a)


if __name__ == "__main__":
    main()
