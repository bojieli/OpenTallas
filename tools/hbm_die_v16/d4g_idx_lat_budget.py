#!/usr/bin/env python3
"""HBM-BANKLAT-IDX 10-19: latency BUDGET of the IDX VM clients on a d4g contract (IDX operand readers hb_idx__op_*,
the IDX root share hb_idx__ctl = ot_hbm_idx_rootctl_static_am, ARGMAX hb_argmax = ot_hbm_argmax_static_sw_vm_r2) and the
hub echo / selector lanes of the same tiles, in the conventions of d4g_bank_latency.py (RT = bank 6 + faces pin 1 + lanes).

BUDGET RULE (recorded; the die binds these values and pads every shorter lane UP to them, so the hardened views need not
change when K straps / GEN2d move a lane within the budget):
  * every forwarded landing whose K strap is a NO_E placeholder is counted at its worst case E = 8 (E is 1..8);
  * the four operand readers feed the lockstep xq score tree (rootctl agree_fault: all 4 quadrant lists in the same edge),
    so they take ONE scalar VM_RT_EXTRA = the maximum over the quadrants; the die pads the other readers' request lanes;
  * ctl VM_RT = max_b RT_b - 6 over the 8 SW banks of its rq4/rr4 (scalar: the share serves INDEX / TOPK / ARGMAX);
  * op_SW = 4 + ctl VM_RT + lanes(op_SW <-> ctl) (n12 VM_RT_EXTRA 4 = 2 shell pins + the share's 2 pins);
  * argmax r2 VMX = 5 + ctl VM_RT + lanes(argmax <-> ctl); ACK = 13 + faces pin 1 + lanes(cq) + lanes(cr);
  * ctl CR_RT = faces pin 1 + lanes(cq) + lanes(cr) (TOPK ACK 13 + CR_RT); SEL_LAT = 4 + lanes(sel_op) + lanes(selected_v).

    d4g_idx_lat_budget.py CONTRACT.json [--out budget.json]
"""
import argparse, json, math, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4g_bank_latency as L


def lane(G, hops, worst):
    """(latency, unresolved landings) of a hop list; worst=True counts every NO_E landing at E = 8."""
    lat, half, nl = 0, 0, 0
    for h in hops:
        m = G.m(h)
        if m.startswith('hbfd_rly'):
            lat += 1
        elif re.match(r'^hbfd_lh0?_', m):
            half += 1
        elif re.match(r'^hbfd_(land0?|lnd)_', m):
            note = G.I[h].get('note', '')
            mk = re.search(r'\bK (\d+)', note); mn = re.search(r'\bN (\d+)', note)
            n = int(mn.group(1)) if mn else half
            e = ((int(mk.group(1)) - math.ceil(n / 2)) % 8 or 8) if mk else 1
            if 'NO_E' in note or mk is None:
                nl += 1
                if worst:
                    e = 8
            lat += math.ceil(n / 2) + 1 + e
            half = 0
    if half:
        lat += math.ceil(half / 2)
    return lat, nl


def seg(G, a, ap, b, bits=range(0, 4096)):
    """max lane latency (E as derived, E worst) over the bits of a.ap that reach b."""
    best = None
    for bit in bits:
        outs = [h for (s, h) in G.fwd(a, ap, bit) if s[0] == b]
        if not outs and best is not None and bit > 0:
            continue
        for h in outs:
            x = lane(G, h, False)[0], lane(G, h, True)[0], lane(G, h, True)[1]
            best = x if best is None or x[1] > best[1] else best
        if bit >= 2055:
            break
    return best


