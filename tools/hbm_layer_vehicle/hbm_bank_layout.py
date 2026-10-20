#!/usr/bin/env python3
"""HBM-ROTLAYOUT (owner rule 2026-10-19): the ONE HBM bank layout of every stream the d4g compiler places, and the
compiler check that refuses any stream that is not rotated across bank sets.

Why (RTL-measured, claude/l2h-bw-safe-1019 89200325b exposed_bank/README.md, tb_hbm_bw_pc4 +EXPOSE): the successor PC
controller (one open row per bank, QD64 ACT lookahead, columns strictly in compiler order) hides ~96 % of tRP+tRCD and
sustains 91.6-92.9 B/edge/SM ONLY when consecutive blocks of a stream sit on different bank sets; with every block on
one set (as-built row-per-block, random rows) it exposes ~47 HBM cycles per ACT and drops to 26 B/edge, and the DS
layout without expert-copy alternation reaches only 54.9.

Address law (rtl ot_hbm_svc_prefetch_overlap_owner_rel_id.sv:51-62, leaf ot_hbm_svc_pc_ctrl_leaf_cfg_safe.sv:405):
an SM block (<= 64 136-B lines = <= 68 32-B words per PC, on the SM's four PCs) has an 18-bit BLOCK ADDRESS
{row[17:3], set[2:0]}; descriptor base[9:7] = set = the physical bank set bank[4:2] of the block on each of its PCs
(the owner's bhi = set ^ row[4:2] XOR is undone in the leaf), bank[1:0] = word t[1:0], col = t[6:2]; i.e. block address
a is DRAM row a >> 3, set a & 7 (smb_unit: sector_address(o + 512 * (a & 7), row_base = a >> 3)).

Layout (the only one):
  * weights / embed_head / kv (static fetch order): SLOT-PACKED -- block i of a stream at block address base + i, so the
    set advances by one every block (8 blocks share one DRAM row index, one per set).  smb_unit.layout_bw additionally
    phases the DS non-expert run so it ends on set 4 / set 0 around the routed blocks (refresh-key contract).
  * experts (routed, runtime ids): the set is a function of the routed POSITION, not of the id -- routed block b_i of the
    p-th routed descriptor reads copy p mod 3 on set RSETS[b_i][p mod 3] (w1+w3 on 5/6/7, w2 on 1/2/3; experts stored
    three times: HBM capacity, not bandwidth).
  * tables (runtime-indexed: embedding rows, engram rows, other lookup tables): entry e of nb blocks at block address
    base + e * nb + k, nb not a multiple of 8, so an entry's blocks rotate over consecutive sets and entries interleave
    over all eight sets (adjacent lookups collide on one set only by chance, 1/8, never by construction).

Check (check_stream): in a stream's fetch order, two blocks on the SAME bank set but DIFFERENT DRAM rows must be
separated by >= T_HIDE column words of other blocks (tRP 16 + tRCD 19 HBM cycles at one column per cycle per PC), so the
controller's lookahead can precharge + activate the second while the blocks in between stream.  A runtime row (routed
expert, table entry: row=None) is assumed to differ from every other row.  Any violation is a refusal (SystemExit), not
a warning: the compiler never emits an unrotated stream.

  python3 tools/hbm_layer_vehicle/hbm_bank_layout.py selftest      # the measured layouts: rotated PASS, unrotated REFUSED
"""
from __future__ import annotations

import sys

NSETS = 8                      # bank sets per PC = bank[4:2] (32 banks = 8 sets x 4)
T_HIDE = 35                    # tRP 16 + tRCD 19 HBM cycles (tb_svg_rel_dram_sparse / cfg_safe HBM3-class timing)
CLASSES = ("weights", "experts", "kv", "embed_head", "tables")
RSETS = ((5, 6, 7), (1, 2, 3))  # routed copies per routed block index (w1+w3, w2), copy = routed position mod 3
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


def packed(base, n):
    """slot-packed run: n block addresses base .. base+n-1 (set advances every block)"""
    return [base + i for i in range(n)]


def expert_set(b_i, position):
    """bank set of routed block b_i (0 = w1+w3, 1 = w2) of the position-th routed descriptor in fetch order"""
    return RSETS[b_i][position % len(RSETS[b_i])]


def table_entry(base, e, nb):
    """block addresses of entry e (nb blocks) of a runtime-indexed table"""
    if nb % NSETS == 0:
        raise LayoutRefused(f"ROTLAYOUT REFUSED tables: entry stride {nb} blocks is a multiple of {NSETS} "
                            "(every entry would start on the same bank set)")
    return [base + e * nb + k for k in range(nb)]


