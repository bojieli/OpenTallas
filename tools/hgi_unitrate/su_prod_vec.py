#!/usr/bin/env python3
"""hgi-unitrate (2026-10-10): PRODUCTION-SHAPE data vectors for the SU / SFU die body (ot_hgi_su_unit).

The records are the real dispatches of the hbm-sim Qwen3-8B token program (TP4, P 8,191, rank 0, layer 0: the
sequencer contract's effective descriptors, tools/hgi_seq_vectors.Ref), not reduced shapes: row_scale_qkv 1,536 words,
rope, softmax over 8 heads x 8,192 keys (65,536 words), row_scale_gu 6,144, SwiGLU 3,072, ...  The layer's SU records
run in program order on ONE die state (hgi_sim machine semantics, u_su_vop / u_glu): VM starts random (seeded), the
SU chain's own results feed its later records (softmax max -> exp_sum -> bf16_p), other units' outputs stay random.
Each record is one DATA case: VM in = every word of its source spans, VM out = every word it writes.

Writes the tb_hgi_su_prod vector set into --out:
  su_rec.mem (2,197 b dispatch a line), su_case.mem {first dispatch, dispatches, first vmi sector, vmi sectors,
  first vme sector, vme sectors, {sfu 1, case id 31}} (7 x 32 b), su_vmi.mem / su_vme.mem {sector 32, data 256} a line
  (vmi: every sector of the sources AND sinks, pre-op; vme: every sink sector, post-op: the words the op does not
  write must keep their pre-op value, so a drain that touches them fails),
  su_sizes.svh, su_prod.json (manifest with the priced cost of each record: timing.cost at N1024 / M256),
  su_aux.svh / su_price.mem (the priced cost x 10 of every dispatch, for the bench's service / price line; the bench
  never prices) / su_vmg.mem (per vme sector: the 8-b mask of the words the case's records write; the rest are guards).

SINK_UNSTAGED (el1013-hbm-redesign-suvop, --sink-unstaged, default on with --chain): one extra case AFTER the
production chain (CASE 0 and its service are unchanged): SU.VOP copies whose O span starts and ends mid-sector (odd
offset / length; one strided sink with partial sectors inside the span) and shares no sector with the record's
sources, so the unit never stages those sink sectors and its local copy of them is whatever an earlier record left
there (same local shapes are issued twice on different data).  The guard words (unwritten words of the sink sectors)
are preset in VM to unique markers no record ever wrote; the golden keeps them.  A drain that writes whole sectors
regardless of the dirty word mask (MUT_DIRTY / MUT_V 2) corrupts them.
"""
import argparse
import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / 'hgi_adapters'))
import common as C  # noqa: E402
import su_bench as SB  # noqa: E402
from hgi_sim import machine as MA, timing as T  # noqa: E402

F = np.float32
VM_SECTORS = 1 << 15                         # the D1 VM: 2^18 words (the bench agents address 15-b sectors)
AGENT_DEF, AGENT_N = (14336, 18432), 2048    # tb_hgi_su_prod SHARED agents' sectors (AR0, AW0; AN each), when free


def agent_regions(used, nsec):
    """(AR0, AW0): the bench agents' read-only / written regions, disjoint from every sector the vectors touch.  The
    tb defaults when they are free (DeepSeek L0), else the highest free 256-sector-aligned runs (the Qwen3 L0 chain
    covers both defaults: its SHARED / CHAIN-topology runs failed on agent traffic over the record's own sectors)."""
    busy = np.zeros(nsec, bool)
    busy[[x for x in used if x < VM_SECTORS]] = True
    out = []
    for d in AGENT_DEF:
        s = d
        if busy[s:s + AGENT_N].any():
            s = (nsec - AGENT_N) // 256 * 256
            while s >= 0 and busy[s:s + AGENT_N].any():
                s -= 256
            assert s >= 0, 'no free VM run for the bench agents'
        busy[s:s + AGENT_N] = True
        out.append(s)
    return tuple(out)
# SINK_UNSTAGED records: (tag, rows no, row words ni, O row stride, O word offset in its first sector).  A is dense.
SU_CASES = (('copy_1x2043_o3', 1, 2043, 2043, 3), ('copy_1x2043_o3_again', 1, 2043, 2043, 3),
            ('copy_8x1021_o5', 8, 1021, 1021, 5), ('copy_8x1021_o5_again', 8, 1021, 1021, 5),
            ('copy_1x1_o4', 1, 1, 1, 4), ('copy_1x5_o6', 1, 5, 5, 6), ('copy_37x11_s19_o3', 37, 11, 19, 3))
