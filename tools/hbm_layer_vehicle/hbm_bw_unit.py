#!/usr/bin/env python3
"""HBM-BW (10-19): controller-only HBM boundary bench for one SM's four PCs (tb_hbm_bw_pc4.sv).

  hbm_bw_unit.py gen  --pattern P --out DIR [--layers N] [--seed S]   write DIR/<P>.blk (row15 slot3 words8, hex) + .json
  hbm_bw_unit.py run  --work W --pattern P [--mr] [--mrkey0] [--gaps]  build (Verilator 5.050 from $VERILATOR) + run + parse
Patterns (block = one SM block of `lines` 136-B lines = ceil(lines*136/128) words per PC; full block 64 lines = 68 words):
  asbuilt   one block per DRAM row index (slot 0), rows consecutive        (HBM-SMBUDGET layout, BSCALE 8)
  packed    8 blocks per row index, slot = block index mod 8                (BSCALE 1: slot = set rotates)
  rand      one block per row index, random rows, slot 0                    (worst case: every block a new row, same set)
  ds        DS V4.1 L14 fetch order (smb_unit kinds: 27 non-expert blocks incl. the shared expert, 6 routed w1+w3 +
            6 routed w2 with RANDOM expert ids) with the HBM-BW layout: non-expert blocks rotate the bank-set and end on
            set 5, routed w1+w3 alternate sets 6/7 and routed w2 sets 1/2 (copy = routed position parity), shared w2 set 0
  ds_nodup  as ds but every routed w1+w3 on set 6 and every w2 on set 1 (no copy alternation)
HBM-ROTLAYOUT (10-19) per-stream-class patterns, every address from the compiler's layout functions (hbm_bank_layout):
  ds_rot     DS L14 layer stream laid out by hbm_bank_layout.layout_bw (= smb_unit) incl. kind-boundary phasing
  weights    DS non-expert blocks (+ shared w2), slot-packed       experts  DS routed w1+w3 / w2, copies by position
  kv         DS attention KV window runs, slot-packed               embed_head  LM-head run of full blocks, slot-packed
  qwen       Qwen3-8B INT8 per-SM qkv/o/gu/down, slot-packed        tables   runtime-indexed 2-block rows (table_entry)
  (ds = the HBM-MC2 hand layout: one same-set block pair at every layer boundary -> refused by the ROTLAYOUT check)
"""
import argparse, json, os, random, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[2]
LINE_B, SECTOR_B = 136, 32

