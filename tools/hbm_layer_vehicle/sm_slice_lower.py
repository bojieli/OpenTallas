#!/usr/bin/env python3
"""TOK-FUNC2-HBM-SM (10-21): production lowering of the DS SM.MATVEC records of one layer onto the d4g SW-quadrant
slice -- every record drives the die's REAL SM chain, no TB x stimulus, no stub, no golden on an on-chip path.

Chain driven (die.v names; one SM service group k = 0..NSM-1 of the SW quadrant, all four SMs of the SW writer):
  host_cp_ingress output pins (slice inputs, ingress AXI rate = layer_images.CpBus) -> hleaf_SW (CFG_LAT 2)
    -> cp_svg_SW<k> (ot_static_run_target, tgt 64+k): svg programme store rows (window A) + issuer descriptors (window B)
       -> svg_SW<k> = ot_hbm_svc_sm_group_rel_id #(ID_COHORT 1) -> vmks_SW<k> -> ctl_SW_p<4k..4k+3> (h9b) -> phy_SW
          (off-chip PHY + DRAM model, preloaded with the packed136 HBM image of the record weights: +HBM_IMG_DIR)
    -> xc_SW<k> (ot_hbm_svc_sm_xcal_rel_t, tgt 192+k): the lockstep extension calendar (cmd_ext)
    -> xl_SW_ctl (ot_hgi_sm_xload_cl2_ctlx, tgt 100): MODE 1 x-load command table; reads the record's x (A operand,
       FP32 in the SW VM: cyc-0 VM preload of the ds_native pre-record state) through rq2 of vmb_SW0..7 (l12 pads),
       BF16 convert / FP8 block quantiser (xl_SW_aqlo/hi) -> xq_SW_p0/p1 egress -> sm_SW0..3 x stores
    -> smw_SW (ot_hbm_sm_vm_wr_q_t_lanes4, tgt 160): MODE 1 writer descriptor table; SM k result rows -> vmb_SW<k>.wq1
    -> calendar_SW (hfd_hgi_vm_calendar_f20, tgt 96): component-probe EXCLUSIVE reservation (every edge, every bank:
       read owner 2 = x-load, write owner 1 = SM writer; all other VM clients idle) -- not a shared layer calendar
    -> refcfg_SW (ot_hbm_pc_refresh_cfg, tgt 126): boot row = the die's per-PC refresh phase (releases the PCs)
  hb_router_ids (central, outside the slice) is replayed from the fixture router top-k for routed experts.
Programme / descriptor / go-slot / residency compiler = smb_unit.compile_all (the proven SMB h9b cohort1 INT8=1 service
compiler, receipt results/token_pass/hbm_functional_1021/smb_param1), XMODE 'die' (x leaves the die x loader at its
measured beat cadence instead of a TB stream); the four SMs run the SAME table (same shapes), SM k takes rows
[kR, kR+R) of the die-0 half (d4g W1 placement, sm_mv_unit 'sm0' = SM 0), its HBM image on PCs 4k..4k+3 (svg id_sm strap).
Checks (static, bit-exact): every result word in VM (sector of bank k, writer row) == the ds_native fixture O at the end
of the replay, and hleaf_SW__s_fault (cp_svg/svg, xc, xl, smw, calendar, refcfg sticky faults) == 0.  The FIXED_GO
issuer, the x-load sequencer (late command / response check) and the writer fault on any static-schedule violation.
Scope: component_probe (exclusive VM reservation; other units idle); no native layer / token qualification.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault("HDC_V41_ARITH", "chunk8")
os.environ.setdefault("SMB_XMODE", "die")
import numpy as np  # noqa: E402

import smb_unit as SB  # noqa: E402
import sm_images as SI  # noqa: E402

if SB.XMODE != "die":
    raise SystemExit(f"sm_slice_lower needs smb_unit XMODE 'die' (x from the die x loader), got {SB.XMODE}")

SVG_TGT, XC_TGT, XL_TGT, SMW_TGT, CAL_TGT, REF_TGT = 64, 192, 100, 160, 96, 126
LEAD = 8                       # ot_static_cmd_target_core LEAD (xl / smw tables)
XL_C = 3 + LEAD                # x command C = launch at the collar pin + 3 + LEAD + at (sm_images.xl_bf_timing)
SMW_F = 2 + LEAD               # writer descriptor fire = launch at the collar pin + 2 + LEAD + at
COLLAR = 3                     # ingress output pin event c -> collar samples launch at c + 1 + CFG_LAT 2
X_MARGIN = int(os.environ.get("SMSL_X_MARGIN", 32))       # extra edges after the modelled last x beat before the go
RES_LAT = int(os.environ.get("SMSL_RES_LAT", 200))        # last SM command -> last result row in the writer (bound)
XROW0 = 256                    # x vectors live in VM rows >= XROW0 (all 8 banks); results in rows < XROW0 (banks 0..3)
NPC_SW = 16                    # refcfg_SW #(NPC 16): PCs 0..15 of the SW stack


def refresh_reload(p):
    """die per-PC refresh phase (tools/hbm_die_v15/full_die_v16.py _pc_refresh_reload; tb_toksim_smhbm g_pc)."""
    return SB.refresh_reload(p)


# refcfg_SW boot row -> PC reset release (hbm edges after the cfg_v pin edge): hleaf CFG_LAT 2 + refcfg cfg flop +
# loaded (stream), ls[0], ls[1], prst (hbm) + the PC leaf reset relay; SB.REF_PAD absorbs the estimate error.
REF_REL_STREAM, REF_REL_HBM = 5, 7


def lower_comps_refresh(compile_k, nsm, *args, **kw):
    """two-pass lowering with the refresh-aware residency bound (smb_unit.REFRESH): pass 1 fixes the absolute launch
    (it does not depend on go values: same install rows), pass 2 recompiles every SM against the refresh hazard windows
    of the quadrant's PCs at that launch.  SMB_REFRESH=0 -> pass 1 only (refresh-blind, diagnostic)."""
    SB.REFRESH = None
    rep, per, summ = lower_comps([compile_k(k) for k in range(nsm)], *args, **kw)
    if not SB.REFRESH_ON:
        return rep, per, summ
    SB.REFRESH = dict(summ["refresh_abs"], pcs=list(range(4 * nsm)))
    try:
        rep2, per2, summ2 = lower_comps([compile_k(k) for k in range(nsm)], *args, **kw)
    finally:
        SB.REFRESH = None
    if summ2["launch_stream"] != summ["launch_stream"]:
        raise AssertionError(f"refresh pass moved the launch {summ['launch_stream']} -> {summ2['launch_stream']} (cal rows {summ['calendar_rows']} -> {summ2['calendar_rows']}, layer {summ['layer_rel_cycles']} -> {summ2['layer_rel_cycles']})")
    return rep2, per2, summ2