# el1013 resume5: a 65,536-word sink at word offset 3 of its first sector = 8,193 sectors at lo % 256 != 0: the unit's
# TWO-FRAME region (D7).  Appended only when the VM has the room (the Qwen3 L0 chain leaves none: --two-frame off).
# Its 8 rows read ONE 8,192-word source row (A row stride 0): 1,024 source sectors instead of 8,192.
SU_TWO_FRAME = ('copy_8x8192_o3_two_frames', 8, 8192, 8192, 3, 0)


# FWD_PIN (el1013 resume5, --fwd-pin; a standalone vector set: --chain --tags NONE --no-sink-unstaged --fwd-pin):
# the case that kills MUT_V 4 (a forward reader takes no frame pin).  Four records, sized so that every local frame
# is held when the last one needs a dedicated frame:
#   R1  copy   A1 (one 8,192-word row read 5 times) -> O1 5 x 8,192 dense        O1 = frame 0, A1 opens the bump frame 1
#   R1b sqrt   2,048 elements at input stride 17 (span 34,800 words) -> 2,048    its source = frame 2; scalar SFU: one
#                                                                                element a vector, > 2,048 cycles
#   R2  copy   O1 -> O2 5 x 8,192                                                A FORWARDS from frame 0, O2 = frame 3
#   R3  copy   2,048 elements at input stride 17 -> 2,048                        its source needs a dedicated frame
# R3's source waits for a free frame.  Correct unit: frame 2 at R1b's compute done (frame 0 stays pinned by R2's
# forward until R2 has computed).  MUT_V 4: frame 0 is freed at R1's retire, during R1b's long compute, R3's source
# is staged over O1's local copy, and R2 copies the wrong words.
FP_ROWS, FP_NI, FP_NE, FP_IS = 5, 8192, 2048, 17