def words(lines):
    return -(-lines * LINE_B // 128)            # per-PC words (sectors) = total/4, total = ceil(lines*136/128)*4

# DS V4.1 L14 fetch order (results/rtl/hbm_ds_layer_tput_1018/smbudget_1019/pos.json, kind L14): (tag, blocks, lines)
L14 = [("engram.wkv", 7, 432), ("wq_a", 1, 40), ("wkv", 1, 40), ("compressor", 2, 80), ("indexer.wq_b", 1, 32),
       ("wq_b", 4, 256), ("wo_a", 4, 256), ("wo_b", 2, 128), ("router", 2, 80), ("shared.w13", 2, 80)]
R13, R2, SH2 = 48, 32, 48

def split(blocks, lines):
    out, left = [], lines
    for _ in range(blocks):
        n = min(64, left); out.append(n); left -= n
    assert left == 0, (blocks, lines)
    return out

def layer_ds(rng, L, nodup):
    """one L14-shaped layer -> list of (kind, lines, set, row_hint)"""
    ne = [n for (_, b, l) in L14 for n in split(b, l)]
    seq = []
    N = len(ne)
    for j, n in enumerate(ne):                      # non-expert: rotate, last on set 4
        seq.append(("ne", n, (4 - (N - 1 - j)) % 8))
    ids = rng.sample(range(384), 6)
    for i, e in enumerate(ids):                     # routed w1+w3: copies on sets 5/6/7 (copy = position mod 3)
        seq.append(("r13", R13, 6 if nodup else 5 + i % 3, e))
    seq.append(("sh2", SH2, 0))
    for i, e in enumerate(rng.sample(ids, 6)):      # routed w2: copies on sets 1/2/3
        seq.append(("r2", R2, 1 if nodup else 1 + i % 3, e))
    return seq

def gen(pattern, n_layers, seed):
    rng = random.Random(seed)
    blks = []                                       # (row, slot, words)
    if pattern in ("asbuilt", "packed", "rand"):
        nb = 64 * n_layers
        for j in range(nb):
            if pattern == "asbuilt":
                blks.append((1000 + j, 0, 68))
            elif pattern == "packed":
                a = 8 * 1000 + j; blks.append((a >> 3, a & 7, 68))
            else:
                blks.append((rng.randrange(21000), 0, 68))
    elif pattern in ("ds", "ds_nodup"):
        ne_row = 100
        for L in range(n_layers):
            last_set = None
            for item in layer_ds(rng, L, pattern == "ds_nodup"):
                kind, lines, st = item[0], item[1], item[2]
                if kind in ("ne", "sh2"):
                    if last_set is not None and st <= last_set:
                        ne_row += 1
                    last_set = st
                    row = ne_row
                else:                               # routed expert e of layer L: its own row index (w13 + w2 slots)
                    row = 2048 + (L * 384 + item[3]) % 18000
                blks.append((row, st, words(lines)))
            ne_row += 1
    elif pattern in CLASS_PATTERNS:
        blks = [(r, st, w) for (r, st, w, _rt) in gen_class(pattern, n_layers, rng)]
    else:
        raise SystemExit(f"unknown pattern {pattern}")
    return blks


# ---------------------------------------------------------------- HBM-ROTLAYOUT (10-19): one census pattern per stream
# class, every address produced by the compiler's layout functions (hbm_bank_layout: packed / expert_set / table_entry)
# with the production shapes of that class.  (row, set, words, runtime_row)
import hbm_bank_layout as BL  # noqa: E402
QWEN_SM = (("qkv", 4096, 1536), ("o", 1024, 4096), ("gu", 4096, 6144), ("down", 3072, 4096))  # (tag, K, m per die)
CLASS_PATTERNS = ("ds_rot", "weights", "experts", "kv", "embed_head", "qwen", "tables", "tables_home", "rand_rot", "tables_seq",
                  "tables_rot")
PATTERN_CLASS = dict(ds_rot="weights", ds="weights", ds_nodup="weights", packed="weights", asbuilt="weights", rand="weights",
                     weights="weights", experts="experts", kv="kv", embed_head="embed_head", qwen="weights",
                     tables="tables", tables_home="tables", tables_seq="tables", tables_rot="tables", rand_rot="weights")


def _run(base, line_list, cls, what):
    addrs, _ = BL.static_run(base, line_list, cls, what)
    return [(a >> 3, a & 7, words(n), False) for a, n in zip(addrs, line_list)], (addrs[-1] // 8 + 1) * 8


def _lines(nl):
    return [min(64, nl - 64 * b) for b in range(-(-nl // 64))]


def gen_class(pattern, n_layers, rng):
    out = []
    if pattern == "ds_rot":
        out = gen_ds_rot(n_layers, rng)
    elif pattern == "weights":                     # DS non-expert L14 blocks (incl. shared w2), one rotated run a layer
        ne = [n for (_, b, l) in L14 for n in split(b, l)] + [SH2]
        base = 100 * 8
        for L in range(n_layers):
            blk, base = _run(base, ne, "weights", f"weights L{L}")
            out += blk
    elif pattern == "experts":                     # STRESS (refused by R2): routed blocks only, back to back, the
        for L in range(n_layers):                  # production copy triples w1+w3 1/2/3, w2 5/6/7 by position
            ids = rng.sample(range(384), 6)
            for p, e in enumerate(ids):
                out.append((2048 + (L * 384 + e) % 18000, (1, 2, 3)[p % 3], words(R13), True))
            for p, e in enumerate(rng.sample(ids, 6)):
                out.append((2048 + (L * 384 + e) % 18000, (5, 6, 7)[p % 3], words(R2), True))
    elif pattern == "kv":                          # DS attention KV of one SM: per layer one rotated window run
        base = 0x4000 * 8
        for L in range(n_layers):
            blk, base = _run(base, _lines(64 * 37 + 23 + 16 * L), "kv", f"kv L{L}")
            out += blk
    elif pattern == "embed_head":                  # LM head / output projection: one long rotated run of full blocks
        out, _ = _run(9000 * 8, [64] * (64 * n_layers), "embed_head", "head")
    elif pattern == "qwen":                        # Qwen3-8B INT8 per-SM rows ceil(m/16) x K codes, 128 codes a line
        base = 100 * 8
        for L in range(n_layers):
            ls = [n for (_, K, m) in QWEN_SM for n in _lines(-(-m // 16) * (K // 128))]
            blk, base = _run(base, ls, "weights", f"qwen L{L}")
            out += blk
    elif pattern == "tables":                      # runtime-indexed 2-block rows (embedding / engram shape 64 + 42 lines),
        for p in range(32 * n_layers):             # lookup p reads phase copy p mod 4 (table_entry)
            e = rng.randrange(17000)
            for a, n in zip(BL.table_entry(2000, e, 2, p), (64, 42)):
                out.append((a >> 3, a & 7, words(n), True))
    elif pattern == "tables_home":                 # REFUSED: the same lookups, every entry on its home sets only
        for _ in range(32 * n_layers):
            e = rng.randrange(70000)
            for k, n in enumerate((64, 42)):
                a = 2000 * 8 + e * 2 + k
                out.append((a >> 3, a & 7, words(n), True))
    elif pattern == "rand_rot":                    # DIAGNOSTIC: one full block per RANDOM row, set = i mod 8 (rotated)
        for i in range(64 * n_layers):
            out.append((2000 + rng.randrange(17000), i % 8, 68, True))
    elif pattern == "tables_seq":                  # DIAGNOSTIC: table entries read in index order (rows ascend)
        for i in range(32 * n_layers):
            for a, n in zip(BL.table_entry(2000 * 8, i, 2), (64, 42)):
                out.append((a >> 3, a & 7, words(n), True))
    elif pattern == "tables_rot":                  # DIAGNOSTIC: random rows, 2-block entries, sets rotate continuously
        for i in range(32 * n_layers):
            r = 2000 + rng.randrange(17000)
            out += [(r, (2 * i) % 8, words(64), True), (r, (2 * i + 1) % 8, words(42), True)]
    return out


def gen_ds_rot(n_layers, rng):
    """DS V4.1 L14 layer stream laid out by THE compiler function (hbm_bank_layout.layout_bw = smb_unit.layout_bw) (every
    kind starts on sets 0,1,2 and ends ...,5,6,7, so the next layer follows rotated).  (row, set, words, runtime_row)"""
    def layer(L):
        recs = []
        for (tag, b, l) in L14:
            recs.append(dict(tag=tag, slot=None, eid=None, blocks=[dict(n_lines=n) for n in split(b, l)]))
        ids = rng.sample(range(384), 6)
        for s_, e in enumerate(ids):
            recs.append(dict(tag="w13", slot=s_, eid=e, blocks=[dict(n_lines=R13)]))
        recs.append(dict(tag="shared.w2", slot=None, eid=None, blocks=[dict(n_lines=SH2)]))
        for e in rng.sample(ids, 6):
            recs.append(dict(tag="w2", slot=ids.index(e), eid=e, blocks=[dict(n_lines=R2)]))
        nonexp = [b for r in recs if r["slot"] is None for b in r["blocks"]]
        exp_blocks = {}
        for r in recs:
            if r["slot"] is not None:
                exp_blocks.setdefault(r["slot"], []).extend(r["blocks"])
        kd = dict(name="L14")
        BL.layout_bw(kd, recs, nonexp, exp_blocks, 0)
        kd["row_top_after"](800 + 8000 * L)          # one disjoint region per bench layer (row = addr >> 3 < 2^15)
        return [b for r in recs for b in r["blocks"]]
    out = []
    for L in range(n_layers):
        for b in layer(L):
            out.append((b["dram_row"] >> 3, b["dram_row"] & 7, words(b["n_lines"]), b["runtime_row"]))
    return out


def runtime_row(pattern, i, _cache={}):
    """is block i's DRAM row a runtime value (routed expert id / table index)?  (the check treats it as a new row)"""
    if pattern not in _cache:
        if pattern in CLASS_PATTERNS:
            _cache[pattern] = [rt for (*_, rt) in gen_class(pattern, 4, random.Random(1))]
        elif pattern in ("ds", "ds_nodup"):
            rt = []
            for L in range(4):
                rt += [it[0] in ("r13", "r2") for it in layer_ds(random.Random(1), L, pattern == "ds_nodup")]
            _cache[pattern] = rt
        else:
            _cache[pattern] = None
    v = _cache[pattern]
    return bool(v[i]) if v is not None and i < len(v) else False

def write_blk(blks, path):
    with open(path, "w") as f:
        for row, slot, w in blks:
            f.write("%07x\n" % ((row << 11) | (slot << 8) | w))

FILES = ["rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv", "rtl/hbm_accel/loader/service_native/ot_hbm_svc_ring_h9b.sv", "rtl/hbm_accel/loader/service_native/ot_hbm_svc_ring_bw_safe.sv", "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pin_skid2_h9.sv", "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pin_skid2_bw_safe.sv", "rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv", "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_safe.sv", "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg_safe.sv", "rtl/model_ready_hbm_r14/ot_hbm_r14_aq_pc_safe.sv", "rtl/test/hbm_accel/svg_rel/tb_hbm_bw_pc4.sv", "rtl/test/hbm_accel/svg_rel/tb_svg_rel_dram_sparse.sv",
         "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf.sv",
         "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg.sv",
         "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_mr.sv",
         "rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg_mr.sv",
         "rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv", "rtl/model_ready_hbm_r14/ot_hbm_r14_aq_pc_mr.sv",
         "rtl/lib/ot_rst_relay.sv", "rtl/lib/ot_rst_forest.sv",
         "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v", "rtl/hbm_accel/loader/service_native/ot_hbm_svc_sram128_n64.sv", "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_128x64_m1/ot_sram_1r1w2c_128x64_m1.v"]

def run(a):
    work = Path(a.work); work.mkdir(parents=True, exist_ok=True)
    defs = (["H9B"] if a.h9b else (["MR","SAFE"] if a.safe else (["MR"] if a.mr else []))) + (["MRKEY0"] if a.mrkey0 else []) + (["GAPS"] if a.gaps else [])
    defs += ["OT_PC_CFG_MUT_PC"] if a.pc_mut else []
    defs += ["BURST_GAPS"] if a.burst else []
    defs += ["EXPOSE"] if a.expose else []          # HBM-MC2: SAFE exposed-bank-latency census (observation only)
    defs += ["OT_PC_SAFE_MC3"] if a.mc3 else []    # HBM-MC3: pure face + reset forest + local pc_id copies
    tag = "_".join(defs) or "base"
    import hashlib
    h = hashlib.sha256(b"".join((ROOT / f).read_bytes() for f in FILES)).hexdigest()[:10]
    obj = work / f"obj_{tag}_{h}"                 # keyed by the bench + RTL sources
    vl = os.environ.get("VERILATOR", "verilator")
    if not (obj / "Vtb_hbm_bw_pc4").exists():
        cmd = [vl, "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--top-module", "tb_hbm_bw_pc4",
               "-O2", "--Mdir", str(obj), "-j", "8"] + [f"+define+{d}" for d in defs] + [str(ROOT / f) for f in FILES]
        r = subprocess.run(cmd, capture_output=True, text=True)
        (work / f"build_{tag}.log").write_text(r.stdout + r.stderr)
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-3000:]); raise SystemExit("build failed")
    blks = gen(a.pattern, a.layers, a.seed)
    bf = work / f"{a.pattern}_{a.seed}.blk"; write_blk(blks, bf)
    r = subprocess.run([str(obj / "Vtb_hbm_bw_pc4"), f"+BLK={bf}", f"+NB={len(blks)}", f"+WARM={a.warm}"],
                       capture_output=True, text=True)
    log = r.stdout + r.stderr
    name = f"{a.pattern}_{tag}_s{a.seed}"
    (work / f"{name}.log").write_text(log)
    m = re.search(r"^BW .*$", log, re.M)
    res = dict(schema="opentallas.hbm_bw_unit.v1", pattern=a.pattern, defines=defs, seed=a.seed, layers=a.layers,
               blocks=len(blks), rc=r.returncode, bw=m.group(0) if m else None,
               pcs=re.findall(r"^PC\d .*$", log, re.M), fault=re.findall(r"^(?:FAULT|%Error|.*fatal).*$", log, re.M)[:5],
               done=re.findall(r"^DONE .*$", log, re.M),
               expose=[dict((k, int(v)) for k, v in re.findall(r"(\w+)=(\d+)", l)) for l in re.findall(r"^EXPOSE .*$", log, re.M)])
    if m:
        kv = dict(re.findall(r"(\w+)=([\d.]+)", m.group(0)))
        res.update(B_per_edge=float(kv["B_per_edge"]), steady_B_per_edge=float(kv["steady_B_per_edge"]),
                   hbm_cycles=int(kv["hbm_cycles"]))
    (work / f"{name}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("pattern", "defines", "rc", "bw", "fault")}))
    if r.returncode or m is None:
        raise SystemExit(r.returncode or 1)

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    g = sp.add_parser("gen"); g.add_argument("--pattern", required=True); g.add_argument("--out", required=True)
    g.add_argument("--layers", type=int, default=4); g.add_argument("--seed", type=int, default=1)
    r = sp.add_parser("run"); r.add_argument("--work", required=True); r.add_argument("--pattern", required=True)
    r.add_argument("--burst", action="store_true"); r.add_argument("--pc-mut", action="store_true"); r.add_argument("--h9b", action="store_true"); r.add_argument("--safe", action="store_true"); r.add_argument("--mr", action="store_true"); r.add_argument("--mrkey0", action="store_true")
    r.add_argument("--gaps", action="store_true"); r.add_argument("--expose", action="store_true"); r.add_argument("--mc3", action="store_true"); r.add_argument("--layers", type=int, default=4)
    r.add_argument("--seed", type=int, default=1); r.add_argument("--warm", type=int, default=8)
    a = ap.parse_args()
    if a.cmd == "gen":
        blks = gen(a.pattern, a.layers, a.seed); Path(a.out).mkdir(parents=True, exist_ok=True)
        write_blk(blks, Path(a.out) / f"{a.pattern}.blk"); print(len(blks), "blocks")
    else:
        run(a)

if __name__ == "__main__":
    main()
