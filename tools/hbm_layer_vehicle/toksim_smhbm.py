#!/usr/bin/env python3
"""TOKSIM-HBM-smhbm (10-19): SM.MATVEC with its HBM weight stream on the GEN2e3 d4g die composition, cycle-accurate.

Wraps smb_unit.py (HBM-SMBUDGET compiler + checks, unchanged) and only swaps the bench and the source set:
  tb_toksim_smhbm.sv = tb_hbm_svg_rel_sm re-composed as die.v binds one SM (svg ID_COHORT 1 -> vmks_splitstrap KRL1 ->
  4 x ot_hbm_svc_pc_ctrl_leaf_cfg_h9b -> DRAM timing fixture; SM ot_hbm_accel_smh_attn ENABLE_INT8 1).
Every RTL file comes from THIS tree (branch from claude/hd4g-gen2e3-1019 9787e078a, the die source; file hashes checked
against artifacts/hdie-d4/d4g_gen2e3/synmeta_a by the lane), with simulation SRAM models.

  toksim_smhbm.py run --fix FIX --smw SMW --work W --out J --layers L14:14 --name x   (+ smb_unit env pacing knobs)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import smb_unit as S  # noqa: E402

ROOT = S.ROOT
TB = "rtl/test/hbm_accel/svg_rel/tb_toksim_smhbm.sv"
SM_FILES = """physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
rtl/dsrom_sys/s81_window_la/recovered_ctl_m2/ot_hdc_prefix.sv
rtl/gpu/ot_gpu_bd_col.sv rtl/gpu/ot_gpu_fadd.sv rtl/gpu/ot_gpu_stack.sv rtl/gpu/ot_gpu_tc_col.sv rtl/gpu/ot_gpu_tree.sv
rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv
rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_be.sv
rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_front_static.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_leafh.sv
rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_native_col.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_pstore.sv
rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_tile.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_desc_static.sv
rtl/hbm_accel/sm/attn/ot_hbm_sm_kv_line.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge.sv
rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv rtl/hbm_accel/sm/static/ot_smh_static_int8.sv
rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv rtl/hbm_accel/sm/ot_hbm_accel_smh.sv rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv
rtl/hbm_accel/sm/ot_hbm_accel_smh_gu.sv rtl/hbm_accel/sm/ot_hbm_accel_stack.sv
rtl/hbm_accel/sm/static/ot_smh_static_feed.sv rtl/hbm_accel/sm/static/ot_smh_static_front.sv
rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fpu.sv
rtl/hdc/ot_hdc_sfu.sv rtl/lib/ot_hdly.sv rtl/lib/ot_rst_relay.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_bterm2.sv""".split()
SN = "rtl/hbm_accel/loader/service_native/"
SVC_FILES = [SN + f for f in """ot_hbm_svc_async_fifo.sv ot_hbm_svc_sm8_landing_bank.sv ot_hbm_svc_static_sm_packed136.sv
ot_hbm_svc_prefetch_overlap_owner_rel_id.sv ot_hbm_svc_sm4pc_cdc_rel_id.sv ot_hbm_svc_sm_issuer_rel.sv
ot_hbm_svc_sm_feed_programmed_rel_id.sv ot_hbm_svc_sm_group_rel_id.sv ot_hbm_svc_sm_xcal_rel.sv ot_hbm_svc_sm_xcal_rel_t.sv
ot_hbm_svc_vm_kshare_splitstrap.sv ot_hbm_svc_ring_h9b.sv ot_hbm_svc_ring_h9b_ff.sv ot_hbm_svc_pin_skid2_h9.sv
ot_hbm_svc_pc_ctrl_leaf.sv ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv""".split()] + \
    ["rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv", "rtl/lib/ot_reset_sync.sv",
     "rtl/hbm_accel/sm/static/ot_smh_calendar_static_x.sv", "rtl/hbm_accel/host_static_20261015/ot_static_run_target.sv",
     "physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v",
     "physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v",
     "rtl/test/hbm_accel/svg_rel/tb_svg_rel_dram_sparse.sv"]


def build(work: Path, bundle, defines):
    tag = "_".join(d.replace("=", "") for d in defines) or "base"
    files = []
    for p in SM_FILES + SVC_FILES + [TB]:
        if p not in files:
            files.append(p)
    files = [ROOT / p for p in files]
    miss = [str(p) for p in files if not p.exists()]
    if miss:
        raise SystemExit(f"missing sources {miss}")
    import hashlib
    h = hashlib.sha256()
    for p in files:
        h.update(p.read_bytes())
    obj = work / f"obj_die_{tag}_{h.hexdigest()[:12]}"      # keyed by the RTL content, not the tool revision
    exe = obj / "Vtb_toksim_smhbm"
    if exe.exists():
        return exe
    vl = os.environ.get("VERILATOR") or os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator")
    incs = sorted({str(p.parent) for p in files})
    cmd = [vl, "--binary", "-j", os.environ.get("VL_JOBS", "16"), "-O1", "-CFLAGS", "-O1", "--x-assign", "fast",
           "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD", "-Wno-MULTIDRIVEN", "--unroll-count", "256",
           "--timing", "--top-module", "tb_toksim_smhbm", "--Mdir", str(obj)] + \
          [f"-D{d}" for d in S.MV.DIE_DEFINES + list(defines)] + [f"-I{i}" for i in incs] + [str(f) for f in files]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    (work / f"build_die_{tag}.log").write_text(" ".join(cmd) + "\n" + r.stdout[-20000:] + r.stderr[-20000:] +
                                               f"\nBUILD_RC {r.returncode} wall {time.time() - t0:.0f} s\n")
    if r.returncode != 0:
        raise SystemExit(f"build failed (see {work}/build_die_{tag}.log)")
    return exe


S.build = build
_lr = S.layer_records


def layer_records(fix, smw):
    """SMB_CENSUS_R=1: rows per SM = ceil(m / 16) (the price model's per-die placement, census bytes_B) instead of the
    fixture's d4g halves ceil(ceil(m / 2) / 16)."""
    out = _lr(fix, smw)
    if os.environ.get("SMB_CENSUS_R") == "1":
        for r in out:
            r["R"] = -(-r["m"] // 16)
    return out


S.layer_records = layer_records
for _k in ("OP_GAP", "X_GAP", "DRAIN", "BUSY"):
    if os.environ.get("SMB_" + _k):
        setattr(S, _k, int(os.environ["SMB_" + _k]))


# ------------------------------------------------------------------------------------------------ Qwen INT8 (fmt 3)
QWEN = {  # census_shapes.json qwen SM.MATVEC: tag -> (K = n, m per die); rows per SM = ceil(m / 16)
    "qkv": (4096, 1536), "o": (1024, 4096), "gu": (4096, 6144), "down": (3072, 4096), "head": (4096, 37984)}
I8_LAT = 2
QBLK = 2 * S.IL      # items per INT8 block: two group-slot waves = 128 issue slots = 64 packed 128-code lines (<= 64 rows)


def qwen_block_programme(Gn, items, r0):
    """UNROLLED (lstep 0, loops 1) INT8 block: word 2p reads packed line p (tag p) with the xc mark command[116]; the
    SM's converter (ot_smh_static_int8) delivers its two BF16 halves I8_LAT and I8_LAT + 1 edges later, where words
    j + I8_LAT carry slot j's absolute command (row / slot relative to r0, xaddr g*8+t, first t==0, last t==7, packet
    tag j // 2).  Slot order = qwen_sm_mv_unit.compile_int8 (per wave: t-major, IL items; padding slots idle but tagged).
    Retire on the last word."""
    order = []
    for wb in range(0, QBLK, S.IL):
        for t in range(S.C8):
            for s_ in range(S.IL):
                k = wb + s_
                order.append((items[k][0], items[k][1], t) if k < len(items) else None)
    nslot = len(order)
    npk = nslot // 2
    n = nslot + I8_LAT
    mark = (S.MV.cmd_word(mode=0) >> 83) | (1 << 33)
    svg, xc = [], []
    for w in range(n):
        read = (w // 2, w // 2) if (w % 2 == 0 and w // 2 < npk) else None
        j = w - I8_LAT
        c = 0
        if 0 <= j < nslot:
            it = order[j]
            if it is not None:
                r, g, t = it
                rr = r - r0
                c = S.MV.cmd_word(mode=0, valid=1, first=int(t == 0), last=int(t == S.C8 - 1), row=rr,
                                  glast=int(g == Gn - 1), slot=rr & 7, xaddr=g * S.C8 + t, pkt=1, pkt_tag=j // 2)
            else:
                c = S.MV.cmd_word(mode=0, pkt=1, pkt_tag=j // 2)
        svg.append(S.svg_word(c & ((1 << 83) - 1), read, retire=(w == n - 1)))
        xc.append((c >> 83) | (mark if read is not None else 0))
    return svg, xc, order, npk


def codes_pair(W, order, p):
    """packed line p = {codes of slot 2p+1, codes of slot 2p} (qwen_sm_mv_unit.codes_line lane order)."""
    word = 0
    for h in range(2):
        it = order[2 * p + h]
        if it is None:
            continue
        r, g, t = it
        K = W.shape[1]
        for j in range(S.MV.LF):
            k = (g * S.MV.LF + j) * S.C8 + t
            if k < K:
                word |= (int(W[r, k]) & 0xFF) << (8 * j + 512 * h)
    return word


def qwen_records(tags, seed):
    from hgi_sim import lib as A
    G, V = S.MV.G, S.MV.V
    out = []
    for i, tag in enumerate(tags):
        K, m = QWEN[tag]
        R = -(-m // 16)
        rng = np.random.default_rng(seed + i)
        W = rng.integers(-127, 128, size=(R, K), dtype=np.int64).astype(np.int8)   # SM 0's rows (busiest = all equal)
        x = G.to_bf16(rng.standard_normal(K).astype(np.float32))
        acc = np.asarray(V.csum(G.mul(W.astype(np.float32), G.to_bf16(x)[None, :])), np.float32)
        lib = np.asarray(A.sm_int8(W, x), np.float32)
        gok = bool(np.array_equal(acc.view(np.uint32), lib.view(np.uint32)))
        out.append(dict(k=i, tag=tag, K=K, m=m, R=R, W=W, x=x, acc=acc, o=acc.view(np.uint32), ofmt="FP32", gok=gok,
                        slot=None, eid=None, fmt=0, rec=dict(tag=tag, priced=None)))
    return out


def compile_qwen(tags, seed=20261019):
    from hbm_svc_packed136_image import sector_address
    import numpy as _np  # noqa: F401
    store = S.Store(S.ATT_RESERVED)
    recs = qwen_records(tags, seed)
    bad = [r["tag"] for r in recs if not r["gok"]]
    if bad:
        raise SystemExit(f"golden self-test mismatch {bad}")
    descs, mem, xw_ev, ing = [], {}, [], []
    kd = dict(name="qwen", layer=0, d0=0, ops=[], exp={}, recs=recs)
    for r in recs:
        _, Gn, xw = S.MV.pack(0, r["W"].astype(np.float32), r["x"])
        r.update(Gn=Gn, xw=xw, blocks=[])
        items = [(rr, g) for rr in range(r["R"]) for g in range(Gn)]
        for bi in range(0, len(items), QBLK):
            it = items[bi:bi + QBLK]
            r0 = it[0][0]
            svg, xc, order, npk = qwen_block_programme(Gn, it, r0)
            pb, pl = store.add(svg, xc)
            lines = [codes_pair(r["W"], order, p) for p in range(npk)]
            b = dict(k=r["k"], r0=r0, n_lines=npk, prog=(pb, pl), nwords=len(svg), lines=lines, head=bi == 0,
                     lstep=0, fmt=0, row_base=len(descs) * S.BSCALE, layer_stride=0, expert_stride=0, id_sel=0,
                     dram_row=len(descs) * S.BSCALE, desc_i=len(descs))
            r["blocks"].append(b)
            descs.append(b)
    kd["d1"] = len(descs)
    if len(descs) > S.TBL:
        raise SystemExit(f"descriptor table overflow: {len(descs)} > {S.TBL}")
    for b in descs:
        raw = b"".join(int(x).to_bytes(136, "little") for x in b["lines"])
        total = ((len(b["lines"]) * 136 + 127) // 128) * 4
        raw += bytes(32 * total - len(raw))
        alloc = dict(pcs=[0, 1, 2, 3], row_base=b["dram_row"] >> 3, stack_bytes=1 << 35)
        for o in range(total):
            sa = sector_address(o + 512 * (b["dram_row"] & 7), alloc)
            assert sa not in mem, ("HBM image alias", hex(sa))
            mem[sa] = int.from_bytes(raw[32 * o:32 * o + 32], "little")
    t = 10
    for a in range(S.ATT_RESERVED, store.top):
        for tgt, w, wd in ((S.SVG_TGT, store.svg[a], 135), (S.XC_TGT, store.xc[a], 173)):
            ing.append((t, S.ingress(cfg=((0 if a < 1024 else 2) << 10 | (a & 1023), S.prog_row(a, w, wd)), target=tgt)))
            t += 1
    desc_install_t = t
    t += 2 * len(descs)
    ops_out = []
    last_cmd_abs = t
    t_arm = max(t, last_cmd_abs + 8)
    t_launch = t_arm + 2
    rc0 = t_launch + S.OFF
    rc = S.FIRST_GO
    prev_go, prev_len, prev_lines = None, 0, 0
    cur_abs = last_cmd_abs
    epoch = 1
    for r in recs:
        nx = len(r["xw"]) * S.MV.NBEAT
        x0 = max(cur_abs + 32, desc_install_t + 2 * len(descs) + 4)
        x_end = x0 + nx
        for a, word in enumerate(r["xw"]):
            for g in range(S.MV.NBEAT):
                xw_ev.append((x0 + a * S.MV.NBEAT + g, (1 << 2062) | (a << 2055) | (g << 2048) |
                              ((word >> (2048 * g)) & ((1 << 2048) - 1))))
        op = dict(layer="qwen", k=r["k"], tag=r["tag"], fmt="INT8", O_fmt="FP32", m=r["m"], K=r["K"], R=r["R"],
                  Gn=r["Gn"], slot=None, eid=None, blocks=len(r["blocks"]), lines=sum(b["n_lines"] for b in r["blocks"]),
                  bytes_hbm=sum(b["n_lines"] for b in r["blocks"]) * 136, bytes_int8=r["R"] * r["K"], priced=None)
        for bi, b in enumerate(r["blocks"]):
            lo = rc
            if prev_go is not None:
                lo = max(lo, prev_go + prev_len + S.BUSY,
                         prev_go + (S.PACE_NUM * prev_lines + S.PACE_DEN - 1) // S.PACE_DEN + S.PACE_ADD)
            if bi == 0:
                lo = max(lo, x_end + S.X_GAP - rc0 - S.LAT_GO, cur_abs + S.OP_GAP - rc0 - S.LAT_GO)
            b.update(go_at=lo, first_cmd_abs=rc0 + lo + S.LAT_GO, landing=b["desc_i"] % S.LANDING, epoch=epoch,
                     tag_base=(b["desc_i"] % 16) * 64)
            epoch += 1
            prev_go, prev_len, prev_lines = lo, b["nwords"], b["n_lines"]
            rc = lo
            cur_abs = rc0 + lo + S.LAT_GO + b["nwords"] - 1
        op["first_cmd_abs"] = r["blocks"][0]["first_cmd_abs"]
        op["last_cmd_abs"] = cur_abs
        ops_out.append(op)
    kd["rc_end"] = prev_go + prev_len + S.BUSY
    kd["t_launch"], kd["rc0"] = t_launch, rc0
    ing.append((t_arm, S.ingress(desc=(0, len(descs), 1), target=S.SVG_TGT)))
    ing.append((t_arm + 1, S.ingress(desc=(0, len(descs), 1), target=S.XC_TGT)))
    ing.append((t_launch, S.ingress(launch=True, target=0)))
    for i, b in enumerate(descs):
        d = S.desc_row(i, row_base=b["row_base"], landing=b["landing"], epoch=b["epoch"], rows=b["n_lines"],
                       tag_base=b["tag_base"], prog_base=b["prog"][0], prog_limit=b["prog"][1], go_at=b["go_at"],
                       layer_stride=0, expert_stride=0, id_sel=0, row_off=b["r0"], loops=1, lstep=0, mode=0, mrel=1,
                       fl=int(b["head"]))
        for j, tgt in enumerate((S.SVG_TGT, S.XC_TGT)):
            ing.append((desc_install_t + 2 * i + j, S.ingress(cfg=(1 << 10 | i, d), target=tgt)))
    ing.sort(key=lambda e: e[0])
    xw_ev.sort(key=lambda e: e[0])
    assert len({e[0] for e in ing}) == len(ing), "two ingress words on one edge"
    assert len({e[0] for e in xw_ev}) == len(xw_ev), "two x beats on one edge"
    n_end = cur_abs + S.DRAIN
    budget = dict(descriptors=len(descs), table_rows=S.TBL, programme_words_matvec=store.top - S.ATT_RESERVED,
                  store_top=store.top, distinct_programmes=len(store.progs), qwen_tags=tags)
    kinds = [kd]
    return dict(ing=ing, xw=xw_ev, ids=[], mem=mem, ops=ops_out, kinds=kinds, n_end=n_end, budget=budget, descs=descs)


_compile_all = S.compile_all


def compile_all(fix_root, smw_root, layers, mut=""):
    """--layers qwen:<tag>[+<tag>...] runs the Qwen INT8 compiler; anything else is smb_unit's DS compiler."""
    if layers and layers[0][0].startswith("qwen"):
        return compile_qwen(os.environ.get("TOKSIM_QWEN_TAGS", "qkv").split("+"))
    return _compile_all(fix_root, smw_root, layers, mut)


S.compile_all = compile_all


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "run" and "--bundle" not in argv:
        argv += ["--bundle", str(ROOT)]
    rc = S.main(argv)
    # annotate the result with the die composition and the static-schedule knobs actually used
    if argv and argv[0] == "run":
        out = Path(argv[argv.index("--out") + 1])
        if out.exists():
            d = json.loads(out.read_text())
            d["rtl"] = ("cp_svg ot_static_run_target -> ot_hbm_svc_sm_group_rel_id #(ID_COHORT 1) -> "
                        "ot_hbm_svc_vm_kshare_splitstrap #(KRL1 1) -> 4 x ot_hbm_svc_pc_ctrl_leaf_cfg_h9b (die params) -> "
                        "DRAM timing fixture; xc ot_hbm_svc_sm_xcal_rel_t; SM ot_hbm_accel_smh_attn #(ENABLE_INT8 1); "
                        "tb_toksim_smhbm.sv, Verilator 5.050 (GEN2e3 die composition)")
            d["static_schedule"] = dict(first_go=S.FIRST_GO, op_gap=S.OP_GAP, x_gap=S.X_GAP, pace_num=S.PACE_NUM,
                                        pace_den=S.PACE_DEN, pace_add=S.PACE_ADD, fetch=S.FETCH, expert_first=S.EXP_FIRST,
                                        ids_lag=S.IDS_LAG, bscale=S.BSCALE)
            d["source_revision"] = (ROOT / "REV").read_text().strip() if (ROOT / "REV").exists() else None
            out.write_text(json.dumps(d, indent=1, default=str) + "\n")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