def fwd_pin(M, die, dyn, rng):
    """-> (dispatches, manifest rows, src-only sectors, sink sectors, pre-op VM, written word addresses, used sectors)"""
    from hgi_sim.records import decode_one
    I = MA.I
    big = FP_ROWS * FP_NI // 8                                # 5,120 sectors
    spn = ((FP_NE - 1) * FP_IS + 1 + 7) // 8                  # 4,350 sectors
    lay, cur = {}, 0
    for nm, n in (('O1', big), ('O2', big), ('A1', FP_NI // 8), ('A1b', spn), ('O1b', FP_NE // 8), ('A3', spn),
                  ('O3', FP_NE // 8)):
        lay[nm] = cur * 8
        cur = (cur + n + 2 + 31) // 32 * 32                    # 256-word aligned, a spare sector between regions
    assert cur <= VM_SECTORS - 2 * AGENT_N, 'FWD_PIN does not fit the VM beside the bench agents'
    w1b = lay['A1b'] + np.arange(FP_NE) * FP_IS
    die.vm[w1b] = (np.abs(rng.normal(1.0, 0.5, FP_NE)) + 0.25).astype(F).view(np.uint32)     # sqrt operands > 0
    cp, sq = SB.sut_word(dst=I.DST_VM), SB.sut_word(dst=I.DST_VM, sfu=I.SFU_SQRT)
    recs = [
        ('fwd_pin.r1_copy', cp, dict(A=SB.mdesc(base=lay['A1'], n=FP_NI, m=FP_ROWS, stride=0, istride=1),
                                     O=SB.mdesc(base=lay['O1'], n=FP_NI, m=FP_ROWS, stride=FP_NI, istride=1))),
        ('fwd_pin.r1b_sqrt', sq, dict(A=SB.mdesc(base=lay['A1b'], n=FP_NE, m=1, stride=FP_NE * FP_IS, istride=FP_IS),
                                      O=SB.mdesc(base=lay['O1b'], n=FP_NE, m=1, stride=FP_NE, istride=1))),
        ('fwd_pin.r2_copy_fwd', cp, dict(A=SB.mdesc(base=lay['O1'], n=FP_NI, m=FP_ROWS, stride=FP_NI, istride=1),
                                         O=SB.mdesc(base=lay['O2'], n=FP_NI, m=FP_ROWS, stride=FP_NI, istride=1))),
        ('fwd_pin.r3_copy_strided', cp, dict(A=SB.mdesc(base=lay['A3'], n=FP_NE, m=1, stride=FP_NE * FP_IS, istride=FP_IS),
                                             O=SB.mdesc(base=lay['O3'], n=FP_NE, m=1, stride=FP_NE, istride=1))),
    ]
    pre = die.vm.copy()
    ds, rows, srcs, snks = [], [], [], []
    for tag, sut, descs in recs:
        d = SB.synth(sut=sut, descs=descs)
        bb = d['hdr'].to_bytes(16, 'little') + d['sut'].to_bytes(32, 'little')
        bb += d['eff'][0].to_bytes(32, 'little') + d['eff'][4].to_bytes(32, 'little')
        r, _ = decode_one(bb, 0)
        r.tag = tag
        M.cur = r
        sp = spans(r, M, die, 0)
        MA.UNITS[(r.unit, r.op)](M, r, 0)
        c, how = T.su_cost(r, dyn, 0)[:2]
        sa, so = sp['A'], sp['O']
        rows.append(dict(tag=tag, unit='SU', case='FWD_PIN', priced=round(float(c), 1), priced_how=how,
                         qualification='exactness only: not part of the production chain price',
                         stage_sectors=int(len(np.unique(sa >> 3))), drain_sectors=int(len(np.unique(so >> 3))),
                         roles=dict(A=[int(sa.min()), int(sa.max()), int(len(sa))], O=[int(so.min()), int(so.max()), int(len(so))])))
        ds.append(d); srcs.append(sa); snks.append(so)
    assert np.array_equal(die.vm[snks[2]], np.tile(pre[srcs[0]], FP_ROWS)), 'R2 must copy what R1 wrote'
    snk = np.concatenate(snks)
    osec = np.unique(snk >> 3)
    # a strided source stages its whole span: load every sector of it
    span_secs = [np.arange(int(x.min()) >> 3, (int(x.max()) >> 3) + 1) for x in srcs]
    ssec = np.setdiff1d(np.unique(np.concatenate(span_secs)), osec)
    used = set(ssec.tolist()) | set(osec.tolist())
    return ds, rows, ssec, osec, pre, snk, used


def sink_unstaged(M, die, dyn, used, prev_vals, agent, two_frame=False):
    """-> (dispatches, manifest rows, src sectors, sink sectors, pre-op VM, written word addresses).  Runs the
    records on the machine (die.vm advances).  `used`: sectors the earlier cases touch; `prev_vals`: every value an
    earlier record wrote (the guard markers must differ from all of them)."""
    from hgi_sim.records import decode_one
    busy = np.zeros(VM_SECTORS, bool)
    busy[[x for x in used if x < VM_SECTORS]] = True
    for lo in agent:
        busy[lo:lo + AGENT_N] = True
    cur = [0]

    def alloc(nsec):
        """first free run of nsec + 2 sectors at a 32-sector (256-word: one bank phase) boundary; a spare sector
        either side keeps every record's sectors its own"""
        s = cur[0]
        while True:
            s = (s + 31) // 32 * 32
            assert s + nsec + 2 <= len(busy), 'no free VM run for SINK_UNSTAGED'
            if not busy[s:s + nsec + 2].any():
                busy[s:s + nsec + 2] = True
                cur[0] = s + nsec + 2
                return s
            s += 32
    plan = []
    for case in SU_CASES + ((SU_TWO_FRAME,) if two_frame else ()):
        tag, no, ni, oso, off = case[:5]
        aso = case[5] if len(case) > 5 else ni                  # A row stride (0: every row reads the same row)
        a0 = alloc(((no - 1) * aso + ni + 7) // 8) * 8
        o0 = alloc((off + (no - 1) * oso + ni + 7) // 8) * 8 + off
        d = SB.synth(sut=SB.sut_word(dst=1), descs=dict(A=SB.mdesc(base=a0, n=ni, m=no, stride=aso, istride=1),
                                                         O=SB.mdesc(base=o0, n=ni, m=no, stride=oso, istride=1)))
        bb = d['hdr'].to_bytes(16, 'little') + d['sut'].to_bytes(32, 'little')
        bb += d['eff'][0].to_bytes(32, 'little') + d['eff'][4].to_bytes(32, 'little')
        r, _ = decode_one(bb, 0)
        r.tag = 'sink_unstaged.' + tag
        M.cur = r
        sp = spans(r, M, die, 0)
        assert len(sp['O']) == no * ni and len(sp['A']) == ((no - 1) * aso + ni if aso < ni else no * ni), (tag, len(sp['A']), len(sp['O']))
        plan.append((r, d, sp['A'], sp['O']))
    src = np.unique(np.concatenate([x[2] for x in plan]))
    snk = np.concatenate([x[3] for x in plan])
    assert len(np.unique(snk)) == len(snk), 'sinks overlap'
    ssec, osec = np.unique(src >> 3), np.unique(snk >> 3)
    assert not set(ssec) & set(osec), 'a sink sector is a source sector: it would be staged'
    # guards: every word of the sink sectors gets a unique marker nothing wrote before (the op overwrites its own words)
    allw = (osec[:, None] * 8 + np.arange(8)).reshape(-1)
    mark = (0xD1A70000 + np.arange(len(allw))).astype(np.uint32)
    assert not np.isin(mark, prev_vals).any() and not np.isin(mark, die.vm).any()
    die.vm[allw] = mark
    assert len(np.unique(die.vm[src])) > len(src) // 2, 'sources must carry distinct data'
    pre = die.vm.copy()
    rows = []
    for r, d, sa, so in plan:
        M.cur = r
        MA.UNITS[(r.unit, r.op)](M, r, 0)
        fs, ls = int(so.min()) >> 3, int(so.max()) >> 3
        nfirst, nlast = int((so >> 3 == fs).sum()), int((so >> 3 == ls).sum())
        assert nfirst < 8 and nlast < 8, (r.tag, 'first and last sink sectors must be partially written')
        c, how = T.su_cost(r, dyn, 0)[:2]
        rows.append(dict(tag=r.tag, unit='SU', case='SINK_UNSTAGED', priced=round(float(c), 1), priced_how=how,
                         qualification='exactness only: not part of the production chain price',
                         stage_sectors=int(len(np.unique(sa >> 3))), drain_sectors=int(len(np.unique(so >> 3))),
                         roles=dict(A=[int(sa.min()), int(sa.max()), int(len(sa))], O=[int(so.min()), int(so.max()), int(len(so))]),
                         first_sector_words=nfirst, last_sector_words=nlast))
    guard = np.setdiff1d(allw, snk)
    assert np.array_equal(die.vm[guard], pre[guard]) and len(guard) >= 2 * len(plan)
    assert not np.isin(die.vm[guard], die.vm[snk]).any()
    for r, d, sa, so in plan:
        assert np.array_equal(die.vm[so], pre[sa] if len(sa) == len(so) else np.tile(pre[sa], len(so) // len(sa))), (r.tag, 'copy')
    # the "again" twins: same shape and bank phase, different data and VM span
    assert not np.array_equal(pre[plan[0][2]], pre[plan[1][2]]) and not np.array_equal(pre[plan[2][2]], pre[plan[3][2]])
    return [d for _, d, _, _ in plan], rows, ssec, osec, pre, snk


def spans(r, M, die, L):
    """{role: VM word addresses} of the record's VM operands (b_half B / D at i >> 1)."""
    out = {}
    a = r.desc["A"]
    _, ni, no, _, _ = M.eff(a, die, L)
    for k, d in r.desc.items():
        if d.space != "VM":
            continue
        if r.unit == "SU" and r.sut.get("b_half") and k in ("B", "D"):
            base, _, _, st, ist = M.eff(d, die, L)
            o, i = np.meshgrid(np.arange(no), np.arange(ni), indexing="ij")
            out[k] = np.unique((base + o * st + (i >> 1) * ist).reshape(-1))
        elif k == "R":
            base, n, m, st, ist = M.eff(d, die, L)
            nred = 1 if (r.sut.get("red_whole") or r.sut.get("red_tree")) else no
            out[k] = base + np.arange(nred) * (st or 1)
        elif r.unit == "SU" and k == "A" and r.sut.get("c_pair"):
            ad = M.vm_addrs(d, die, L, no, ni)
            out[k] = np.unique(np.concatenate([ad, ad ^ 1]))
        elif r.unit == "SFU" or k != "A":
            out[k] = np.unique(M.vm_addrs(d, die, L))
        else:
            out[k] = np.unique(M.vm_addrs(d, die, L, no, ni))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--unit', default='both', choices=['su', 'sfu', 'both'])
    ap.add_argument('--tags', default='', help='comma list of tags to keep (default: every layer-0 SU / SFU record)')
    ap.add_argument('--allow-incomplete-coverage', action='store_true', help='emit explicitly unqualified partial vectors instead of failing when canonical SU/SFU coverage is incomplete')
    ap.add_argument('--seed', type=int, default=20261010)
    ap.add_argument('--chain', action='store_true', help='ONE case: every kept record back to back (the unit may '
                    'overlap them); VM in = the pre-chain state of every touched sector, out = the final sink sectors')
    ap.add_argument('--drain-traffic', action='store_true', help='independent per-record masked VM write golden for the production chain, including overwritten predecessor sinks')
    ap.add_argument('--ds-program', default='', help='a ds_native --program-out dump: use its layer-0 rank-0 records '
                    '(DeepSeek-V4.1 1M) instead of the Qwen3-8B token program')
    ap.add_argument('--sink-unstaged', action=argparse.BooleanOptionalAction, default=None,
                    help='append the SINK_UNSTAGED case (see the module text); default: on with --chain')
    ap.add_argument('--fwd-pin', action='store_true',
                    help='append the FWD_PIN case (kills MUT_V 4, see the module text); a standalone set: '
                         '--chain --tags NONE --no-sink-unstaged --fwd-pin')
    ap.add_argument('--two-frame', action='store_true',
                    help='SINK_UNSTAGED: append a 65,536-word sink at word offset 3 (8,193 sectors: the unit\'s '
                         'two-frame region, D7 / MUT_V 7); needs ~16.4 k free VM sectors')
    a = ap.parse_args()
    if a.sink_unstaged is None:
        a.sink_unstaged = bool(a.chain) and a.unit != 'sfu' and not a.tags
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.ds_program:
        from hgi_sim.records import decode_one
        dd = json.loads(Path(a.ds_program).read_text())
        lay = dd['layers'][0]
        words, recs = [], []
        for x in lay['records']:
            b = bytes.fromhex(x['hex'])
            words += [int.from_bytes(b[q:q + 16], 'little') for q in range(0, len(b), 16)]
            r, _ = decode_one(b, 0)
            r.tag = x['tag']
            recs.append(r)
        words += C.SV.record(C.SV.header('CTL', 'END'), descs={'A': C.SV.mdesc(space=1, fmt=5, base=(1 << 18) - 16, n=1, m=1)})
        POS = (1 << 20) - 1
        tr, _ = C.SV.Ref(words, 0, 0, POS, 0, 129280, 1 << 20, {}).run()
        tr = [x for x in tr if C.unit_of(x) != 0]
        prog_name = f'ds_native DeepSeek-V4.1 TP96 P{POS} rank 0 layer {lay["layer"]} ({a.ds_program})'
    else:
        words, recs, g, md = C.SV.qwen_program()
        tr, _ = C.qwen_dispatch()
        POS = 8191
        prog_name = 'hbm-sim Qwen3-8B TP4 P8191 rank 0 layer 0'
    ex = [(k, L) for k, L, L1 in T.expand(recs, POS) if recs[k].unit != 'CTL']
    assert len(ex) == len(tr), (len(ex), len(tr))
    rng = np.random.default_rng(a.seed)
    M = MA.Machine([MA.Die(0, MA.Hbm())])
    M.cfg["cp_ctx_max"] = max(M.cfg.get("cp_ctx_max", 0), 1 << 20)
    M.doorbell(0, POS)
    die = M.dies[0]
    die.vm[:] = rng.normal(0.0, 1.0, die.vm.size).astype(F).view(np.uint32)   # die.vm is the die's VM (MA.VM_WORDS drifted from it)
    keep = set(a.tags.split(',')) if a.tags else None
    units = {'su': ('SU',), 'sfu': ('SFU',), 'both': ('SU', 'SFU')}[a.unit]
    dyn = T.Dyn(POS)
    recl, cases, vmi, vme, man = [], [], [], [], []
    wrmask = {}                                             # case index -> word addresses its records write
    used, prev_sinks = set(), []
    chain = []
    coverage = {}
    for dispatch_index, (record_index, layer) in enumerate(ex):
        record = recs[record_index]
        if record.unit not in ('SU', 'SFU') or record.tag in coverage:
            continue
        coverage[record.tag] = dict(unit=record.unit, tag=record.tag, status='NOT_EMITTED', descriptors={k: dataclasses.asdict(v) for k, v in record.desc.items()}, effective_dispatch_hex=C.hexw(SB.pack_rec(tr[dispatch_index]), 2197))
        if any(md.space != 'VM' for md in record.desc.values()):
            coverage[record.tag]['status'] = 'UNQUALIFIED_NON_VM_FIXTURE'
            fixture = dict(coverage[record.tag], qualification='actual canonical descriptor/dispatch fixture; native STREAM execution unqualified; no VM alias substitution')
            (out / ('fixture_' + record.tag.replace('.', '_') + '.json')).write_text(json.dumps(fixture, indent=2) + '\n')
    # Seed isolated indexed scalar fixtures before taking the chain's initial
    # VM snapshot, so su_vmi carries the same U32 values used by Machine.eff.
    for record_index, layer in ex:
        record = recs[record_index]
        if record.tag.startswith('route.gather') and any(md.indexed for md in record.desc.values()):
            ib = M._plain_base(record.desc['I'], die, layer)
            die.vm[ib + layer] = np.uint32(int(record.tag.removeprefix('route.gather')))
    drain_traffic = []
    seen = set()
    for i, (k, L) in enumerate(ex):
        r = recs[k]
        d = tr[i]
        if r.unit not in ('SU', 'SFU'):
            continue
        if any(x.space != 'VM' for x in r.desc.values()):
            coverage[r.tag]['status'] = 'UNQUALIFIED_NON_VM_FIXTURE'
            fixture = dict(coverage[r.tag], qualification='actual descriptor/dispatch fixture; native STREAM execution unqualified; no VM alias substitution')
            (out / ('fixture_' + r.tag.replace('.', '_') + '.json')).write_text(json.dumps(fixture, indent=2) + '\n')
            continue                                        # STREAM / HBM operands: not a D1 VM record
        if r.unit == 'SU' and r.sut.get('a_ind'):
            coverage[r.tag]['status'] = 'UNQUALIFIED_VECTOR_GATHER'
            print(f"unqualified {r.tag}: SU vector gather is unsupported by this golden; never silently omitted")
            continue
        if r.tag in seen:
            break                                           # next layer
        seen.add(r.tag)
        die.dyn[4] = L
        M.cur = r
        # Indexed MDESCs are resolved by the sequencer, unlike SUT a_ind.
        # Other units are not executed in this isolated SU fixture. Supply
        # explicit valid TOPK index fixture data instead of interpreting random
        # FP32 bits as U32 route indices, and pin the exact effective dispatch.
        if any(md.indexed for md in r.desc.values()):
            assert r.tag.startswith('route.gather') and r.desc['A'].n == 1 and r.desc['A'].m == 1, 'unsupported indexed fixture; do not invent arbitrary gather data'
            selected = int(r.tag.removeprefix('route.gather'))
            ib = M._plain_base(r.desc['I'], die, L)
            die.vm[ib + L] = np.uint32(selected)
            d = dict(d, eff=list(d['eff']), n=list(d['n']))
            effective = {}
            for role, md in r.desc.items():
                base, nn, _, _, _ = M.eff(md, die, L)
                slot = C.OPND.index(role)
                lsb, width = C.MD['base']
                d['eff'][slot] = (d['eff'][slot] & ~(((1 << width) - 1) << lsb)) | (int(base) << lsb)
                d['n'][slot] = int(nn)
                effective[role] = dict(base=int(base), n=int(nn))
            coverage[r.tag]['index_fixture'] = dict(source='isolated valid route-index fixture; actual TOPK producer not executed', index_word=int(ib + L), selected=selected, effective=effective)
            coverage[r.tag]['effective_dispatch_hex'] = C.hexw(SB.pack_rec(d), 2197)
        try:
            sp = spans(r, M, die, L)
        except MA.Fault as e:
            coverage[r.tag]['status'] = 'UNQUALIFIED_ADDRESS_FAULT'
            coverage[r.tag]['reason'] = str(e)
            print(f"unqualified {r.tag}: {e} (sut a_ind {r.sut.get('a_ind')})")
            continue
        src = np.unique(np.concatenate([v for kk, v in sp.items() if kk not in ('O', 'R')]))
        snk = np.unique(np.concatenate([v for kk, v in sp.items() if kk in ('O', 'R')]))
        if a.chain and r.unit not in units:
            coverage[r.tag]['status'] = 'DECLARED_UNIT_FILTER'
            continue                                         # a chain runs one unit's records only, on its own state
        before = die.vm.copy()
        try:
            MA.UNITS[(r.unit, r.op)](M, r, L)
        except MA.Fault as e:
            coverage[r.tag]['status'] = 'UNQUALIFIED_ARITHMETIC_FAULT'
            coverage[r.tag]['reason'] = str(e)
            print(f"unqualified {r.tag}: {e}")
            die.vm[:] = before
            continue
        changed = np.nonzero(die.vm != before)[0]
        wrote = snk                                          # every sink word the op writes (value may be unchanged)
        assert set(changed) <= set(wrote.tolist()), (r.tag, 'wrote outside its sinks')
        if keep and r.tag not in keep:
            coverage[r.tag]['status'] = 'DECLARED_TAG_FILTER'
            continue
        if r.unit not in units:
            coverage[r.tag]['status'] = 'DECLARED_UNIT_FILTER'
            continue
        coverage[r.tag]['status'] = 'EMITTED_VM_COMPONENT_FIXTURE'
        used.update((src >> 3).tolist(), (snk >> 3).tolist())
        prev_sinks.append(snk)
        if a.chain:
            if a.drain_traffic:
                for sec in np.unique(snk >> 3):
                    ws = snk[(snk >> 3) == sec]
                    mask = sum(1 << int(x & 7) for x in np.unique(ws))
                    drain_traffic.append((int(sec), mask, [int(x) for x in die.vm[sec*8:(sec+1)*8]]))
            chain.append((r, d, before, src, snk, sp))
            continue
        c, gr, how = T.cost(r, dyn, L) if r.unit != 'SU' else (T.su_cost(r, dyn, L)[0] + 0.0, '', T.su_cost(r, dyn, L)[1])
        secs = np.unique(np.concatenate([src >> 3, snk >> 3]))  # sink sectors are loaded too: their other words guard
        osecs = np.unique(snk >> 3)
        wrmask[len(cases)] = snk
        cases.append((len(recl), 1, len(vmi), len(secs), len(vme), len(osecs), len(man) | ((r.unit == 'SFU') << 31)))
        recl.append(SB.pack_rec(d))
        for s_ in secs:
            vmi.append((int(s_), [int(x) for x in before[s_ * 8:(s_ + 1) * 8]]))
        for s_ in osecs:
            vme.append((int(s_), [int(x) for x in die.vm[s_ * 8:(s_ + 1) * 8]]))
        man.append(dict(tag=r.tag, unit=r.unit, priced=round(float(c), 1), priced_how=how,
                        stage_sectors=int(sum(len(np.unique(v >> 3)) for kk, v in sp.items() if kk not in ('O', 'R'))),
                        drain_sectors=int(sum(len(np.unique(v >> 3)) for kk, v in sp.items() if kk in ('O', 'R'))),
                        roles={kk: [int(v.min()), int(v.max()), int(len(v))] for kk, v in sp.items()},
                        vm_in_sectors=int(len(secs)), vm_out_words=int(len(wrote)), vm_out_sectors=int(len(osecs))))
        print(f"{r.unit} {r.tag:28s} priced {c:7.1f}  in sectors {len(secs):6d}  out words {len(wrote):6d}")
    if a.chain and chain:
        pre = chain[0][2]
        secs = np.unique(np.concatenate([np.concatenate([x[3] >> 3, x[4] >> 3]) for x in chain]))
        osecs = np.unique(np.concatenate([x[4] >> 3 for x in chain]))
        sfu = chain[0][0].unit == 'SFU'
        assert all((x[0].unit == 'SFU') == sfu for x in chain), 'a chain is one unit'
        wrmask[len(cases)] = np.concatenate([x[4] for x in chain])
        cases.append((0, len(chain), 0, len(secs), 0, len(osecs), (sfu << 31)))
        tot = 0.0
        for r, d, before, src, snk, sp in chain:
            recl.append(SB.pack_rec(d))
            c = T.cost(r, dyn, 0)[0] if r.unit != 'SU' else T.su_cost(r, dyn, 0)[0]
            tot += c
            man.append(dict(tag=r.tag, unit=r.unit, priced=round(float(c), 1),
                            stage_sectors=int(sum(len(np.unique(v >> 3)) for kk, v in sp.items() if kk not in ('O', 'R'))),
                            drain_sectors=int(sum(len(np.unique(v >> 3)) for kk, v in sp.items() if kk in ('O', 'R')))))
        for s_ in secs:
            vmi.append((int(s_), [int(x) for x in pre[s_ * 8:(s_ + 1) * 8]]))
        for s_ in osecs:
            vme.append((int(s_), [int(x) for x in die.vm[s_ * 8:(s_ + 1) * 8]]))
        print(f"chain of {len(chain)} records, priced sum {tot:.1f}, {len(secs)} sectors in, {len(osecs)} out")
    su_case = -1
    fp = None
    if a.fwd_pin:
        assert not used and not a.sink_unstaged, '--fwd-pin is a standalone set (--chain --tags NONE --no-sink-unstaged)'
        fp = fwd_pin(M, die, dyn, rng)
        used = set(fp[6])
    agent = agent_regions(used, VM_SECTORS)
    if agent != AGENT_DEF:
        print(f"bench agent regions moved off the vectors' sectors: AR0 {agent[0]} AW0 {agent[1]} (tb default {AGENT_DEF})")
    if a.sink_unstaged:
        prev_vals = die.vm[np.unique(np.concatenate(prev_sinks))] if prev_sinks else np.zeros(0, np.uint32)
        ds, rows, ssec, osec, pre, snk = sink_unstaged(M, die, dyn, used, prev_vals, agent, a.two_frame)
        su_case = max([c[6] & 0x7FFFFFFF for c in cases] + [-1]) + 1 if a.chain else len(man)
        wrmask[len(cases)] = snk
        cases.append((len(recl), len(ds), len(vmi), len(ssec) + len(osec), len(vme), len(osec), su_case))
        recl += [SB.pack_rec(d) for d in ds]
        for s_ in np.concatenate([ssec, osec]):
            vmi.append((int(s_), [int(x) for x in pre[s_ * 8:(s_ + 1) * 8]]))
        for s_ in osec:
            vme.append((int(s_), [int(x) for x in die.vm[s_ * 8:(s_ + 1) * 8]]))
        man += rows
        print(f"SINK_UNSTAGED case {su_case}: {len(ds)} records, {len(osec)} sink sectors, "
              f"{len(osec) * 8 - len(snk)} guard words (sectors {int(osec.min())}..{int(osec.max())})")
    if fp is not None:
        ds, rows, ssec, osec, pre, snk = fp[:6]
        su_case = 0
        wrmask[len(cases)] = snk
        cases.append((len(recl), len(ds), len(vmi), len(ssec) + len(osec), len(vme), len(osec), su_case))
        recl += [SB.pack_rec(d) for d in ds]
        for s_ in np.concatenate([ssec, osec]):
            vmi.append((int(s_), [int(x) for x in pre[s_ * 8:(s_ + 1) * 8]]))
        for s_ in osec:
            vme.append((int(s_), [int(x) for x in die.vm[s_ * 8:(s_ + 1) * 8]]))
        man += rows
        print(f"FWD_PIN case {su_case}: {len(ds)} records, {len(ssec)} source-only + {len(osec)} sink sectors")
    assert len(man) == len(recl)
    vmg = []
    for ci, c in enumerate(cases):
        w = np.zeros(die.vm.size, bool)
        w[wrmask[ci]] = True
        vmg += [int(np.packbits(w[s_ * 8:(s_ + 1) * 8], bitorder='little')[0]) for s_, _ in vme[c[4]:c[4] + c[5]]]
    (out / 'su_vmg.mem').write_text(''.join(f'{x:02X}\n' for x in vmg))
    (out / 'su_price.mem').write_text(''.join(f'{int(round(m["priced"] * 10)):08X}\n' for m in man))
    (out / 'su_aux.svh').write_text('// GENERATED by tools/hgi_unitrate/su_prod_vec.py\n'
                                    f'localparam integer SU_CASE = {su_case};   // the SINK_UNSTAGED case id (-1: none)\n'
                                    f'localparam integer AR0 = {agent[0]}, AW0 = {agent[1]};   // SHARED bench agents\n')
    (out / 'su_rec.mem').write_text(''.join(C.hexw(x, 2197) + '\n' for x in recl))
    (out / 'su_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    (out / 'su_vmi.mem').write_text(''.join(f'{s:08X}' + ''.join(f'{w:08X}' for w in reversed(ws)) + '\n'
                                            for s, ws in vmi))
    (out / 'su_vme.mem').write_text(''.join(f'{s:08X}' + ''.join(f'{w:08X}' for w in reversed(ws)) + '\n'
                                            for s, ws in vme))
    if a.drain_traffic:
        assert a.chain and chain, '--drain-traffic requires a nonempty production chain'
        counts = {}
        for sec, mask, data in drain_traffic:
            counts[sec] = counts.get(sec, 0) + 1
        assert max(counts.values()) <= 8, 'traffic scoreboard needs more than eight writes per sector'
        (out / 'su_drain_traffic.mem').write_text(''.join(f'{sec:08X}{mask:02X}' + ''.join(f'{w:08X}' for w in reversed(data)) + '\n' for sec, mask, data in drain_traffic))
        (out / 'su_drain_traffic.svh').write_text(f'localparam integer NDRAIN_TRAFFIC = {len(drain_traffic)};\n')
    (out / 'su_sizes.svh').write_text('// GENERATED by tools/hgi_unitrate/su_prod_vec.py\n' + ''.join(
        f'localparam integer {k} = {v};\n' for k, v in dict(NREC=len(recl), NCASE=len(cases), NVMI=max(1, len(vmi)),
                                                          NVME=max(1, len(vme))).items()))
    (out / 'su_prod.json').write_text(json.dumps(dict(schema='opentallas.hgi_unitrate.su_prod_vec.v1',
                                                      program=prog_name,
                                                      seed=a.seed, cases=man), indent=1) + '\n')
    emitted = {row['tag'] for row in man}
    for tag in coverage:
        if coverage[tag]['status'] == 'EMITTED_VM_COMPONENT_FIXTURE':
            assert tag in emitted, 'coverage says emitted but no record exists'
    complete = all(item['status'] == 'EMITTED_VM_COMPONENT_FIXTURE' for item in coverage.values())
    coverage_manifest = dict(schema='opentallas.su.actual_canonical_coverage.v1',
        status='ALL_CANONICAL_COMPONENT_RECORDS_EMITTED' if complete else 'FAIL_INCOMPLETE_CANONICAL_COVERAGE',
        qualification='component fixtures only; native programme execution/throughput not qualified',
        source_sha256={str(Path(__file__)): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        required_records=list(coverage.values()), emitted_record_count=len(recl))
    (out / 'su_coverage.json').write_text(json.dumps(coverage_manifest, indent=2) + '\n')
    if not complete and not a.allow_incomplete_coverage:
        raise SystemExit('FAIL_INCOMPLETE_CANONICAL_COVERAGE: see su_coverage.json and actual nonVM fixtures; --allow-incomplete-coverage permits explicitly partial component evidence only')



if __name__ == '__main__':
    main()
