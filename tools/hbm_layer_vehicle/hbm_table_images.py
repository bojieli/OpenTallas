#!/usr/bin/env python3
"""HBM-ROTLAYOUT-TBL (10-19): runtime-indexed table images on the d4g vehicle (embedding rows, any table whose row index
is a runtime value) -- layout, image, readback, the ROTLAYOUT check -- and the per-die HBM capacity price.

Measured on the MC3b successor (tb_hbm_bw_pc4 +EXPOSE, Verilator 5.050; results/.../hbm_rotlayout_1019/census_tbl):
  * phase copies (v3 law: an nb-block entry stored 8 // nb times, copy j on sets j*nb .. j*nb+nb-1 of the entry's DRAM
    row index, lookup p reads the copy the layout gives it): 101.5 B/edge/SM on a long run;
  * one copy on the HEAD sets ("pingpong": every lookup on sets 0,1; R1/R2-clean) = 16.0 B/edge/SM (41-word blocks,
    48 exposed cyc/ACT, 875 refresh stalls/PC), 76.7 with 68-word blocks, 52-54 mixed into weight streams -> new check
    R4 in hbm_bank_layout (a: a new row on the set used 2 blocks earlier needs a >= 64-word block between; b: any 8
    consecutive blocks use >= 3 sets); one v3 KV run 0,1,2,1 (68-word blocks) a layer = 99.3 (R4-clean);
  * lookups as tokens of the first layer's stream (this module's law): DS 2 copies 101.2-101.8, Qwen 4 copies 103.8,
    Qwen 8 copies long run 96.0-97.4;
  * one copy on random home sets = 60.1 (v3 census, refused).

THE law (phase copies) and where lookups go:
  * entry = nb = ceil(lines / 64) balanced blocks; copies = the fewest of 1 / 2 / 4 / 8 // nb whose production
    streams pass (min_copies: DS 2, Qwen 4; 8 // nb = v3 fallback), copy j on sets j*nb + k;
  * a SHORT run (AR: 1 lookup, DS MTP: 2) cannot sit between two streams: every stream ends so that HEAD (sets 0,1,2)
    follows, and any 1..3-block run there breaks R2 or R4 (refused below).  Lookups are therefore TOKENS of the static
    stream they are scheduled in (the first layer's weight stream: the embedding is needed before its first matvec,
    the weight blocks do not depend on it): layout_stream lays the stream out by beam search, a lookup token takes
    the copy whose sets continue the rotation, weight blocks take the usual +1 / -1 / -2 / +2 / +3 steps, and the
    whole stream is checked (R1..R4) and wrapped into HEAD.  Long back-to-back runs (DFlash verify, 16) cycle copies.
  * rows far below a block (Engram 264 B) are not SM-block entries (an 8,704-B slot per 264-B row = 33x): they stay
    1-copy sector rows read by indexed DMA (9-channel-row law, HGI-1 sec 8), prefetched a token ahead.

The set sequence is a function of token POSITION only (never of a runtime id), so the compiler checks it statically.

  python3 tools/hbm_layer_vehicle/hbm_table_images.py selftest            # laws + images + refusals + fit
  python3 tools/hbm_layer_vehicle/hbm_table_images.py price [--out J]     # per-design table inventory and HBM fit
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hbm_bank_layout as BL  # noqa: E402

LINE_B = BL.LINE_B                        # 136-B SM line
BLOCK_LINES = 64                          # <= 64 lines a block
SLOT_B = 68 * 32 * 4                      # one block slot (row index, set) on the SM's 4 PCs = 8,704 B
NSETS = BL.NSETS
ROOT = Path(__file__).resolve().parents[2]
N_SM = 32                                 # die SMs; entry e of a die table is homed on SM e mod 32 (its 4 PCs)
ROW_FIELD = 1 << 15                       # descriptor row_base field (smb_unit desc_row: 15 bits)


def entry_lines(row_bytes):
    """balanced block split of one table row: [lines of block 0, ...] (nb = ceil(lines / 64))"""
    nl = -(-row_bytes // LINE_B)
    nb = -(-nl // BLOCK_LINES)
    base, extra = divmod(nl, nb)
    return [base + (1 if k < extra else 0) for k in range(nb)]


def copy_sets(nb, copies, j, family="packed"):
    """bank sets of copy j: packed = sets j*nb .. j*nb+nb-1 (copies adjacent from set 0, the v3 law); spread = copies
    spread evenly over the row index (stride 8 // copies sets)"""
    st = nb if family == "packed" else NSETS // copies
    return tuple((j * st + k) % NSETS for k in range(nb))


def plan(row_bytes, what="", copies=None, family="packed"):
    lines = entry_lines(row_bytes)
    nb = len(lines)
    if not 1 <= nb <= 4:
        raise BL.LayoutRefused(f"ROTLAYOUT REFUSED tables {what}: {nb}-block entries (1..4 supported)")
    c = copies or NSETS // nb
    if c * nb > NSETS or NSETS % c:
        raise BL.LayoutRefused(f"ROTLAYOUT REFUSED tables {what}: {c} copies of {nb} blocks do not tile 8 sets")
    return dict(row_bytes=row_bytes, lines=lines, nb=nb, law="phase", copies=c, slots=c * nb, family=family,
                bytes_per_entry=c * nb * SLOT_B, read_bytes_per_lookup=row_bytes, what=what,
                copy_sets=[copy_sets(nb, c, j, family) for j in range(c)])


def home(e):
    """(SM, local entry) of die-table entry e: a lookup run splits into per-SM sub-runs in fetch order"""
    return e % N_SM, e // N_SM


# ------------------------------------------------------------------------------------------------ stream layout
def layout_stream(tokens, plans, what="", beam=3000, heads=None, tails=None):
    """tokens in fetch order: ('ne', words) static block | ('t', table) one lookup of plans[table].  Beam search: the
    first blocks are HEAD (0, 1, 2); an ne block steps +1 (free) or -1 / -2 / +2 / +3 (one deviation); a lookup takes any
    copy (free if its first set continues +1); every block keeps R1..R4 (hbm_bank_layout._r1 / _r2), the first blocks
    also behind each of `tails` (the actual last blocks [(set, words)] of every stream that may precede), and the stream
    wraps into HEAD or each of `heads` (the actual first blocks of every stream that may follow).
    -> dict(sets per token, copies per lookup, deviations, seq [(None, set, words)], check) or LayoutRefused"""
    heads = heads or [[(h, 68) for h in BL.HEAD]]
    tails = tails or []
    win = max(BL.T_HIDE, BL.REF_WIN) + 68
    states = [((), 0, [])]
    nblk, wsum = 0, 0
    for i, t in enumerate(tokens):
        nxt = {}
        if t[0] == "ne":
            items = [None]
        else:
            pl = plans[t[1]]
            items = list(pl["copy_sets"])
        for seq, dev, path in states:
            prev = seq[-1][1] if seq else None
            for j, cs in enumerate(items):
                if t[0] == "ne":
                    ws = (t[1],)
                    if nblk < len(BL.HEAD):
                        opts = [((BL.HEAD[nblk],), 0)]
                    else:
                        opts = [(((prev + st) % NSETS,), int(st != 1)) for st in (1, 7, 6, 2, 3)]
                else:
                    ws = tuple(BL.words(n) for n in plans[t[1]]["lines"])
                    if any(s_ != BL.HEAD[nblk + k] for k, s_ in enumerate(cs) if nblk + k < len(BL.HEAD)):
                        continue
                    opts = [(cs, 0 if prev is None or cs[0] == (prev + 1) % NSETS else 1)]
                for sets_, dd in opts:
                    sq, good, w0 = seq, True, wsum
                    for s_, w in zip(sets_, ws):
                        sq = sq + ((None, s_, w),)
                        k = len(sq) - 1
                        if BL._r1(sq, k) is not None or BL._r2(sq, k) is not None:
                            good = False
                            break
                        if w0 < win:
                            for tl in tails:
                                full = tuple((None, a, b) for a, b in tl) + sq
                                if BL._r1(full, len(full) - 1) is not None or BL._r2(full, len(full) - 1) is not None:
                                    good = False
                                    break
                            if not good:
                                break
                        w0 += w
                    if not good:
                        continue
                    acc, cut = 0, len(sq)
                    while cut > 0 and acc < win:
                        cut -= 1
                        acc += sq[cut][2]
                    key = tuple(x[1:] for x in sq[cut:])
                    cand = (sq[cut:] if w0 >= win else sq, dev + dd, path + [(sets_, j if t[0] == "t" else None)])
                    if key not in nxt or nxt[key][1] > cand[1]:
                        nxt[key] = cand
        if t[0] == "ne":
            nblk, wsum = nblk + 1, wsum + t[1]
        else:
            nblk += plans[t[1]]["nb"]
            wsum += sum(BL.words(n) for n in plans[t[1]]["lines"])
        states = sorted(nxt.values(), key=lambda c: c[1])[:beam]
        if not states:
            raise BL.LayoutRefused(f"ROTLAYOUT REFUSED tables {what}: no rotated assignment at token {i} {t}")

    def wrap_ok(seq):
        tail = list(seq[-BL.REF_BACK:])
        for hd in heads:
            full = tail + [(None, h, w) for (h, w) in hd]
            if not all(BL._r1(full, k) is None and BL._r2(full, k) is None for k in range(len(tail), len(full))):
                return False
        return True
    good = [c for c in states if wrap_ok(c[0])]
    if not good:
        raise BL.LayoutRefused(f"ROTLAYOUT REFUSED tables {what}: no assignment of {len(tokens)} tokens wraps into the heads")
    _, dev, path = good[0]
    full = []
    for t, (sets_, j) in zip(tokens, path):
        ws = (t[1],) if t[0] == "ne" else tuple(BL.words(n) for n in plans[t[1]]["lines"])
        full += [(None, s_, w) for s_, w in zip(sets_, ws)]
    res = BL.check_stream("tables" if any(t[0] == "t" for t in tokens) else "weights", full, what)
    for hd in heads:
        BL.check_stream(res["cls"], [(None, s_, w) for (_, s_, w) in full[-BL.REF_BACK:]] + [(None, h, w) for h, w in hd],
                        what + " +wrap")
    return dict(sets=[p[0] for p in path], copies=[p[1] for p in path if p[1] is not None], deviations=dev,
                seq=full, check=res)


HEAD_RUN = 16                             # full blocks of the LM-head stream the census puts before each token


def head_run_tail():
    """the stream that precedes a token's embedding lookups is the previous token's LM-head run (embed_head class:
    full 64-line blocks, laid out rotated by static_run): its last blocks [(set, words)]"""
    sets_, _, _ = BL.assign_sets([("ne", 68)] * HEAD_RUN, "embed_head", "lm head run")
    return [(s_, 68) for s_ in sets_[-BL.REF_BACK:]], sets_


def token_streams(design, pl, ks, name="emb"):
    """production order: ... LM-head run | k lookups + first-layer weight blocks | next kind (HEAD) ...: lay out the
    lookup stream of every run length k behind the actual LM-head tail -> {k: layout_stream result}"""
    tail, _ = head_run_tail()
    return {k: layout_stream(stream_tokens(design, {name: pl}, name, k), {name: pl}, f"{design} {pl['what']} k{k}",
                             tails=[tail]) for k in ks}


def lookup_run_standalone(pl, k, what=""):
    """a run of k lookups as its OWN stream (copies cycled 0, 1, ...; HEAD start, wrap into HEAD): legal only for long
    runs (k a multiple of the copies) -- short runs are refused and must be tokens of a stream (layout_stream)"""
    seq = []
    for p in range(k):
        for s_, n in zip(pl["copy_sets"][p % pl["copies"]], pl["lines"]):
            seq.append((None, s_, BL.words(n)))
    return BL.check_wrapped("tables", seq, f"{what} standalone k{k}")


# ------------------------------------------------------------------------------------------------ image compiler
class Allocator:
    """block-address allocator of one SM's 4 PCs: a table entry owns one row index (its copies' slots); static runs
    take free slots per set (rows need not ascend: the check sees every static block as its own row)"""

    def __init__(self, row0=0, rows=ROW_FIELD):
        self.row0, self.rows, self.used = row0, rows, set()

    def table(self, name, n_entries, pl):
        base = self.row0
        sets = sorted({s_ for cs in pl["copy_sets"] for s_ in cs})
        for e in range(n_entries):
            for s_ in sets:
                a = BL.block_address(base + e, s_)
                assert a not in self.used, ("table slot alias", name, a)
                self.used.add(a)
        self.row0 = base + n_entries
        if self.row0 > self.rows:
            raise SystemExit(f"table {name}: {n_entries} entries overflow the {self.rows}-row block address field")
        return base

    def static(self, sets, start=0):
        out, cur = [], {}
        for s_ in sets:
            a = cur.get(s_, (start & ~7) | s_)
            while a in self.used:
                a += 8
            self.used.add(a)
            cur[s_] = a + 8
            out.append(a)
        return out


def compile_table(name, rows, pl, alloc):
    """HBM image of one SM's table slice: {block address: bytes (lines x 136, zero padded)}, every entry x copy"""
    base = alloc.table(name, len(rows), pl)
    img = {}
    for e, row in enumerate(rows):
        row = bytes(row).ljust(sum(pl["lines"]) * LINE_B, b"\0")
        for cs in pl["copy_sets"]:
            off = 0
            for s_, n in zip(cs, pl["lines"]):
                img[BL.block_address(base + e, s_)] = row[off:off + n * LINE_B]
                off += n * LINE_B
    return img, base


def lookup_addrs(pl, base, e, j):
    """[(block address, lines)] of a lookup of local entry e that reads copy j (j from layout_stream)"""
    return [(BL.block_address(base + int(e), s_), n) for s_, n in zip(pl["copy_sets"][j], pl["lines"])]


def readback(img, pl, base, e, j):
    """bytes a lookup of entry e through copy j returns (the gather the d4g issuer performs)"""
    return b"".join(img[a] for a, _ in lookup_addrs(pl, base, e, j))


# ------------------------------------------------------------------------------------------------ the price
GB = 1e9
HBM_PER_DIE = dict(stacks=4, gb_per_stack=36.0, src="docs/HBM_GENERIC_INTERFACE.md Table 9-1 (144 GB = 4 x 36 GB)")


def inventory():
    """every table the two HBM designs place in HBM, per die (sources: configs/models/candidates, tools/hgi_sim)"""
    ds = json.loads((ROOT / "configs/models/candidates/deepseek-v4.1-flash-engram_hbm.json").read_text())
    md = ds["metadata"]
    TP_DS, TP_Q = 96, 4
    V_DS, H_DS = md["operator_config"]["vocab_size"], ds["hidden_size"]
    eng = md["hbm_resident_regions"]
    Q = dict(vocab=151936, hidden=4096, layers=36, kv_heads=8, head_dim=128, ctx=40960)
    q_emb_row = -(-(Q["hidden"] + 2) // 32) * 32                       # qwen_compiler emb_row = al(H + 2) = 4,128 B
    q_lin = Q["layers"] * ((Q["hidden"] + 2 * 1024) * Q["hidden"] + Q["hidden"] ** 2 + 3 * 12288 * Q["hidden"])
    designs = {
        "HBM-DS": dict(
            model="DeepSeek-V4.1-Flash", dies=TP_DS, tp=TP_DS,
            tables=[
                dict(name="embedding", rows=V_DS, row_bytes=2 * H_DS, per_die="replicated (full hidden row per die)",
                     lookups=dict(AR=1, MTP=2), path="indexed DMA.LOAD at TOKEN x 10,240 B (HGI-1 sec 7)"),
                dict(name="engram_l1", rows=-(-int(eng[0]["rows"]) // TP_DS), row_bytes=int(eng[0]["row_bytes"]),
                     per_die="rows owned by id mod 96 (w19 f_engram_fetch)", lookups=dict(AR=1, MTP=2),
                     path="indexed DMA.LOAD per hashed id; 24 ids/token over 96 owners = 0.25 avg, <= 24 max a die",
                     prefetch="ids from the last 4 token ids: issued a token ahead (0 token-path cycles)"),
                dict(name="engram_l14", rows=-(-int(eng[1]["rows"]) // TP_DS), row_bytes=int(eng[1]["row_bytes"]),
                     per_die="rows owned by id mod 96", lookups=dict(AR=1, MTP=2), path="as engram_l1",
                     prefetch="as engram_l1"),
            ],
            static=[
                dict(name="LM head", bytes=V_DS * H_DS * 2 / TP_DS, note="row-sharded, streamed in full every token "
                     "(embed_head class, static rotated run, 103.9 B/edge/SM) -- not row-gathered, no copies"),
                dict(name="RoPE / norm / sink / bias tables", bytes=1048576 * 64 * 4 / 1, note="POS-indexed rows: "
                     "consecutive positions = consecutive rows, laid out as a static rotated run (no copies)"),
                dict(name="routed experts x3 position copies (hbm_bank_layout triples)", bytes=3 * ds["routed_weight_bytes"] / TP_DS,
                     note="v3 law: 3 copies of every routed block (capacity priced here: 3 x 3.01 GB)"),
                dict(name="dense + shared + MTP weights", bytes=(ds["dense_weight_bytes"] + ds["draft_dense_weight_bytes"]
                                                                 + ds["draft_routed_weight_bytes"]) / TP_DS, note="static runs"),
                dict(name="KV (1M ctx, 4 users)", bytes=4 * md["global_kv_bytes_per_token"] * ds["max_context_tokens"] / TP_DS
                     + 4 * 40 * 128 * 528, note="global KV 890 B/token rank-sharded + SWA window"),
            ]),
        "HBM-Qwen": dict(
            model="Qwen3-8B INT8", dies=TP_Q, tp=TP_Q,
            tables=[
                dict(name="embedding", rows=Q["vocab"], row_bytes=q_emb_row, per_die="replicated",
                     lookups=dict(AR=1, DFlash_b8=8, DFlash_b16=16), path="indexed DMA.LOAD codes + BF16 scale "
                     "(qwen_compiler emb_row 4,128 B); DFlash verify = 16 indexed loads on the draft ids"),
            ],
            static=[
                dict(name="LM head", bytes=Q["vocab"] * Q["hidden"] * 1.0 / TP_Q, note="row-sharded INT8, streamed in full"),
                dict(name="layer weights INT8 + scales", bytes=q_lin * 1.0 / TP_Q, note="static runs (qwen class 103.95)"),
                dict(name="KV FP8 (40,960 ctx, 4 users)", bytes=4 * Q["layers"] * 2 * 2 * Q["head_dim"] * Q["ctx"],
                     note="2 KV heads a die (TP4)"),
                dict(name="RoPE / norm tables", bytes=Q["ctx"] * Q["head_dim"] * 4, note="POS-indexed static rows"),
            ]),
    }
    return designs


def first_stream(design):
    """the static stream a table lookup run is a token of: the first layer's weight blocks (lines) of that design"""
    import hbm_bw_unit as B
    if design == "HBM-DS":
        return [n for (_, bb, ll) in B.L14 for n in B.split(bb, ll)] + [B.SH2]
    return [n for (_, K, m) in B.QWEN_SM for n in B._lines(-(-m // 16) * (K // 128))]


def stream_tokens(design, plans, name, k):
    """k lookups at the head of the first layer's stream (the embedding is consumed by its first matvec)"""
    return [("t", name)] * k + [("ne", BL.words(n)) for n in first_stream(design)]


def min_copies(design, t, plans_out=None):
    """fewest copies c (1, 2, 4, 8 // nb) whose layout_stream passes for every run length the design issues"""
    nb = len(entry_lines(t["row_bytes"]))
    res = []
    for c, fam in [(c, f) for c in sorted({c for c in (1, 2, 4, NSETS // nb) if c * nb <= NSETS})
                   for f in (("packed", "spread") if 1 < c < NSETS // nb else ("packed",))]:
        pl = plan(t["row_bytes"], t["name"], copies=c, family=fam)
        try:
            ks = sorted(set(t["lookups"].values()))
            lay = token_streams(design, pl, ks, t["name"])
            res.append(dict(copies=c, family=fam, verdict="ROTATED",
                            runs={str(n): dict(copies_used=v["copies"], deviations=v["deviations"]) for n, v in lay.items()}))
            return pl, res
        except BL.LayoutRefused as e:
            res.append(dict(copies=c, family=fam, verdict="REFUSED", why=str(e)[:200]))
    raise BL.LayoutRefused(f"ROTLAYOUT REFUSED tables {design} {t['name']}: no copy count passes {res}")


def price():
    cap = HBM_PER_DIE["stacks"] * HBM_PER_DIE["gb_per_stack"] * GB
    out = dict(schema="opentallas.hbm_table_price.v1", hbm_per_die=HBM_PER_DIE, slot_bytes=SLOT_B, designs={})
    for dn, d in inventory().items():
        rows_out, tot = [], dict(v3_phase_all=0.0, v3_phase=0.0, chosen=0.0, raw=0.0)
        for t in d["tables"]:
            lines = entry_lines(t["row_bytes"])
            nb = len(lines)
            per_sm = -(-t["rows"] // N_SM)
            r = dict(t, lines=lines, nb=nb, raw_GB=t["rows"] * t["row_bytes"] / GB,
                     v3_phase_copies=NSETS // nb, v3_phase_GB=t["rows"] * NSETS * SLOT_B / GB,
                     row_indices_per_sm=per_sm, row_field_ok=per_sm <= ROW_FIELD)
            if t["row_bytes"] < 8 * LINE_B:
                # a row far below one block: block slots waste > 8x; read as 1-copy sector rows by indexed DMA
                r["chosen"] = dict(law="sector_rows", copies=1, GB=r["raw_GB"],
                                   why=f"{t['row_bytes']}-B rows: one {SLOT_B}-B block slot each would be "
                                       f"{SLOT_B / t['row_bytes']:.0f}x the row ({r['v3_phase_GB']:.0f} GB/die with the "
                                       f"v3 copies, row field {per_sm:,} > {ROW_FIELD:,}); {t.get('prefetch', '')}")
                tot["v3_phase"] += r["raw_GB"]
            else:
                pl, tried = min_copies(dn, t)
                r["chosen"] = dict(law="phase", copies=pl["copies"], family=pl["family"], slots=pl["slots"],
                                   copy_sets=pl["copy_sets"],
                                   GB=t["rows"] * pl["bytes_per_entry"] / GB, tried=tried)
                tot["v3_phase"] += r["v3_phase_GB"]
            rows_out.append(r)
            tot["raw"] += r["raw_GB"]
            tot["v3_phase_all"] += r["v3_phase_GB"]
            tot["chosen"] += r["chosen"]["GB"]
        static = sum(x["bytes"] for x in d["static"]) / GB
        fit = {k: dict(tables_GB=round(v, 3), total_GB=round(v + static, 3), cap_GB=cap / GB,
                       util=round((v + static) / (cap / GB), 4), fits=(v + static) * GB <= cap) for k, v in tot.items()}
        out["designs"][dn] = dict(model=d["model"], dies=d["dies"], tables=rows_out,
                                  static=[dict(x, GB=round(x["bytes"] / GB, 3)) for x in d["static"]],
                                  static_GB=round(static, 3), fit=fit)
    return out


def print_price(p):
    for dn, d in p["designs"].items():
        print(f"== {dn} ({d['model']}, {d['dies']} dies, HBM {p['hbm_per_die']['stacks']} x "
              f"{p['hbm_per_die']['gb_per_stack']:.0f} GB / die)")
        for t in d["tables"]:
            c = t["chosen"]
            print(f"  table {t['name']:11s} rows/die {t['rows']:>11,} row {t['row_bytes']:>6,} B  raw "
                  f"{t['raw_GB']:8.3f} GB | v3 {t['v3_phase_copies']} phase copies {t['v3_phase_GB']:9.3f} GB | "
                  f"chosen {c['law']} x{c['copies']} {c['GB']:8.3f} GB  lookups {t['lookups']}")
            for tr in c.get("tried", []):
                print(f"      copies {tr['copies']} {tr['family']}: {tr['verdict']} {tr.get('runs', tr.get('why', ''))}")
        for s in d["static"]:
            print(f"  static {s['name']:52s} {s['GB']:8.3f} GB")
        for k, f in d["fit"].items():
            print(f"  fit [{k:9s}] tables {f['tables_GB']:9.3f} + static {d['static_GB']:7.3f} = {f['total_GB']:9.3f} GB "
                  f"of {f['cap_GB']:.0f} ({100 * f['util']:.1f} %) {'FITS' if f['fits'] else 'DOES NOT FIT'}")


# ------------------------------------------------------------------------------------------------ selftest
def _selftest():
    ok = True

    def expect(cond, msg):
        nonlocal ok
        ok &= bool(cond)
        print(("ok  " if cond else "BAD ") + msg)

    def refused(fn, msg):
        try:
            fn()
            expect(False, f"{msg} must be REFUSED")
        except BL.LayoutRefused as e:
            expect(True, f"REFUSED {msg}: {str(e)[:150]}")

    pds, pq = plan(10240, "DS embedding"), plan(4128, "Qwen embedding")
    expect(pds["lines"] == [38, 38] and pds["copies"] == 4, f"DS 10,240-B rows: {pds['lines']} x{pds['copies']} copies")
    expect(pq["lines"] == [31] and pq["copies"] == 8, f"Qwen 4,128-B rows: {pq['lines']} x{pq['copies']} copies")
    # measured refusals (census_tbl / census_mc3b)
    pp = [(None, s_, 41) for _ in range(8) for s_ in (0, 1)]
    refused(lambda: BL.check_stream("tables", pp, "pingpong 1 copy on sets 0,1 (measured 16.0 B/edge)"),
            "pingpong (1 copy on the HEAD sets)")
    # long standalone runs pass, short ones (AR 1, MTP 2) are refused: lookups must be stream tokens
    for k in (16, 32, 64):
        lookup_run_standalone(plan(14416, "v3 shape"), k, "v3")
    expect(True, "standalone phase x4 (v3 64+42 shape) runs of 16/32/64 pass")
    refused(lambda: lookup_run_standalone(pds, 1, "DS AR"), "standalone 1-lookup run (DS AR)")
    refused(lambda: lookup_run_standalone(pds, 2, "DS MTP"), "standalone 2-lookup run (DS MTP)")
    refused(lambda: lookup_run_standalone(pq, 1, "Qwen AR"), "standalone 1-lookup run (Qwen AR)")
    # lookups as tokens of the first layer's stream
    for dn, pl, ks in (("HBM-DS", pds, (1, 2)), ("HBM-Qwen", pq, (1, 8, 16))):
        lay = token_streams(dn, pl, ks)
        for k, v in lay.items():
            expect(v["check"]["verdict"] == "ROTATED", f"{dn} LM-head run | {k} lookup(s) + first-layer stream: copies "
                                                       f"{v['copies']}, {v['deviations']} phase steps, sets "
                                                       f"{[x[1] for x in v['seq'][:k + 4]]}...")
    # image compile + readback, static data packed into the free slots
    rng = random.Random(7)
    for pl, n in ((pds, 200), (pq, 200)):
        al = Allocator(row0=100)
        rows = [bytes(rng.randrange(256) for _ in range(pl["row_bytes"])) for _ in range(n)]
        img, base = compile_table("t", rows, pl, al)
        free = al.static([s_ % 8 for s_ in range(40)], start=100 * 8)
        good = all(readback(img, pl, base, e, j)[:pl["row_bytes"]] == rows[e]
                   for e in rng.sample(range(n), 20) for j in range(pl["copies"]))
        expect(good and len(img) == n * pl["slots"] and not set(free) & set(img),
               f"{pl['what']}: image {len(img)} slots ({pl['copies']} copies), every copy reads back exact, "
               f"40 static blocks outside the table slots")
    p = price()
    for dn, d in p["designs"].items():
        f = d["fit"]["chosen"]
        expect(f["fits"], f"{dn}: tables + static {f['total_GB']} GB of {f['cap_GB']:.0f} GB per die ({100 * f['util']:.1f} %)")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["selftest"]:
        raise SystemExit(_selftest())
    if a[:1] == ["price"]:
        p = price()
        print_price(p)
        if "--out" in a:
            Path(a[a.index("--out") + 1]).write_text(json.dumps(p, indent=1) + "\n")
        raise SystemExit(0)
    print(__doc__)
