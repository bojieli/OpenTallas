#!/usr/bin/env python3
"""HBM-ROTLAYOUT (owner rule 2026-10-19): the ONE HBM bank layout of every stream the d4g compiler places, and the
compiler check that refuses any stream that is not rotated across bank sets.

Why (RTL-measured, claude/l2h-bw-safe-1019 89200325b exposed_bank/README.md and results/rtl/hbm_ds_layer_tput_1018/
hbm_rotlayout_1019, tb_hbm_bw_pc4 +EXPOSE on the MC3 successor): the successor PC controller (ot_hbm_r14_aq_pc_safe:
one open row per bank, QD64 ACT lookahead, columns strictly in compiler order, REFpb on the bank-set FARTHEST AHEAD of
the newest queued entry's set) hides tRP+tRCD and refresh ONLY when the fetch order advances the bank set cyclically.
Every block on one set (as-built row-per-block) = 26 B/edge; random set order (runtime-indexed table rows on their home
set) = 60-64 B/edge (refresh lands on the next block's set: ~200-cycle stalls); cyclic rotation = 92-104.

Address law (rtl ot_hbm_svc_prefetch_overlap_owner_rel_id.sv:51-62, leaf ot_hbm_svc_pc_ctrl_leaf_cfg_safe.sv:405):
an SM block (<= 64 136-B lines = <= 68 32-B words per PC, on the SM's four PCs) has an 18-bit BLOCK ADDRESS
{row[17:3], set[2:0]}; descriptor base[9:7] = set = the physical bank set bank[4:2] of the block on each of its PCs
(the owner's bhi = set ^ row[4:2] XOR is undone in the leaf), bank[1:0] = word t[1:0], col = t[6:2]; i.e. block address
a is DRAM row a >> 3, set a & 7 (smb_unit: sector_address(o + 512 * (a & 7), row_base = a >> 3)).

THE layout (assign_sets; every stream class):
  * every stream (kind / layer stream / KV run / table-lookup run) STARTS on set 0, 1, 2 and steps the set by +1 a
    block; a few evenly spaced phase steps of -2 or -1 (never in the first three; the fewest that pass) let the stream
    END so that ANY stream may follow ANY stream (kind -> kind, layer -> layer, weights -> KV) without a refresh or row
    conflict (a 1-block stream is refused: merge it into a neighbour stream);
  * routed experts (runtime ids): routed block kind b_i reads copy p mod 3 of its p-th fetch-order occurrence; the copy
    triple is the three sets after the block before its first occurrence (DS L14: w1+w3 on 1/2/3, w2 on 5/6/7), so the
    set is a function of the routed POSITION, never of the id (experts stored three times: capacity, not bandwidth);
  * runtime-indexed tables (embedding rows, engram rows, other lookup tables): entry e of nb <= 4 blocks owns one DRAM
    row index with 8 // nb phase copies; the p-th lookup of a run reads copy p mod (8 // nb), so lookups rotate the set
    exactly like a static run (capacity x 8 // nb, priced separately).

Check (check_stream), from the controller contract (aq_pc_safe.sv:14-20): in a stream's fetch order
  R1 two blocks on the same set with different rows are separated by >= T_HIDE (35 = tRP 16 + tRCD 19) column words;
  R2 no block's set is d = 4 or 5 ahead (mod 8) of any of the three blocks before it -- those are the sets REFpb may be
     refreshing (LEAD + tRFCpb = 244 cycles) when the earlier block was the newest queued entry (protected d = 6,7,0..3);
  R3 a stream of > 1 block uses more than one set.
Any violation is a refusal (SystemExit 'ROTLAYOUT REFUSED'), not a warning: the compiler never emits an unrotated stream.

  python3 tools/hbm_layer_vehicle/hbm_bank_layout.py selftest      # measured layouts: rotated PASS, unrotated REFUSED
"""
from __future__ import annotations

import sys

