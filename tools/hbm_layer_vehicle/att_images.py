#!/usr/bin/env python3
"""VEH-ATT (10-19): ATT.QK / ATT.PV lowering for the d4g HBM die vehicle, from the REAL layer fixture (no random records).

Input: the attention operands captured at the unit call of the bit-exact native DeepSeek programme
(ds_att_kv.py -> att_kv.json / att_kv.npz: q, the K=V rows the unit consumes in its order -- the window ring oldest first,
then the selected compressed rows -- the probabilities p and the unit outputs).

d4g placement (tools/hgi_sim/d4g_quadrant_1017.py class W2: "token blocks of the head are dealt to the 16 SMs"; GEN2b
die.v: 16 x ot_hbm_accel_smh_attn = sm_SW0..7 (south stack) + sm_NW0..7 (north stack), SM j -> j < 8 ? sm_SW<j> :
sm_NW<j-8>):  the record's T rows are dealt in ALIGNED POWER-OF-TWO CHUNK RUNS (chunk = 8 rows, the golden's csum8
leaf): nrun = the smallest power of two with ceil(nchunks / nrun) <= 16, SM s owns rows [8 nrun s, 8 nrun (s+1)).  The
same split serves QK and PV (DS shares K and V: one KV line placement, no duplicate store); a run never mixes the SM-KV8
(window) and SM-KV4 (compressed) formats (asserted).  PV node of SM s = pairwise over its run's chunk sums (padded to
nrun) == the golden's subtree; the cross-SM reduce = pairwise over the SM nodes padded to 16 (golden order) -- that merge
runs outside the SM (SU / COLL; NOT in this lowering, stated in the output).

KV line format = the SM converter's (tools/hbm_sm_attention/sm_attn_bench.py canon_row: KV8 528 B = 512 E4M3 codes + 16
UE8M0; KV4 288 B = 256 B E2M1 nibbles + 32 E4M3 scales), 136-B lines; every encoded row is checked to decode to the
fixture's K row bit for bit (canonical zero), so the SM sees exactly the golden's operand.

Subcommands
  plan     --kv DIR --layer L --out J            per-SM ops + line / byte / programme-word budget (svg W135 / xc W173)
  unit     --kv DIR --layer L --work W --out J   [--sms 0,1,..] [--dmut N] [--smut early] [--bundle B]
           compiles each SM's QK and PV calendar with the SM-element compiler (sm_elem_bench.compile_op, measured
           latencies) and plays it on the REAL die master of the SM (ot_hbm_accel_smh_attn with the die's master file list
           and defines from the GEN2b bundle views.json) in tb_hbm_smh_attn; checks every score / node bit for bit against
           the fixture and composes the cross-SM PV merge against the fixture PV output.  Verilator 5.050, fleet only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools" / "hbm_sm_attention"))
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402
import sm_attn_bench as B  # noqa: E402
import sm_elem_bench as E  # noqa: E402

F = np.float32
NSM = 16
SM_NAMES = [f"sm_SW{j}" for j in range(8)] + [f"sm_NW{j}" for j in range(8)]
SVG_W, XC_W, PROG_WORDS = 135, 173, 1024
DIE_DEFINES = ["OT_SMH_FC_HIER", "OT_SMH_HIER", "OT_SMH_XLK", "OT_FP_DATA_NORST", "OT_SMH_DRST0", "OT_SMH_RSTRELAY"]


def zb(a):
    return B.zbits(np.asarray(a, dtype=F))


def bf16_exact(a):
    a = np.asarray(a, dtype=F)
    return not (a.view(np.uint32) & 0xFFFF).any()


# ------------------------------------------------------------------------------------------------ fixture -> record
def kv8_encode(k):
    """KV8 codes of a fixture window row k (already qdq_fp8 in the golden); decode must equal k bit for bit."""
    codes, ue, _deq = B.kv8_row(k)
    dec = np.array([B._dec8(c) * 2.0 ** (int(ue[i // 32]) - 127) for i, c in enumerate(codes)], dtype=np.float64)
    if not np.array_equal(zb(dec.astype(F)), zb(k)):
        raise SystemExit("KV8: encoded window row does not decode to the fixture row")
    return codes, ue, np.asarray(k, F)


def kv4_encode(k):
    codes, sc, _deq = B.kv4_row(k)
    dec = np.array([(-1 if c & 8 else 1) * B.E2M1[c & 7] * B._dec8(sc[i // 16]) for i, c in enumerate(codes)])
    if not np.array_equal(zb(dec.astype(F)), zb(k)):
        raise SystemExit("KV4: encoded compressed row does not decode to the fixture row")
    return codes, sc, np.asarray(k, F)


def load_ds(kv_dir: Path, layer: int, rank=0):
    d = kv_dir / f"L{layer:02d}"
    meta = json.loads((d / "att_kv.json").read_text())
    z = np.load(d / "att_kv.npz")
    recs = {(r["op"], r["occ"]): r for r in meta["records"] if r["rank"] == rank}
    qk, pv = recs[("ATT.QK", 0)], recs[("ATT.PV", 0)]
    g = lambda r, n: z[r["arrays"][n]["key"]]  # noqa: E731
    q, K, s = g(qk, "A")[0], g(qk, "K"), g(qk, "O")[0]
    p, K2, o = g(pv, "A")[0], g(pv, "K"), g(pv, "O")[0]
    if not np.array_equal(K.view(np.uint32), K2.view(np.uint32)):
        raise SystemExit("QK and PV rows differ (DS shares K and V)")
    if not bf16_exact(q) or not bf16_exact(p):
        raise SystemExit("q / p not BF16-exact: the SM x path carries BF16")
    T8 = qk["ring"]["n"]
    T4 = qk["c_rows"]
    assert K.shape == (T8 + T4, 512), (K.shape, T8, T4)
    rows8 = [kv8_encode(K[i]) for i in range(T8)]
    rows4 = [kv4_encode(K[T8 + i]) for i in range(T4)]
    rec = dict(q=np.asarray(q, F), rows8=rows8, rows4=rows4, K=np.asarray(K, F), s=np.asarray(s, F),
               p=np.asarray(p, F), pv=np.asarray(o, F))
    # the fixture's own outputs are the golden (re-checked here with the shipped arithmetic)
    if not np.array_equal(zb(B.A.att_qk(rec["q"], rec["K"])), zb(rec["s"])):
        raise SystemExit("att_qk(q, K) != fixture scores")
    if not np.array_equal(zb(B.A.att_pv(rec["p"], rec["K"])), zb(rec["pv"])):
        raise SystemExit("att_pv(p, K) != fixture PV")
    src = dict(att_kv_json=str(d / "att_kv.json"), npz_sha256=meta["npz_sha256"], layer=layer, rank=rank,
               qk_priced=qk.get("priced"), pv_priced=pv.get("priced"), ring=qk["ring"], c_rows=T4)
    return rec, src


def plan_d4g(rec, sub=0):
    """per-SM ops [(name, kind, kv4, rows, nrun, sm_index, k)] for the d4g 16-SM W2 split (module doc).

    sub (HBM-ATTGAP 10-19): rows per SUB-RUN (a multiple of 8 dividing the SM's 8 x nrun rows; 0 = one op per SM).  An
    SM then runs its QK and its PV as consecutive sub-runs of `sub` rows (k = 0, 1, ..): every sub-run of a kind has the
    SAME calendar (a canonical line stream from a block start, relative tags/rows; results placed by the smw writer
    table), so ONE resident copy of the QK and of the PV programme serves all of them (programme SRAM 1,024 words).  A
    PV sub-run publishes the node of its sub/8 chunks: an aligned golden subtree, so the cross-SM merge runs over
    sub-run nodes in position order padded to next_pow2(chunks) / (sub/8) -- the golden tree."""
    T8, T = len(rec["rows8"]), len(rec["K"])
    nch = -(-T // 8)
    nrun = 1
    while -(-nch // nrun) > NSM:
        nrun *= 2
    ops = []
    for s in range(-(-nch // nrun)):
        r0, r1 = 8 * nrun * s, min(T, 8 * nrun * (s + 1))
        kv4 = 1 if r0 >= T8 else 0
        if not all((r >= T8) == bool(kv4) for r in range(r0, r1)):
            raise SystemExit(f"SM {s}: run [{r0},{r1}) mixes SM-KV8 and SM-KV4 rows")
        rows = list(range(r0, r1))
        if not sub:
            ops.append((f"qk_{SM_NAMES[s]}", "qk", kv4, rows, 0, s, 0))
            ops.append((f"pv_{SM_NAMES[s]}", "pv", kv4, rows, nrun, s, 0))
            continue
        if sub % 8 or (8 * nrun) % sub:
            raise SystemExit(f"sub-run {sub} rows must be a multiple of 8 dividing {8 * nrun}")
        parts = [rows[i:i + sub] for i in range(0, len(rows), sub)]
        for k, pr in enumerate(parts):
            ops.append((f"qk_{SM_NAMES[s]}_k{k}", "qk", kv4, pr, 0, s, k))
        for k, pr in enumerate(parts):
            ops.append((f"pv_{SM_NAMES[s]}_k{k}", "pv", kv4, pr, sub // 8, s, k))
    return ops, nrun


def merge_pad(rec, ops):
    """golden pad of the cross-SM merge: next_pow2(chunks) / (chunks a PV node)."""
    nch = -(-len(rec["K"]) // 8)
    p2 = 1 << (nch - 1).bit_length()
    per = len(next(o for o in ops if o[1] == "pv")[3]) // 8
    return p2 // per


def programme_residency(rec, ops, lat):
    """per SM: the calendar words of each kind's sub-runs; resident = one copy per kind when all sub-runs of the kind are
    word-identical (cmd, KV_DESC); returns {sm: dict(qk_words, pv_words, identical, resident_words, fits)}."""
    out = {}
    for s in sorted({o[5] for o in ops}):
        e = dict()
        for kind in ("qk", "pv"):
            seqs = []
            for o in ops:
                if o[5] != s or o[1] != kind:
                    continue
                cal, exp = E.compile_op(rec, o[:5], lat, kind == "pv")
                first = min([c for c, f in enumerate(cal.cyc) if f] + list(cal.kvd) + list(cal.pkt))
                seqs.append([(E.cmd_word(**(cal.cyc[c] if c < len(cal.cyc) else {})), cal.kvd.get(c, 0))
                             for c in range(first, exp["end"] + 1)])
            e[f"{kind}_words"] = len(seqs[0])
            e[f"{kind}_subruns"] = len(seqs)
            e[f"{kind}_identical"] = all(q == seqs[0] for q in seqs)
        e["resident_words"] = e["qk_words"] + e["pv_words"]
        e["fits_1024_word_programme"] = e["resident_words"] <= PROG_WORDS and e["qk_identical"] and e["pv_identical"]
        out[SM_NAMES[s]] = e
    return out


def op_lines(rec, rows):
    T8 = len(rec["rows8"])
    blob = b""
    for r in rows:
        codes, sc, _ = rec["rows4"][r - T8] if r >= T8 else rec["rows8"][r]
        blob += B.canon_row(codes, sc, 1 if r >= T8 else 0)
    return B.stream_lines(blob)


def budget(rec, ops, lat):
    """programme-word / line / byte budget of every op (the svg W135 and xc W173 calendars are one word per edge from
    the op's first command word to its last result word; 1,024-word programme SRAM per target, resident)."""
    out = []
    for op in ops:
        cal, exp = E.compile_op(rec, op, lat, op[1] == "pv")
        first = min([c for c, f in enumerate(cal.cyc) if f] + list(cal.kvd) + list(cal.pkt))
        lines = op_lines(rec, op[3])
        out.append(dict(name=op[0], sm=SM_NAMES[op[5]], kind=op[1], kv4=op[2], rows=len(op[3]), lines=len(lines),
                        hbm_bytes=136 * len(lines), svg_blocks=-(-len(lines) // 64),
                        x_beats=len(cal.xw), words=exp["end"] + 1 - first, first_word=first, end=exp["end"],
                        first_line=exp["first_line"], last_consume=exp["last_consume"]))
    return out


# ------------------------------------------------------------------------------------------------ unit pre-check
def die_sources(bundle: Path):
    mf = json.loads((bundle / "master_files.json").read_text())
    return [bundle / p for p in mf["ot_hbm_accel_smh_attn"]]


def build_unit(work: Path, bundle: Path, tb: Path, dmut: int, probe: bool):
    obj = work / f"obj_d{dmut}_p{int(probe)}"
    exe = obj / "Vtb_hbm_smh_attn"
    if exe.exists():
        return exe
    vl = os.environ.get("VERILATOR") or os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
    cmd = [vl, "--binary", "-j", os.environ.get("VL_JOBS", "16"), "-O1", "-CFLAGS", "-O1", "--x-assign", "fast",
           "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--unroll-count", "256",
           "--top-module", "tb_hbm_smh_attn", f"-GDMUT={dmut}", "--Mdir", str(obj)] + \
          [f"-D{d}" for d in DIE_DEFINES] + (["-DPROBE"] if probe else []) + \
          [f"-I{bundle / p}" for p in sorted({str(Path(s).parent.relative_to(bundle)) for s in die_sources(bundle)})] + \
          [str(s) for s in die_sources(bundle)] + [str(tb)]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (work / f"build_d{dmut}_p{int(probe)}.log").write_text(" ".join(cmd) + "\n" + r.stdout + r.stderr +
                                                          f"\nBUILD_RC {r.returncode} wall {time.time() - t0:.0f} s\n")
    if r.returncode != 0:
        raise SystemExit(f"build failed (see {work}/build_d{dmut}_p{int(probe)}.log)")
    return exe


def pv_merge(nodes, pad=NSM):
    """cross-SM reduce of the SM (sub-run) nodes in golden order: pairwise over the nodes padded to `pad` (zeros)."""
    return B.A.pairwise([np.asarray(n, F) for n in nodes] + [np.zeros(512, F)] * (pad - len(nodes)))


def node_from_words(words):
    got = np.full(512, -1, dtype=np.int64)
    for _cyc, rrow, data in words:
        lr, wd = rrow >> 4, rrow & 15
        for col in range(8):
            got[8 * (16 * lr + wd) + col] = (data >> (32 * col)) & 0xFFFFFFFF
    return got


def cmd_unit(a):
    rec, src = load_ds(Path(a.kv), a.layer)
    ops, nrun = plan_d4g(rec, a.subrun)
    allops = list(ops)
    if a.sms:
        want = {int(x) for x in a.sms.split(",")}
        ops = [o for o in ops if o[5] in want]
    if a.kinds:
        ops = [o for o in ops if o[1] in a.kinds.split(",")]
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    lat = dict(E.DEFAULT_LAT)
    if a.lat:
        lat.update(json.loads(a.lat))
    exe = build_unit(work, Path(a.bundle).resolve(), ROOT / "rtl/test/hbm_accel/sm_attn/tb_hbm_smh_attn.sv", a.dmut,
                     a.probe)
    results, nodes = [], {}
    t0 = time.time()
    for op in ops:
        cal, exp = E.compile_op(rec, op[:5], lat, op[1] == "pv", smut=a.smut)
        d = work / f"L{a.layer:02d}_{op[0]}_d{a.dmut}{('_' + a.smut) if a.smut else ''}{('_s%d' % a.subrun) if a.subrun else ''}"
        d.mkdir(exist_ok=True)
        n = exp["end"] + 4
        if n > 4096:
            raise SystemExit(f"{op[0]}: calendar {n} > tb MAXC 4096")
        cal.write(d, n)
        r = subprocess.run([str(exe), f"+CMD={d}/cmd.hex", f"+PKT={d}/pkt.hex", f"+XW={d}/xw.hex", f"+KVD={d}/kvd.hex",
                            f"+N={n}"], capture_output=True, text=True, timeout=7200)
        out = r.stdout + r.stderr
        (d / "run.log").write_text(out)
        res = dict(name=op[0], sm=SM_NAMES[op[5]], subrun=op[6], kind=op[1], kv4=op[2], rows=len(op[3]), rc=r.returncode,
                   fault=("FAULT" in out), calendar=exp)
        res.update(E.check(rec, op[:5], exp, out))
        res["pass"] = r.returncode == 0 and not res["fault"] and res["mismatches"] == 0 and \
            res["results"] == res["expected"]
        if res["first_result"] is not None:
            res["span_first_line_to_last_result"] = res["last_result"] - exp["first_line"]
            res["span_first_word_to_last_result"] = res["last_result"] - min(
                [c for c, f in enumerate(cal.cyc) if f] + list(cal.kvd) + list(cal.pkt))
        if op[1] == "pv" and res["pass"]:
            words = [(int(x[1]), int(x[2], 16), int(x[3], 16)) for x in (ln.split() for ln in out.splitlines()
                                                                        if ln.startswith("R "))]
            nodes[(op[5], op[6])] = node_from_words(words).astype(np.uint32).view(F)
        results.append(res)
        print(("PASS " if res["pass"] else "FAIL ") + json.dumps({k: v for k, v in res.items() if k != "calendar"}),
              flush=True)
    merged = None
    keys = sorted({(o[5], o[6]) for o in allops if o[1] == "pv"})
    if all(k in nodes for k in keys):
        pad = merge_pad(rec, allops)
        m = pv_merge([nodes[k] for k in keys], pad)
        merged = dict(nodes=len(keys), pad=pad, equals_fixture_pv=bool(np.array_equal(zb(m), zb(rec["pv"]))),
                      mismatches=int(np.sum(zb(m) != zb(rec["pv"]))))
        # the RTL nodes in position order: input of the on-die merge bench (att_merge_su.py)
        np.savez(Path(a.out).with_suffix(".nodes.npz"), nodes=np.stack([nodes[k] for k in keys]).view(np.uint32),
                 keys=np.array(keys), pad=pad, fixture_pv=np.asarray(rec["pv"], F).view(np.uint32))
    residency = programme_residency(rec, allops, lat) if a.subrun else None
    spans = {}
    for r in results:
        if r.get("span_first_word_to_last_result") is not None:
            e = spans.setdefault(r["sm"], {}).setdefault(r["kind"], [])
            e.append(r["span_first_word_to_last_result"])
    if residency and not a.sms and not a.kinds and not all(e["fits_1024_word_programme"] for e in residency.values()):
        results.append({"name": "programme_residency", "pass": False})
    summ = dict(layer=a.layer, ops=len(results), passed=sum(bool(r.get("pass")) for r in results), dmut=a.dmut, smut=a.smut,
                nrun=nrun, subrun=a.subrun, lat=lat, source=src, cross_sm_merge=merged, programme_residency=residency,
                spans_first_word_to_last_result=spans,
                cross_sm_merge_scope="pairwise over the SM (sub-run) nodes padded to the golden pad, composed in Python "
                                     "here; the on-die merge (SU lane-store tree + COLL ring all-gather) is benched by "
                                     "att_merge_su.py on these RTL nodes (<out>.nodes.npz)",
                rtl="ot_hbm_accel_smh_attn die master (GEN2b bundle master_files.json + views.json defines "
                    + ",".join(DIE_DEFINES) + ") in tb_hbm_smh_attn", wall_s=round(time.time() - t0, 1),
                verdict="PASS" if results and all(r.get("pass") for r in results) else "FAIL")
    Path(a.out).write_text(json.dumps(dict(summary=summ, ops=results), indent=1, default=int))
    print(("PASS" if summ["verdict"] == "PASS" else "FAIL") + " HBM_VEH_ATT_UNIT " +
          json.dumps({k: v for k, v in summ.items() if k != "source"}, default=int))
    return 0 if summ["verdict"] == "PASS" else 1


def cmd_plan(a):
    rec, src = load_ds(Path(a.kv), a.layer)
    ops, nrun = plan_d4g(rec, a.subrun)
    b = budget(rec, ops, dict(E.DEFAULT_LAT))
    per_sm = {}
    for x in b:
        e = per_sm.setdefault(x["sm"], dict(words=0, lines=0, hbm_bytes=0, svg_blocks=0))
        for k in ("words", "lines", "hbm_bytes", "svg_blocks"):
            e[k] += x[k]
    # host-CP cost of (re)installing a programme / descriptor through the ingress (layer_images.CpBus: one 256-b row =
    # 8 AXI writes x 5 edges = CP_FRAME_EDGES; svg and xc each hold their own copy of programme rows and descriptors)
    sys.path.insert(0, str(HERE))
    import layer_images as LI  # noqa: E402
    res = programme_residency(rec, ops, dict(E.DEFAULT_LAT)) if a.subrun else None
    for sm, e in per_sm.items():
        if res:      # sub-runs: one resident copy per kind (word-identical calendars), not the sum over sub-runs
            e["words_issued"] = e["words"]
            e["words"] = res[sm]["resident_words"]
        e["fits_1024_word_programme"] = e["words"] <= PROG_WORDS
        e["install_edges_svg_plus_xc"] = 2 * e["words"] * LI.CP_FRAME_EDGES
        e["descriptor_rows_svg_plus_xc"] = 2 * e["svg_blocks"]
        e["descriptor_install_edges"] = 2 * e["svg_blocks"] * LI.CP_FRAME_EDGES
    tot = dict(programme_install_edges_all_sms=sum(e["install_edges_svg_plus_xc"] for e in per_sm.values()),
               descriptor_install_edges_all_sms=sum(e["descriptor_install_edges"] for e in per_sm.values()),
               note="one ingress bus (host_cp_ingress) serves every target: programme rows must be RESIDENT (installed "
                    "once); anything that changes per token (window-ring rotation -> KV block bases in the issuer "
                    "descriptors) is a per-token descriptor rewrite at CP_FRAME_EDGES per row unless the base is "
                    "relocated in hardware")
    doc = dict(schema="opentallas.hbm_vehicle_att_plan.v1", lane="VEH-ATT", source=src, sms=NSM, nrun=nrun,
               rows=len(rec["K"]), window_rows=len(rec["rows8"]), compressed_rows=len(rec["rows4"]),
               placement="d4g W2: aligned chunk runs of 8 x nrun rows on SM s (sm_SW0..7, sm_NW0..7); same split QK/PV",
               ops=b, per_sm=per_sm, host_cp=tot, svg_word_bits=SVG_W, xc_word_bits=XC_W, programme_words=PROG_WORDS,
               subrun=a.subrun, programme_residency=res)
    Path(a.out).write_text(json.dumps(doc, indent=1, default=int) + "\n")
    print(json.dumps(dict(nrun=nrun, sms=len(per_sm), per_sm=per_sm), default=int))
    return 0


# ------------------------------------------------------------------------------------------------ HBM KV image
BLOCK_LINES = 64           # svg block = 64 136-B lines (descriptor rows 7 b; budget() svg_blocks)
KV_ROW0 = 0x4000           # explicit KV allocation: DRAM row KV_ROW0 + block on the SM's own four PCs (weights stay low)


def kv_image(rec, ops, row0=KV_ROW0):
    """HBM image of the KV lines of every in-slice SM (sm_SW0..7 -> svg_SW<k> id_sm k -> phy_SW PCs 4k..4k+3).

    Address law = ot_hbm_svc_prefetch_overlap_owner_id (k_addr) = tools/hbm_svc_packed136_image.sector_address: logical
    sector o of a block -> lane o&3 (PC pcs[lane]), t = o>>2, bank {t[9:7], t[1:0]}, col t[6:2], row = row_base; 136-B
    lines packed contiguously per block (w19_payload_loader.compact_sectors: little-endian 32-B sectors, last padded),
    total = ceil(rows*136/128)*4 sectors (issuer rule).  QK and PV of an SM read the SAME blocks (DS K = V).
    HBM-ROTLAYOUT (owner rule 10-19): KV blocks are SLOT-PACKED -- block b at block address row0*8 + b, i.e. DRAM row
    row0 + b // 8 on bank set b % 8 (descriptor base[9:7] = set, rel owner t[9:7] | slot), so consecutive KV blocks
    rotate over the eight bank sets; the stream is refused by hbm_bank_layout.check_stream unless rotated."""
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from hbm_svc_packed136_image import sector_address, sector_pc  # noqa: E402
    import hbm_bank_layout as BL  # noqa: E402
    sms = sorted({o[5] for o in ops})
    hexlines, blocks, seen = [], [], set()
    for s in sms:
        rows = next(o[3] for o in ops if o[5] == s and o[1] == "qk")
        if s >= 8:
            blocks.append(dict(sm=SM_NAMES[s], in_slice=False, rows=len(rows),
                               note="sm_NW* is outside the SW slice: its QK scores / PV node are replayed at the boundary"))
            continue
        lines = op_lines(rec, rows)
        alloc = dict(pcs=[4 * s + k for k in range(4)], row_base=0, stack_bytes=1 << 35)
        nblk = -(-len(lines) // BLOCK_LINES)
        addrs = BL.packed(row0 * 8, nblk)
        BL.check_addrs("kv", addrs, [BL.words(min(BLOCK_LINES, len(lines) - BLOCK_LINES * b)) for b in range(nblk)],
                       f"{SM_NAMES[s]} KV")
        for b in range(nblk):
            blk = lines[BLOCK_LINES * b:BLOCK_LINES * (b + 1)]
            raw = b"".join(x.to_bytes(136, "little") for x in blk)
            total = ((len(blk) * 136 + 127) // 128) * 4
            raw += bytes(32 * total - len(raw))
            row, bset = BL.split(addrs[b])
            alloc["row_base"] = row
            secs = []
            for o in range(total):
                sa = sector_address(o + 512 * bset, alloc)
                if sa in seen:
                    raise SystemExit(f"KV image alias at sector {sa:#x}")
                seen.add(sa)
                assert sector_pc(sa) == alloc["pcs"][o & 3]
                hexlines.append(f"{sa:08x} {int.from_bytes(raw[32 * o:32 * o + 32], 'little'):064x}")
                secs.append(sa)
            blocks.append(dict(sm=SM_NAMES[s], in_slice=True, block=b, lines=len(blk), rows_field=len(blk),
                               total_sectors=total, pcs=list(alloc["pcs"]), row_base=row, bank_set=bset,
                               block_address=addrs[b],
                               first_sector=secs[0], last_sector=secs[-1],
                               bytes_sha256=hashlib.sha256(raw).hexdigest()))
    return hexlines, blocks


def image_readback(hexlines, blocks):
    """inverse of kv_image: rebuild every in-slice block's line stream from the hex image (the check that the image
    holds exactly the lines the unit pre-check feeds the SM)."""
    sys.path.insert(0, str(ROOT / "tools"))
    from hbm_svc_packed136_image import sector_address  # noqa: E402
    mem = {int(a, 16): int(d, 16) for a, d in (ln.split() for ln in hexlines)}
    out = {}
    for b in blocks:
        if not b["in_slice"]:
            continue
        alloc = dict(pcs=b["pcs"], row_base=b["row_base"], stack_bytes=1 << 35)
        raw = b"".join(mem[sector_address(o + 512 * b.get("bank_set", 0), alloc)].to_bytes(32, "little")
                       for o in range(b["total_sectors"]))
        out.setdefault(b["sm"], []).extend(int.from_bytes(raw[136 * i:136 * i + 136], "little")
                                           for i in range(b["lines"]))
    return out


def cmd_image(a):
    rec, src = load_ds(Path(a.kv), a.layer)
    ops, nrun = plan_d4g(rec)
    hexlines, blocks = kv_image(rec, ops)
    back = image_readback(hexlines, blocks)
    for s in sorted({o[5] for o in ops if o[5] < 8}):
        rows = next(o[3] for o in ops if o[5] == s and o[1] == "qk")
        if back[SM_NAMES[s]] != op_lines(rec, rows):
            raise SystemExit(f"{SM_NAMES[s]}: image readback != SM line stream")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "phy_SW.hex").write_text("\n".join(hexlines) + "\n")
    doc = dict(schema="opentallas.hbm_vehicle_att_kv_image.v1", lane="VEH-ATT2", source=src, nrun=nrun,
               file="phy_SW.hex (+HBM_IMG_DIR: ot_hbm3e_phy_rc_e8p5 DRAM model, lines '<sector30 hex> <256-b hex>')",
               phy_hex_sha256=hashlib.sha256((out / "phy_SW.hex").read_bytes()).hexdigest(), sectors=len(hexlines),
               allocation=dict(row0=KV_ROW0, block_lines=BLOCK_LINES,
                               law="svg_SW<k> (id_sm k) PCs 4k..4k+3; block b at block address KV_ROW0*8+b = DRAM row "
                                   "KV_ROW0+b//8, bank set b%8 (HBM-ROTLAYOUT slot-packed); "
                                   "hbm_svc_packed136_image.sector_address == overlap_owner_id k_addr"),
               readback="every in-slice SM's image decodes to exactly the 136-B line stream of the unit pre-check "
                        "(op_lines), whose rows decode bit-exact to the fixture K rows (kv8/kv4_encode)",
               blocks=blocks,
               descriptor_note="issuer descriptor per block: rows = lines, row_base = KV_ROW0 + b//8, base[9:7] = b%8 "
                               "(bank set), pcs = the SM's own "
                               "four PCs, total = ceil(rows*136/128)*4 (sm_images.py / VEH-FMT-SM2 owns the row ABI)")
    (out / "kv_image.json").write_text(json.dumps(doc, indent=1, default=int) + "\n")
    print(f"PASS HBM_VEH_ATT_IMAGE sectors={len(hexlines)} blocks={sum(b['in_slice'] for b in blocks)} "
          f"outside_slice={sum(not b['in_slice'] for b in blocks)}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("plan", "unit", "image"):
        p = sub.add_parser(nm)
        p.add_argument("--kv", required=True, help="ds_att_kv.py output dir (contains L<NN>/att_kv.json)")
        p.add_argument("--layer", type=int, default=2)
        p.add_argument("--out", required=True)
        p.add_argument("--subrun", type=int, default=0, help="rows per SM sub-run (HBM-ATTGAP: 32 = resident QK+PV)")
        if nm == "unit":
            p.add_argument("--work", required=True)
            p.add_argument("--bundle", required=True, help="GEN2b slice bundle (master_files.json, rtl/, physical/)")
            p.add_argument("--sms", default="")
            p.add_argument("--kinds", default="")
            p.add_argument("--dmut", type=int, default=0)
            p.add_argument("--smut", default="", choices=["", "early", "r7clear"])
            p.add_argument("--probe", action="store_true")
            p.add_argument("--lat", default="")
    a = ap.parse_args(argv)
    return {"unit": cmd_unit, "plan": cmd_plan, "image": cmd_image}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