def layout_bw(kd, recs, nonexp, exp_blocks, L, avoid_first=(), nexp=384):
    """The d4g SM block layout of one compiled kind (moved here from smb_unit.layout_bw, HBM-BW 10-19; smb_unit calls it).
    The sub-row slot of a block address IS the physical bank-set of the block on each of its four PCs
    (owner bhi = slot ^ row[4:2], leaf bank[4:2] = bhi ^ row[4:2]); strides that are multiples of 8 keep it per layer
    and per expert.  In the fetch order, non-expert blocks advance the set cyclically and the run before the first
    routed block ends on set 4 (ot_hbm_r14_aq_pc_mr refresh-key contract: tail-2 .. tail+3 protected); routed block
    b_i of the p-th routed descriptor (fetch order) reads COPY p mod 3 on set RSETS[b_i][p mod 3] (one DRAM row index per
    expert and layer holds the w1+w3 copies on sets 5/6/7 and the w2 copies on 1/2/3); non-expert blocks after the first
    routed one end on set 0.  Experts are stored three times (HBM capacity, not bandwidth).
    HBM-ROTLAYOUT: avoid_first = bank sets the kind's FIRST block must not use (the tail sets of every kind that can
    precede it in the layer sequence); the first block then takes the next free set before the rotation (a skipped
    slot costs capacity only).  Mutates the block dicts like the original; returns nothing (kd['row_top_after'])."""
    order = [b for r in recs for b in r["blocks"]]
    routed = {id(b) for bl in exp_blocks.values() for b in bl}
    first_r = next((i for i, b in enumerate(order) if id(b) in routed), len(order))
    pre = [b for b in order[:first_r] if id(b) not in routed]
    post = [b for b in order[first_r:] if id(b) not in routed]
    end_pre = 4 if exp_blocks else (len(pre) - 1) % 8
    want = {}
    for j, b in enumerate(pre):
        want[id(b)] = (end_pre - (len(pre) - 1 - j)) % 8
    for j, b in enumerate(post):
        want[id(b)] = (0 - (len(post) - 1 - j)) % 8
    head = pre[0] if pre else (post[0] if post and first_r > 0 else None)
    if head is not None and want[id(head)] in avoid_first:
        nxt = pre[1] if len(pre) > 1 and head is pre[0] else None
        cand = [c for c in (4, 5, 6, 7, 0, 1, 2, 3) if c not in avoid_first and (nxt is None or c != want[id(nxt)])]
        if not cand:
            raise LayoutRefused(f"ROTLAYOUT REFUSED {kd.get('name')}: no free first set (avoid {sorted(avoid_first)})")
        want[id(head)] = cand[0]
    p, offs = -1, {}
    for b in pre + post:
        p += 1
        while p % 8 != want[id(b)]:
            p += 1
        offs[id(b)] = p
    lstride = 8 * (p // 8 + 1)

    def after(row_top):
        kbase = row_top
        top = row_top + lstride * (max(L, 0) + 1)
        kd.update(lstride=lstride, kbase=kbase, estride=8 if exp_blocks else 0)
        for b in nonexp:
            b.update(row_base=kbase + offs[id(b)], layer_stride=lstride, id_sel=0, expert_stride=0,
                     dram_row=kbase + L * lstride + offs[id(b)], bank_set=offs[id(b)] % 8, runtime_row=False)
        kd["exp"] = {}
        if exp_blocks:
            assert max(len(v) for v in exp_blocks.values()) <= len(RSETS), "routed expert with more blocks than RSETS"
            elstride = nexp * 8
            eb = top
            top += elstride * (L + 1)
            pos = [0] * len(RSETS)
            for b in order:
                if id(b) not in routed:
                    continue
                s = next(s_ for s_, bl in exp_blocks.items() if any(x is b for x in bl))
                b_i = next(i for i, x in enumerate(exp_blocks[s]) if x is b)
                eid = next(r["eid"] for r in recs if r["slot"] == s)
                kd["exp"][s] = eid
                st = expert_set(b_i, pos[b_i])
                pos[b_i] += 1
                b.update(row_base=eb + st, layer_stride=elstride, id_sel=s + 1, expert_stride=8,
                         dram_row=eb + L * elstride + eid * 8 + st, bank_set=st, runtime_row=True)
            kd.update(ebase=eb, elstride=elstride)
        return top
    kd["row_top_after"] = after


def kind_seq(order):
    """fetch-order check sequence of a laid-out kind: [(row | None, set, words)]"""
    return [(None if b.get("runtime_row") else b["dram_row"] >> 3, b["dram_row"] & 7, words(b["n_lines"]))
            for b in order]


def tail_sets(seq, t_hide=T_HIDE):
    """bank sets a following stream's first block must avoid: the sets of the tail blocks within T_HIDE words"""
    out, acc = set(), 0
    for (_, s, w) in reversed(seq):
        out.add(s)
        acc += w
        if acc >= t_hide:
            break
    return out


def check_sequence_pairs(kinds, what="kinds"):
    """every ordered pair (A tail -> B head) of laid-out kinds (any kind may follow any kind in the layer sequence,
    including itself): the concatenated boundary window must be rotated"""
    res = []
    for na, sa in kinds.items():
        for nb, sb in kinds.items():
            if not sa or not sb:
                continue
            k = 0
            acc = 0
            for (_, _, w) in reversed(sa):
                k += 1
                acc += w
                if acc >= T_HIDE:
                    break
            win = [(None, s, w) if r is None else (("A", r), s, w) for (r, s, w) in sa[-k:]] + \
                  [(None, s, w) if r is None else (("B", r), s, w) for (r, s, w) in sb[:4]]
            res.append(check_stream("weights", win, f"{what} boundary {na}->{nb}"))
    return res


def check_stream(cls, seq, what="", t_hide=T_HIDE):
    """seq = fetch order [(row | None, set, words)]; returns a summary dict or raises LayoutRefused."""
    if cls not in CLASSES:
        raise LayoutRefused(f"ROTLAYOUT REFUSED {what}: unknown stream class {cls!r} (classes {CLASSES})")
    worst = None
    sets_used = set()
    for i, (r, s, w) in enumerate(seq):
        if not 0 <= s < NSETS:
            raise LayoutRefused(f"ROTLAYOUT REFUSED {cls} {what}: block {i} bank set {s} outside 0..{NSETS - 1}")
        sets_used.add(s)
        acc = 0
        for j in range(i - 1, -1, -1):
            rj, sj, wj = seq[j]
            if sj == s and (r is None or rj is None or rj != r):
                raise LayoutRefused(
                    f"ROTLAYOUT REFUSED {cls} {what}: block {i} (row {r}, set {s}) follows block {j} (row {rj}, same set) "
                    f"with only {acc} column words between (< T_HIDE {t_hide}): the stream is not rotated across bank sets")
            acc += wj
            if acc >= t_hide:
                break
        if i and (worst is None or acc < worst):
            worst = acc
    if len(seq) > 1 and len(sets_used) < 2:
        raise LayoutRefused(f"ROTLAYOUT REFUSED {cls} {what}: all {len(seq)} blocks on bank set {sets_used}")
    return dict(cls=cls, what=what, blocks=len(seq), sets=sorted(sets_used), t_hide=t_hide, verdict="ROTATED")


def check_addrs(cls, addrs, wds, what=""):
    """check a static stream given as block addresses + per-block words"""
    return check_stream(cls, [(a >> 3, a & 7, w) for a, w in zip(addrs, wds)], what)


def require_all(results):
    """every stream class the image holds was checked (a compiler that skips a class is refused)"""
    seen = {r["cls"] for r in results}
    return dict(classes_checked=sorted(seen), all_rotated=all(r["verdict"] == "ROTATED" for r in results))


def _selftest():
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    import hbm_bw_unit as B
    ok = True
    for pat, want in (("ds_rot", True), ("ds", False), ("packed", True), ("weights", True), ("experts", True), ("kv", True),
                      ("embed_head", True), ("qwen", True), ("tables", True),
                      ("asbuilt", False), ("rand", False), ("ds_nodup", False)):
        blks = B.gen(pat, 4, 1)
        cls = B.PATTERN_CLASS.get(pat, "weights")
        seq = [(None if B.runtime_row(pat, i) else row, slot, w) for i, (row, slot, w) in enumerate(blks)]
        try:
            check_stream(cls, seq, pat)
            got = True
            msg = "ROTATED"
        except LayoutRefused as e:
            got = False
            msg = str(e)[:150]
        ok &= got == want
        print(f"{'ok ' if got == want else 'BAD'} {pat:10s} {cls:10s} {msg}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["selftest"]:
        raise SystemExit(_selftest())
    print(__doc__)