def bank_rts(G, cl, rq='vm_rq', rr='vm_rr'):
    out = []
    for b in range(8):
        for (s, h) in G.fwd(cl, rq, 17 * b + 16):
            bk, bp, _ = s
            if not bp.startswith('rq'):
                continue
            ret = [hh for ss, hh in G.fwd(bk, 'rr' + bp[2:], 256) if ss[0] == cl]
            if ret:
                q0, q8, n = lane(G, h, False)[0], *lane(G, h, True)
                r0, r8, m = lane(G, ret[0], False)[0], *lane(G, ret[0], True)
                out.append(dict(bank=bk, rt=7 + q0 + r0, rt_worst=7 + q8 + r8, unresolved=n + m))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('contract'); ap.add_argument('--out')
    a = ap.parse_args()
    G = L.Graph(L.load(a.contract))
    first = lambda a_, p, b: seg(G, a_, p, b, bits=[0])
    S = {}
    S['ctl_banks'] = bank_rts(G, 'hb_idx__ctl')
    for q in ('SE', 'NE'):
        S[f'op_{q}_banks'] = bank_rts(G, f'hb_idx__op_{q}')
    S['nwsh_banks'] = bank_rts(G, 'hb_idx__nwsh')
    S['op_SW_ctl'] = [first('hb_idx__op_SW', 'vm_rq', 'hb_idx__ctl'), first('hb_idx__ctl', 'index_rr', 'hb_idx__op_SW')]
    S['op_NW_nwsh'] = [first('hb_idx__op_NW', 'vm_rq', 'hb_idx__nwsh'), first('hb_idx__nwsh', 'a_rr', 'hb_idx__op_NW')]
    S['argmax_ctl'] = [first('hb_argmax', 'vm_rq', 'hb_idx__ctl'), first('hb_idx__ctl', 'argmax_m', 'hb_argmax')]
    S['ctl_cq_cr'] = [first('hb_idx__ctl', 'cq', 'hb_vms_SW'), seg(G, 'hb_vms_SW', 'cr', 'hb_idx__ctl', bits=range(0, 1200))]
    S['argmax_cq_cr'] = [first('hb_argmax', 'cq', 'hb_vms_SW'), seg(G, 'hb_vms_SW', 'cr', 'hb_argmax', bits=range(0, 1200))]
    S['ctl_sel'] = [first('hb_idx__ctl', 'sel_op', 'hb_idx__selector'), first('hb_idx__selector', 'selected_v', 'hb_idx__ctl')]
    W = lambda pair, i: sum(p[i] for p in pair)          # i = 0 derived E, 1 worst E
    mx = lambda rows, k: max(r[k] for r in rows)
    B = {}
    for i, tag in ((0, 'gen2c_derived_E'), (1, 'budget_worst_E8')):
        k = 'rt' if i == 0 else 'rt_worst'
        ctl_vm_rt = mx(S['ctl_banks'], k) - 6
        nwsh_ex = mx(S['nwsh_banks'], k) - 6
        op = dict(SW=4 + ctl_vm_rt + W(S['op_SW_ctl'], i),
                  SE=4 + mx(S['op_SE_banks'], k) - 8, NE=4 + mx(S['op_NE_banks'], k) - 8,
                  NW=4 + nwsh_ex + W(S['op_NW_nwsh'], i) - 2)
        B[tag] = dict(ctl=dict(VM_RT=ctl_vm_rt, CR_RT=1 + W(S['ctl_cq_cr'], i), SEL_LAT=4 + W(S['ctl_sel'], i)),
                      op_per_quadrant=op, op_uniform_VM_RT_EXTRA=max(op.values()), nwsh_BANK_RT_assumed=nwsh_ex + 6,
                      argmax=dict(VMX=5 + ctl_vm_rt + W(S['argmax_ctl'], i), ACK=14 + W(S['argmax_cq_cr'], i)))
    bud = B['budget_worst_E8']; u = bud['op_uniform_VM_RT_EXTRA']
    pads = dict(
        ctl_rq4=f"pad every SW bank lane of hb_idx__ctl to RT {bud['ctl']['VM_RT'] + 6} (lanes rq4+rr4 = {bud['ctl']['VM_RT'] - 1})",
        op_SW=f"pad hb_idx__op_SW <-> hb_idx__ctl lanes (both directions together) to {u - 4 - bud['ctl']['VM_RT']}",
        op_SE_NE=f"pad every bank lane of hb_idx__op_SE / op_NE to RT {u + 4} (lanes rq+rr = {u - 3})",
        op_NW=f"pad hb_idx__op_NW <-> hb_idx__nwsh lanes to {u - 2 - (bud['nwsh_BANK_RT_assumed'] - 6)} at nwsh BANK_RT "
              f"{bud['nwsh_BANK_RT_assumed']} (HBM-BANKLAT-COLL owns nwsh; lanes = {u + 4} - nwsh BANK_RT)",
        argmax=f"argmax <-> ctl lanes {W(S['argmax_ctl'], 1)} (pad if shorter); cq+cr lanes {W(S['argmax_cq_cr'], 1)}",
        ctl_cq_cr=f"ctl cq+cr lanes {W(S['ctl_cq_cr'], 1)}; sel_op+selected_v lanes {W(S['ctl_sel'], 1)} (SEL_LAT is exact: pad to it)")
    rec = dict(schema='opentallas.d4g_idx_lat_budget.v1', contract=str(a.contract), segments=S, values=B, die_pads=pads,
               rule=__doc__.split('BUDGET RULE')[1].split('d4g_idx_lat_budget.py CONTRACT')[0].strip())
    txt = json.dumps(rec, indent=1)
    if a.out:
        Path(a.out).write_text(txt + '\n')
    print(json.dumps(B, indent=1)); print(json.dumps(pads, indent=1))


if __name__ == '__main__':
    main()