def compile_sm(fix_dir: Path, smw_dir: Path, layer: int, k: int):
    """smb_unit.compile_all for SM k's rows (one layer kind)."""
    orig = SB.layer_records

    def sliced(f, s):
        recs, keep = orig(f, s), []
        for r in recs:
            R = r["R"]
            lo, hi = k * R, (k + 1) * R
            m_die = -(-r["m"] // 2)
            if lo >= m_die:                      # d4g W1: SM k holds no row of this record (idle SM)
                continue
            if hi > m_die:
                raise ValueError(f"SM {k} rows [{lo},{hi}) partially outside the die-0 half of k{r['k']} (m {r['m']})")
            keep.append(r)
            r["w"] = SB.MV.V.Q8(r["w"].q[lo:hi], r["w"].e[lo:hi]) if not isinstance(r["w"], np.ndarray) else r["w"][lo:hi]
            r["o_full"], r["acc_full"] = r["o"], r["acc"]
            r["o"], r["acc"], r["row0"] = r["o"][lo:hi], r["acc"][lo:hi], lo
        return keep
    SB.layer_records = sliced
    gap, opg = SB.X_GAP, SB.OP_GAP
    SB.X_GAP = gap + X_MARGIN
    SB.OP_GAP = max(opg, RES_LAT + 64)
    try:
        return SB.compile_all(fix_dir.parent, smw_dir.parent, [(fix_dir.name, layer)])
    finally:
        SB.layer_records, SB.X_GAP, SB.OP_GAP = orig, gap, opg


def hbm_image(descs, pcs):
    """packed136 HBM sectors of every block at its DRAM row on the SM's four PCs (smb_unit compile_all, pcs strap)."""
    from hbm_svc_packed136_image import sector_address
    mem = {}
    for b in descs:
        raw = b"".join(int(x).to_bytes(136, "little") for x in b["lines"])
        total = ((len(b["lines"]) * 136 + 127) // 128) * 4
        raw += bytes(32 * total - len(raw))
        alloc = dict(pcs=list(pcs), row_base=b["dram_row"] >> 3, stack_bytes=1 << 35)
        for o in range(total):
            sa = sector_address(o + 512 * (b["dram_row"] & 7), alloc)
            assert sa not in mem, ("HBM image alias", hex(sa))
            mem[sa] = int.from_bytes(raw[32 * o:32 * o + 32], "little")
    return mem


def decode_ing(v):
    return dict(cfg=bool(v >> 319 & 1), desc=bool(v >> 318 & 1), launch=bool(v >> 317 & 1), target=v >> 309 & 0xFF,
                addr=v >> 297 & 0xFFF, data=v >> 41 & ((1 << 256) - 1), base=v >> 29 & 0xFFF, limit=v >> 16 & 0x1FFF,
                loops=v & 0xFFFF)


def runs(rows):
    """[(addr, data)] -> contiguous address runs [(base, [data...])] in order."""
    out = []
    for a, d in rows:
        if out and out[-1][0] + len(out[-1][1]) == a:
            out[-1][1].append(d)
        else:
            out.append((a, [d]))
    return out


def lower(fix_dir, smw_dir, layer, boundary, nsm=4, t_start=4, quarter=0, priced_by_tag=None):
    """-> (replay dict, per-fixture-record entries, summary).  fix_dir = FIX/L<LL>, smw_dir = SMW/L<LL>.
    priced_by_tag {tag: [priced i in layer order]}: a fused fixture record 'T w1+w3' (one matrix, w1 and w3 rows
    stacked) without its own priced link covers the priced records 'T w1' and 'T w3' of the same occurrence."""
    fix_dir, smw_dir = Path(fix_dir), Path(smw_dir)
    if fix_dir.name != smw_dir.name:
        raise ValueError("fixture and SM weight dirs must name the same layer")
    return lower_comps_refresh(lambda k: compile_sm(fix_dir, smw_dir, layer, k), nsm, layer, boundary, design="ds",
                               t_start=t_start, quarter=quarter, priced_by_tag=priced_by_tag,
                               provenance="released_checkpoint_fixture")


QWEN_TAGS = ("qkv", "o", "gu", "down")


def compile_qwen_sm(kv_dir: Path, L: int, k: int, rank=0, tags=QWEN_TAGS, *, partitions=16, row_chunk=None):
    """Qwen3-8B D4G8 INT8 (fmt 3) SM.MATVEC of layer L for SM k: toksim_smhbm.compile_qwen (the packed INT8 svg
    programme, PREL mark bit 118 + xc command[116], measured fi8 runs) on the REAL captured operands
    (qwen_sm_mv_kv.py sm_mv.json/.npz: W int8, A, O = lib.sm_int8) instead of its seeded draw; d4g8 placement rows
    [kR, kR+R), R = ceil(m / 16)."""
    import toksim_smhbm as TS
    from qwen_sm_mv_unit import load_kv
    from hgi_sim import lib as A
    G, V = SB.MV.G, SB.MV.V
    if partitions < 1 or not 0 <= k < partitions:
        raise ValueError("SM logical partition must lie inside explicit partition count")
    _, kv = load_kv(Path(kv_dir), L, rank)

    def real(tags_, seed):
        out = []
        for i, tag in enumerate(tags_):
            d = kv[tag]
            W, x, O = d["W"], np.asarray(d["A"], np.float32), np.asarray(d["O"], np.float32)
            m, K = W.shape
            R = -(-m // partitions)
            lo, hi = k * R, (k + 1) * R
            if row_chunk is not None:
                hi = min(hi, m)
                first, count = row_chunk
                if first < 0 or count < 1 or first + count > hi - lo:
                    raise ValueError(f"Qwen {tag}: chunk {row_chunk} exceeds partition rows {hi-lo}")
                lo, hi = lo + first, lo + first + count
                R = count
            if hi > m or lo >= hi:
                raise ValueError(f"Qwen {tag}: SM {k} rows [{lo},{hi}) beyond m {m}")
            Wk = W[lo:hi]
            acc = np.asarray(V.csum(G.mul(Wk.astype(np.float32), G.to_bf16(x)[None, :])), np.float32)
            lib = np.asarray(A.sm_int8(Wk, x), np.float32)
            gok = bool(np.array_equal(acc.view(np.uint32), lib.view(np.uint32)) and
                       np.array_equal(lib.view(np.uint32), O[lo:hi].view(np.uint32)))
            out.append(dict(k=i, tag=tag, K=K, m=m, R=R, W=Wk, x=x, acc=acc, o=O[lo:hi].view(np.uint32), ofmt="FP32",
                            gok=gok, slot=None, eid=None, fmt=0, row0=lo,
                            logical_partition=k, partitions=partitions, row_chunk=row_chunk,
                            rec=dict(tag=tag, priced=d["meta"].get("priced_d4g8", []),
                                     desc={"A": ["VM", K, 1, "FP32", tag, L]})))
        return out
    q, gap, opg = TS.qwen_records, SB.X_GAP, SB.OP_GAP
    TS.qwen_records = real
    SB.X_GAP = gap + X_MARGIN
    SB.OP_GAP = max(opg, RES_LAT + 64)
    try:
        c = TS.compile_qwen(list(tags))
    finally:
        TS.qwen_records, SB.X_GAP, SB.OP_GAP = q, gap, opg
    for r in c["kinds"][0]["recs"]:
        r.setdefault("rec", {}).setdefault("desc", {"A": ["VM", r["K"], 1, "FP32", r["tag"], L]})
    return c


def lower_qwen(kv_dir, L, boundary, nsm=4, t_start=4):
    return lower_comps_refresh(lambda k: compile_qwen_sm(Path(kv_dir), L, k), nsm, L, boundary, design="qwen",
                               t_start=t_start, provenance="captured_qwen_sm_operands (qwen_sm_mv_kv, rank 0)")


GO_LO, GO_W = 119, 24          # issuer descriptor go_at field (smb_unit.desc_row)


def lower_comps(comps, layer, boundary, design, t_start=4, quarter=0, priced_by_tag=None, provenance=""):
    """the slice replay of per-SM service compiles (smb_unit / toksim_smhbm compile dicts, SM k = comps[k])."""
    from layer_images import CpBus
    nsm = len(comps)
    if quarter != 0:
        raise ValueError("SW slice: quarter 0 only")
    inports = {e["name"] for e in boundary["inputs"]}
    outports = {e["name"] for e in boundary["outputs"]}
    insts = set(boundary["instances"])
    need = {"phy_SW", "xl_SW_ctl", "smw_SW", "calendar_SW", "refcfg_SW", "hleaf_SW"} | \
        {f"{p}{k}" for k in range(nsm) for p in ("sm_SW", "svg_SW", "cp_svg_SW", "xc_SW", "vmks_SW")}
    if not need <= insts:
        raise ValueError(f"slice lacks the SM chain instances {sorted(need - insts)}")
    c0 = comps[0]
    kd = c0["kinds"][0]
    E1 = kd["t_launch"] + 1                       # SMB: launch event edge + 1 = collar sample edge
    rel = lambda t: int(t) - E1
    # ---- per SM: programme rows (its own store), descriptor rows on SM 0's FIXED go slots (one quadrant schedule:
    # the x loader and the writer serve the four SMs together).  An SM that holds no row of a record (d4g W1 dealing)
    # has no descriptor for it; its other blocks keep SM 0's slots (go_at is absolute from the run launch).
    def bid(descs):
        n = {}
        out = []
        for b in descs:
            out.append((b["k"], n.get(b["k"], 0)))
            n[b["k"]] = n.get(b["k"], 0) + 1
        return out
    go0 = {i_: b["go_at"] for i_, b in zip(bid(c0["descs"]), c0["descs"])}
    tables = []
    for k, c in enumerate(comps):
        prog, run, orig_desc = {}, {}, {}
        for t, v in c["ing"]:
            f = decode_ing(v)
            if f["cfg"] and f["addr"] >> 10 == 1:
                orig_desc.setdefault(f["target"], {})[f["addr"] & 1023] = f["data"]
            elif f["cfg"]:
                prog.setdefault(f["target"], []).append((f["addr"], f["data"]))
            elif f["desc"]:
                run[f["target"]] = (f["base"], f["limit"], f["loops"])
        assert set(prog) == {SVG_TGT, XC_TGT} and set(run) == {SVG_TGT, XC_TGT}, (sorted(prog), sorted(run))
        drows, early = [], 0
        for i, (ident, b) in enumerate(zip(bid(c["descs"]), c["descs"])):
            g = go0[ident]
            early = max(early, b["go_at"] - g)
            d = orig_desc[SVG_TGT][i]
            if orig_desc[XC_TGT][i] != d or (d >> GO_LO) & ((1 << GO_W) - 1) != b["go_at"]:
                raise AssertionError("descriptor row / go slot differ from the service compile")
            d = (d & ~(((1 << GO_W) - 1) << GO_LO)) | (g << GO_LO)      # SM 0's fixed slot
            drows.append((1 << 10 | i, d))
        if early > 0:
            raise ValueError(f"SM {k}: its own residency model needs a slot {early} edges after SM 0's")
        tables.append(dict(prog=prog, desc=drows, run=run, recs={r["k"] for r in c["kinds"][0]["recs"]}))
    # ---- x: VM placement (dedupe identical operands), x-load command table, SMB op timing
    recs = {r["k"]: r for r in kd["recs"]}
    xplace, xrow, xl_entries, smw_entries, ops = {}, XROW0, [], [], []
    vm_pre = {}
    orow = 0
    prev_last = None
    for j, op in enumerate(c0["ops"]):
        r = recs[op["k"]]
        x = np.asarray(r["x"], np.float32)
        key = (json.dumps(r["rec"].get("desc", {}).get("A")), hashlib.sha256(x.tobytes()).hexdigest())
        if key not in xplace:
            rows = -(-len(x) // 64)
            if xrow + rows > 1024:
                raise ValueError("SW VM rows exhausted by x operands; split the replay")
            xplace[key] = xrow
            words = np.zeros(rows * 64, np.uint32)
            words[:len(x)] = x.view(np.uint32)
            for i in range(rows * 8):
                sec = (quarter << 13) | ((xrow + (i >> 3)) << 3) | (i & 7)
                vm_pre[sec] = [int(w) for w in words[8 * i:8 * i + 8]]
            xrow += rows
        xbase = xplace[key] << 6
        at_x = rel(op["x0"]) - XL_C
        if at_x < 0:
            raise ValueError(f"x-load of op {j} before the table can fire ({at_x})")
        xl_entries.append((at_x, SI.xl_cmd(xbase, len(x), 1, 0, fmt=r["fmt"], xb=op.get("xb", 0))))
        R = r["R"]
        nrow = ((R - 1) >> 3) + 1
        if orow + nrow > XROW0:
            raise ValueError("SW VM result rows exhausted; split the replay")
        ofmt_bf = r["ofmt"] == "BF16"
        if j == 0:
            at_w = 0
        else:
            w_rel = rel(prev_last) + RES_LAT
            if w_rel + SMW_F + 8 >= rel(op["first_cmd_abs"]):
                raise ValueError(f"no idle writer window before op {j} (last result bound {RES_LAT})")
            at_w = w_rel - SMW_F
        smw_entries.append((at_w, SI.smw_cmd(orow, 0, 1, 0, fmt=int(ofmt_bf), h=0)))
        priced = [int(p["i"]) for p in r["rec"].get("priced", [])]
        tag = r["rec"]["tag"]
        if not priced and priced_by_tag and tag.endswith(" w1+w3"):
            occ = int(r["rec"].get("occ", 0))
            for part in ("w1", "w3"):
                lst = priced_by_tag.get(tag[:-len("w1+w3")] + part, [])
                if occ < len(lst):
                    priced.append(int(lst[occ]))
        ops.append(dict(op, x_vm_row=xplace[key], x_n=len(x), x_fmt=r["fmt"], xl_at=at_x, smw_at=at_w, o_row=orow,
                        o_rows=nrow, priced=priced))
        orow += nrow
        prev_last = op["last_cmd_abs"]
    if any(b[0] <= a[0] for a, b in zip(xl_entries, xl_entries[1:])):
        raise ValueError("x-load table not strictly increasing")
    if any(b[0] <= a[0] for a, b in zip(smw_entries, smw_entries[1:])):
        raise ValueError("writer table not strictly increasing")
    if len(xl_entries) > 128 or len(smw_entries) > 128:
        raise ValueError("MODE 1 table depth 128 exceeded")
    # ---- calendar: exclusive component reservation (rslot owner 2 = x load, wslot owner 1 = SM writer, all banks)
    end_rel = rel(c0["n_end"]) + RES_LAT
    payload = SI.cal_word(rslot_v=0xFF, rslot=sum(2 << (3 * b) for b in range(8)),
                          wslot_v=0xFF, wslot=sum(SI.WSLOT_SMW << (3 * b) for b in range(8)))
    # ---- the ingress stream (install everything, arm every target, ONE global launch)
    bus = CpBus(t_start, src="image:SM")
    bus.install(REF_TGT, [sum(refresh_reload(p) << (8 * p) for p in range(NPC_SW))], base=0x800)
    for k, T in enumerate(tables):
        for tgt0, tgt in ((SVG_TGT, SVG_TGT + k), (XC_TGT, XC_TGT + k)):
            for base, data in runs(T["prog"][tgt0] + T["desc"]):
                bus.install(tgt, data, base=base)
    xl_rows = SI.cmd_table_rows(xl_entries, SI.XL_CW)
    smw_rows = SI.cmd_table_rows(smw_entries, SI.SMW_CW)
    assert [r_ for r_, _ in xl_rows] == list(range(len(xl_rows))) and [r_ for r_, _ in smw_rows] == list(range(len(smw_rows)))
    bus.install(XL_TGT, [d for _, d in xl_rows], base=SI.CMD_WIN_TABLE)
    bus.install(SMW_TGT, [d for _, d in smw_rows], base=SI.CMD_WIN_TABLE)
    # calendar rows: enough rows x loops to cover the observation window from its launch
    span = end_rel + 256                       # the calendar runs from the global launch to past the final checks
    cal_rows = max(1, -(-span // 65535))
    if cal_rows > 128:
        raise ValueError("calendar reservation too long")
    cal_loops = min(65535, -(-span // cal_rows) + 1)
    bus.install(CAL_TGT, [SI.prog_row(i, payload, SI.CAL_W) for i in range(cal_rows)], base=0)
    for k, T in enumerate(tables):
        for tgt0 in (SVG_TGT, XC_TGT):
            b_, l_, n_ = T["run"][tgt0]
            bus.desc(tgt0 + k, b_, l_, n_)
    bus.desc(XL_TGT, 0, len(xl_entries), 1)
    bus.desc(SMW_TGT, 0, len(smw_entries), 1)
    bus.desc(CAL_TGT, 0, cal_rows, cal_loops)
    c_launch = bus.launch()
    S = c_launch + COLLAR
    ref_pin = min(e["cyc"] for e in bus.ev if e["port"] == "host_cp_ingress__cfg_target" and int(e["val"], 16) == REF_TGT)
    refresh_abs = dict(rc0_abs=S + SB.OFF - 1,                  # issuer rc 0 (E1 = t_launch + 1 maps to S)
                       r0_hbm=int((ref_pin + REF_REL_STREAM) * SB.HBM_PER_STREAM) + REF_REL_HBM)
    ev = [dict(e) for e in bus.ev]
    # ---- router top-k broadcast (central hb_router_ids, outside the slice): fixture router result, compiler slot
    for t, v in c0["ids"]:
        c = rel(t) + S
        for port, val in (("hb_router_ids__ids_v", 1), ("hb_router_ids__ids_layer", v >> 54 & 0xFF),
                          ("hb_router_ids__ids", v & ((1 << 54) - 1)), ("hb_router_ids__ids_cohort", 1)):
            ev.append(dict(k="D", dom="stream", cyc=c, port=port, val=f"{val:x}", src="fixture:router_topk"))
        ev.append(dict(k="D", dom="stream", cyc=c + 1, port="hb_router_ids__ids_v", val="0", src="fixture:router_topk"))
    # ---- VM preload (x operands = ds_native pre-record state), HBM image (record weights), checks
    for sec, words in sorted(vm_pre.items()):
        ev.append(dict(k="M", dom="stream", cyc=0, mem="vm", quarter=quarter, sector=sec, bank=sec & 7,
                       row=(sec & 0x1FFF) >> 3, val="".join(f"{w:08x}" for w in reversed(words)), src="fixture:VM_preload"))
    hbm_sectors = 0
    for k, c in enumerate(comps):
        mem = hbm_image(c["descs"], [4 * k + p for p in range(4)])
        hbm_sectors += len(mem)
        for sa, d in sorted(mem.items()):
            ev.append(dict(k="M", dom="hbm", cyc=0, mem="hbm", inst="phy_SW", sector=sa, val=f"{d:064x}",
                           src="image:HBM_packed136"))
    t_check = S + end_rel + 64
    checks = 0
    for j, op in enumerate(ops):
        for k, c in enumerate(comps):
            rk = {r["k"]: r for r in c["kinds"][0]["recs"]}.get(op["k"])
            if rk is None:                       # idle SM for this record
                continue
            o = np.asarray(rk["o"], np.uint32)
            for rr in range(op["o_rows"]):
                words, msk = [0] * 8, [0] * 8
                for ln in range(8):
                    r_ = 8 * rr + ln
                    if r_ < len(o):
                        words[ln], msk[ln] = int(o[r_]), 0xFFFFFFFF
                sec = (quarter << 13) | ((op["o_row"] + rr) << 3) | k
                ev.append(dict(k="C", dom="stream", cyc=t_check, port=f"vm:{sec:x}",
                               val="".join(f"{w:08x}" for w in reversed(words)),
                               mask="".join(f"{m:08x}" for m in reversed(msk)), src="fixture:ds_native_O",
                               rec=op["priced"][0] if op["priced"] else -1))
                checks += 1
    for port in ("hleaf_SW__s_fault", "fs_SW__fault"):
        if port in outports:
            w = [e["width"] for e in boundary["outputs"] if e["name"] == port][0]
            ev.append(dict(k="C", dom="stream", cyc=t_check + 1, port=port, val="0", mask=f"{(1 << w) - 1:x}",
                           src="static:no_fault"))
    for e in ev:
        if e["k"] == "D" and e["port"] not in inports:
            raise ValueError(f"replay drives {e['port']}, not a slice input")
    ev.sort(key=lambda x: (x["dom"], x["cyc"], x["k"]))
    rep = dict(schema="opentallas.hbm_slice_replay.v1", slice=boundary.get("slice_top", "sw"), design=design,
               scope="component_probe", qualifies_native_layer=False, qualifies_native_chain=False,
               state_seed_provenance=[provenance], layer=str(layer),
               lowering="sm_slice_v1 (smb_unit h9b cohort1 svg/xc + xl_SW_ctl + smw_SW + calendar reservation)",
               launch_stream=c_launch, collar_launch_stream=S, end_check_stream=t_check, events=ev)
    summary = dict(sms=nsm, ops=len(ops), descriptors=[len(T["desc"]) for T in tables],
                   programme_words=[len(T["prog"][SVG_TGT]) for T in tables],
                   xl_commands=len(xl_entries), smw_commands=len(smw_entries), calendar_rows=cal_rows,
                   calendar_loops=cal_loops, x_vm_rows=xrow - XROW0, o_vm_rows=orow, hbm_sectors=hbm_sectors,
                   vm_preload_sectors=len(vm_pre), checks=checks,
                   events=sum(e["k"] != "M" for e in ev), launch_stream=c_launch,
                   first_cmd_stream=rel(ops[0]["first_cmd_abs"]) + S, last_cmd_stream=rel(ops[-1]["last_cmd_abs"]) + S,
                   layer_rel_cycles=rel(ops[-1]["last_cmd_abs"]) - rel(ops[0]["first_cmd_abs"]) if ops else 0,
                   static_schedule=c0["budget"].get("static_schedule"), x_margin=X_MARGIN, result_latency_bound=RES_LAT,
                   refresh_abs=refresh_abs)
    per = []
    for op in ops:
        per.append(dict(k=op["k"], tag=op["tag"], fmt=op["fmt"], O_fmt=op["O_fmt"], R=op["R"], Gn=op["Gn"],
                        blocks=op["blocks"], lines=op["lines"], priced=op["priced"], x_vm_row=op["x_vm_row"],
                        x_n=op["x_n"], xl_at=op["xl_at"], smw_at=op["smw_at"], o_row=op["o_row"],
                        first_cmd_stream=rel(op["first_cmd_abs"]) + S, last_cmd_stream=rel(op["last_cmd_abs"]) + S,
                        routed_slot=op["slot"], expert_id=op["eid"],
                        active_sms=[k for k, T in enumerate(tables) if op["k"] in T["recs"]]))
    return rep, per, summary


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fixtures", type=Path, help="FIX/L<LL> (ds_layer_fixtures dir)")
    ap.add_argument("--smw", type=Path, help="SMW/L<LL> (ds_sm_weights dir)")
    ap.add_argument("--qwen-kv", type=Path, help="Qwen: qwen_sm_mv_kv stage dir (sm_mv.json/.npz) instead of DS dirs")
    ap.add_argument("--layer", type=int, required=True)
    ap.add_argument("--boundary", type=Path, required=True)
    ap.add_argument("--sms", type=int, default=4)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    bnd = json.loads(a.boundary.read_text())
    if a.qwen_kv:
        rep, per, summ = lower_qwen(a.qwen_kv, a.layer, bnd, nsm=a.sms)
    else:
        rep, per, summ = lower(a.fixtures, a.smw, a.layer, bnd, nsm=a.sms)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "replay.json").write_text(json.dumps(rep) + "\n")
    (a.out / "sm_manifest.json").write_text(json.dumps(dict(summary=summ, records=per), indent=1) + "\n")
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