NSETS = 8                      # bank sets per PC = bank[4:2] (32 banks = 8 sets x 4)
T_HIDE = 35                    # tRP 16 + tRCD 19 HBM cycles (tb_svg_rel_dram_sparse / cfg_safe HBM3-class timing)
REF_UNPROT = (4, 5)            # aq_pc_safe.sv:414: prot = d >= 6 || d <= 3, d = set - tail_set (mod 8)
REF_BACK = 3                   # blocks back R2 looks (a refreshed bank is not needed for >= 4 blocks)
CLASSES = ("weights", "experts", "kv", "embed_head", "tables")
HEAD = (0, 1, 2)               # every stream starts here (the wrap check appends it after every stream's tail)
LINE_B, WORD_B = 136, 128


class LayoutRefused(SystemExit):
    pass


def words(lines):
    """per-PC 32-B words of a block of `lines` 136-B lines (issuer total = ceil(lines*136/128)*4 sectors over 4 PCs)"""
    return -(-lines * LINE_B // WORD_B)


def block_address(row, bank_set):
    assert 0 <= bank_set < NSETS
    return (row << 3) | bank_set


def split(addr):
    """block address -> (DRAM row, bank set)"""
    return addr >> 3, addr & 7


# ------------------------------------------------------------------------------------------------ the check
def check_stream(cls, seq, what="", t_hide=T_HIDE):
    """seq = fetch order [(row | None, set, words)]; row None = runtime (routed expert / table entry) = a row different
    from every other.  Returns a summary dict or raises LayoutRefused."""
    if cls not in CLASSES:
        raise LayoutRefused(f"ROTLAYOUT REFUSED {what}: unknown stream class {cls!r} (classes {CLASSES})")
    sets_used = set()
    for i, (r, s, w) in enumerate(seq):
        if not 0 <= s < NSETS:
            raise LayoutRefused(f"ROTLAYOUT REFUSED {cls} {what}: block {i} bank set {s} outside 0..{NSETS - 1}")
        sets_used.add(s)
        acc = 0
        for j in range(i - 1, -1, -1):                                   # R1
            rj, sj, wj = seq[j]
            if sj == s and (r is None or rj is None or rj != r):
                raise LayoutRefused(
                    f"ROTLAYOUT REFUSED {cls} {what}: R1 block {i} (row {r}, set {s}) follows block {j} (row {rj}, same "
                    f"set) with only {acc} column words between (< T_HIDE {t_hide}): not rotated across bank sets")
            acc += wj
            if acc >= t_hide:
                break
        for j in range(max(0, i - REF_BACK), i):                          # R2
            d = (s - seq[j][1]) % NSETS
            if d in REF_UNPROT:
                raise LayoutRefused(
                    f"ROTLAYOUT REFUSED {cls} {what}: R2 block {i} set {s} is {d} sets ahead of block {j} (set "
                    f"{seq[j][1]}, {i - j} back): REFpb may hold that set (not a cyclic rotation)")
    if len(seq) > 1 and len(sets_used) < 2:                               # R3
        raise LayoutRefused(f"ROTLAYOUT REFUSED {cls} {what}: R3 all {len(seq)} blocks on bank set {sets_used}")
    return dict(cls=cls, what=what, blocks=len(seq), sets=sorted(sets_used), t_hide=t_hide, verdict="ROTATED")


def check_wrapped(cls, seq, what=""):
    """the stream itself AND the stream followed by any stream (every stream starts on HEAD)"""
    check_stream(cls, seq, what)
    tail = seq[-REF_BACK:]
    return check_stream(cls, [(None, s, w) for (_, s, w) in tail] + [(None, s, 68) for s in HEAD], what + " +wrap")


def check_addrs(cls, addrs, wds, what=""):
    """check a static stream given as block addresses + per-block words (and its wrap into any next stream)"""
    return check_wrapped(cls, [(a >> 3, a & 7, w) for a, w in zip(addrs, wds)], what)


def require_all(results):
    seen = {r["cls"] for r in results}
    return dict(classes_checked=sorted(seen), all_rotated=all(r["verdict"] == "ROTATED" for r in results))


# ------------------------------------------------------------------------------------------------ the layout
def assign_sets(tokens, cls="weights", what="", max_adj=12):
    """tokens = fetch order [('ne', words) | ('r', b_i, words)] -> (sets, triples, phase steps).  ne blocks step +1
    (-2 at the chosen phase positions); routed block kind b_i cycles its copy triple.  The first assignment (fewest
    phase steps) whose stream + wrap passes check_stream wins; none -> LayoutRefused."""
    ne_idx = [i for i, t in enumerate(tokens) if t[0] == "ne" and i >= len(HEAD)]
    last_err = None
    cands = [(0, 0, 6)]
    for nadj in range(1, max_adj + 1):
        if len(ne_idx) < nadj:
            break
        for step in (6, 7):                        # phase step -2 or -1
            for shift in range(0, 3):
                cands.append((nadj, shift, step))
    for (nadj, shift, step) in cands:
        if True:
            adj = set()
            if nadj:
                stride = max(1, len(ne_idx) // nadj)
                adj = {ne_idx[min(len(ne_idx) - 1, k * stride + shift)] for k in range(nadj)}
                if len(adj) < nadj:
                    continue
            sets, triples, pos, prev = [], {}, {}, None
            for i, t in enumerate(tokens):
                if t[0] == "ne":
                    s = 0 if prev is None else (prev + (step if i in adj else 1)) % NSETS
                else:
                    b = t[1]
                    if b not in triples:
                        base = 0 if prev is None else (prev + 1) % NSETS
                        triples[b] = tuple((base + k) % NSETS for k in range(3))
                    s = triples[b][pos.get(b, 0) % 3]
                    pos[b] = pos.get(b, 0) + 1
                sets.append(s)
                prev = s
            tv = list(triples.values())
            if any(set(a) & set(b) for x, a in enumerate(tv) for b in tv[x + 1:]):
                last_err = "routed copy triples overlap"
                continue
            seq = [(None, s, t[-1]) for s, t in zip(sets, tokens)]
            try:
                check_wrapped(cls, seq, what)
            except LayoutRefused as e:
                last_err = str(e)
                continue
            return sets, triples, nadj
    raise LayoutRefused(f"ROTLAYOUT REFUSED {cls} {what}: no rotated assignment ({last_err})")


def static_run(base, line_list, cls="weights", what=""):
    """block addresses of a static run (weights / KV / LM head) laid out rotated from block address base (multiple
    of 8): block i at the next free address > previous whose set is sets[i]"""
    assert base % NSETS == 0
    sets, _, nadj = assign_sets([("ne", words(n)) for n in line_list], cls, what)
    out, p = [], base - 1
    for s in sets:
        p += 1
        while p % NSETS != s:
            p += 1
        out.append(p)
    return out, nadj


def table_copies(nb):
    if not 1 <= nb <= 4:
        raise LayoutRefused(f"ROTLAYOUT REFUSED tables: {nb}-block entries (1..4 supported)")
    return NSETS // nb


def table_entry(base_row, e, nb, position):
    """block addresses of the position-th lookup (entry e, nb blocks) of a runtime-indexed table run: entry e owns DRAM
    row base_row + e, its 8 // nb phase copies fill the row's eight sets; lookup p reads copy p mod (8 // nb)"""
    c = position % table_copies(nb)
    return [block_address(base_row + e, c * nb + k) for k in range(nb)]


def layout_bw(kd, recs, nonexp, exp_blocks, L, nexp=384):
    """The d4g SM block layout of one compiled kind (smb_unit calls it; HBM-BW layout generalised by HBM-ROTLAYOUT).
    The sub-row slot of a block address IS the physical bank set; strides that are multiples of 8 keep it per layer and
    per expert.  Sets come from assign_sets over the kind's fetch order (record order, blocks in wave order); routed
    block b_i of the p-th routed occurrence reads copy p mod 3 (one DRAM row index per expert and layer holds all its
    copies: DS L14 w1+w3 on sets 1/2/3 and w2 on 5/6/7).  Mutates the block dicts (row_base, layer_stride, id_sel,
    expert_stride, dram_row = block address, bank_set, runtime_row); returns nothing (kd['row_top_after'])."""
    order = [b for r in recs for b in r["blocks"]]
    routed = {}
    for s_, bl in exp_blocks.items():
        for b_i, b in enumerate(bl):
            routed[id(b)] = (s_, b_i)
    toks = [("r", routed[id(b)][1], words(b["n_lines"])) if id(b) in routed else ("ne", words(b["n_lines"]))
            for b in order]
    sets, triples, nadj = assign_sets(toks, "weights", f"kind {kd.get('name')}")
    want = {id(b): s for b, s in zip(order, sets)}
    p, offs = -1, {}
    for b in order:
        if id(b) in routed:
            continue
        p += 1
        while p % 8 != want[id(b)]:
            p += 1
        offs[id(b)] = p
    lstride = 8 * (p // 8 + 1)
    kd["rotlayout"] = dict(sets=sets, triples={str(k): v for k, v in triples.items()}, phase_steps=nadj)

    def after(row_top):
        kbase = row_top
        top = row_top + lstride * (max(L, 0) + 1)
        kd.update(lstride=lstride, kbase=kbase, estride=8 if exp_blocks else 0)
        for b in nonexp:
            b.update(row_base=kbase + offs[id(b)], layer_stride=lstride, id_sel=0, expert_stride=0,
                     dram_row=kbase + L * lstride + offs[id(b)], bank_set=offs[id(b)] % 8, runtime_row=False)
        kd["exp"] = {}
        if exp_blocks:
            elstride = nexp * 8
            eb = top
            top += elstride * (L + 1)
            for b in order:
                if id(b) not in routed:
                    continue
                s, _ = routed[id(b)]
                eid = next(r["eid"] for r in recs if r["slot"] == s)
                kd["exp"][s] = eid
                st = want[id(b)]
                b.update(row_base=eb + st, layer_stride=elstride, id_sel=s + 1, expert_stride=8,
                         dram_row=eb + L * elstride + eid * 8 + st, bank_set=st, runtime_row=True)
            kd.update(ebase=eb, elstride=elstride)
        return top
    kd["row_top_after"] = after


def kind_seq(order):
    """fetch-order check sequence of a laid-out kind: [(row | None, set, words)]"""
    return [(None if b.get("runtime_row") else b["dram_row"] >> 3, b["dram_row"] & 7, words(b["n_lines"]))
            for b in order]


def check_sequence_pairs(kinds, what="kinds"):
    """every ordered pair (A tail -> B head) of laid-out kinds (any kind may follow any kind, itself included)"""
    res = []
    for na, sa in kinds.items():
        for nb, sb in kinds.items():
            if sa and sb:
                win = [(None, s, w) for (_, s, w) in sa[-REF_BACK:]] + [(None, s, w) for (_, s, w) in sb[:REF_BACK + 1]]
                res.append(check_stream("weights", win, f"{what} boundary {na}->{nb}"))
    return res


def _selftest():
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    import hbm_bw_unit as B
    ok = True
    for pat, want in (("ds_rot", True), ("weights", True), ("kv", True), ("embed_head", True), ("qwen", True),
                      ("tables", True), ("packed", True),
                      ("ds", False), ("asbuilt", False), ("rand", False), ("ds_nodup", False), ("experts", False),
                      ("tables_home", False)):
        blks = B.gen(pat, 4, 1)
        cls = B.PATTERN_CLASS.get(pat, "weights")
        seq = [(None if B.runtime_row(pat, i) else row, slot, w) for i, (row, slot, w) in enumerate(blks)]
        try:
            check_stream(cls, seq, pat)
            got, msg = True, "ROTATED"
        except LayoutRefused as e:
            got, msg = False, str(e)[:160]
        ok &= got == want
        print(f"{'ok ' if got == want else 'BAD'} {pat:11s} {cls:10s} {msg}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        raise SystemExit(_selftest())
    print(__doc__)
