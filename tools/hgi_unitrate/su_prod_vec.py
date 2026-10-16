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
  su_sizes.svh, su_prod.json (manifest with the priced cost of each record: timing.cost at N1024 / M256).
"""
import argparse
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
    ap.add_argument('--seed', type=int, default=20261010)
    ap.add_argument('--chain', action='store_true', help='ONE case: every kept record back to back (the unit may '
                    'overlap them); VM in = the pre-chain state of every touched sector, out = the final sink sectors')
    ap.add_argument('--ds-program', default='', help='a ds_native --program-out dump: use its layer-0 rank-0 records '
                    '(DeepSeek-V4.1 1M) instead of the Qwen3-8B token program')
    a = ap.parse_args()
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
    die.vm[:MA.VM_WORDS] = rng.normal(0.0, 1.0, MA.VM_WORDS).astype(F).view(np.uint32)
    keep = set(a.tags.split(',')) if a.tags else None
    units = {'su': ('SU',), 'sfu': ('SFU',), 'both': ('SU', 'SFU')}[a.unit]
    dyn = T.Dyn(POS)
    recl, cases, vmi, vme, man = [], [], [], [], []
    chain = []
    seen = set()
    for i, (k, L) in enumerate(ex):
        r = recs[k]
        d = tr[i]
        if r.unit not in ('SU', 'SFU'):
            continue
        if any(x.space != 'VM' for x in r.desc.values()):
            continue                                        # STREAM / HBM operands: not a D1 VM record
        if r.unit == 'SU' and r.sut.get('a_ind'):
            print(f"skip {r.tag}: SU gather (a_ind) - the D1 peer refuses it (record fault)")
            continue
        if r.tag in seen:
            break                                           # next layer
        seen.add(r.tag)
        die.dyn[4] = L
        M.cur = r
        try:
            sp = spans(r, M, die, L)
        except MA.Fault as e:
            print(f"skip {r.tag}: {e} (sut a_ind {r.sut.get('a_ind')})")
            continue
        src = np.unique(np.concatenate([v for kk, v in sp.items() if kk not in ('O', 'R')]))
        snk = np.unique(np.concatenate([v for kk, v in sp.items() if kk in ('O', 'R')]))
        if a.chain and r.unit not in units:
            continue                                         # a chain runs one unit's records only, on its own state
        before = die.vm.copy()
        try:
            MA.UNITS[(r.unit, r.op)](M, r, L)
        except MA.Fault as e:
            print(f"skip {r.tag}: {e}")
            die.vm[:] = before
            continue
        changed = np.nonzero(die.vm != before)[0]
        wrote = snk                                          # every sink word the op writes (value may be unchanged)
        assert set(changed) <= set(wrote.tolist()), (r.tag, 'wrote outside its sinks')
        if keep and r.tag not in keep:
            continue
        if r.unit not in units:
            continue
        if a.chain:
            chain.append((r, d, before, src, snk, sp))
            continue
        c, gr, how = T.cost(r, dyn, L) if r.unit != 'SU' else (T.su_cost(r, dyn, L)[0] + 0.0, '', T.su_cost(r, dyn, L)[1])
        secs = np.unique(np.concatenate([src >> 3, snk >> 3]))  # sink sectors are loaded too: their other words guard
        osecs = np.unique(snk >> 3)
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
    (out / 'su_rec.mem').write_text(''.join(C.hexw(x, 2197) + '\n' for x in recl))
    (out / 'su_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    (out / 'su_vmi.mem').write_text(''.join(f'{s:08X}' + ''.join(f'{w:08X}' for w in reversed(ws)) + '\n'
                                            for s, ws in vmi))
    (out / 'su_vme.mem').write_text(''.join(f'{s:08X}' + ''.join(f'{w:08X}' for w in reversed(ws)) + '\n'
                                            for s, ws in vme))
    (out / 'su_sizes.svh').write_text('// GENERATED by tools/hgi_unitrate/su_prod_vec.py\n' + ''.join(
        f'localparam integer {k} = {v};\n' for k, v in dict(NREC=len(recl), NCASE=len(cases), NVMI=max(1, len(vmi)),
                                                          NVME=max(1, len(vme))).items()))
    (out / 'su_prod.json').write_text(json.dumps(dict(schema='opentallas.hgi_unitrate.su_prod_vec.v1',
                                                      program=prog_name,
                                                      seed=a.seed, cases=man), indent=1) + '\n')


if __name__ == '__main__':
    main()
