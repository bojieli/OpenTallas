#!/usr/bin/env python3
"""TOK-FUNC-QW stage xdie (10-21): bind the ONE shared compute<->KV pair image into a tb_xdie_qwen_exchange calendar dir.

The two dies' calendar sequencers replay the image constants (ot_qwen_d2d_cal_seq_dies_mu_ew595_r16.sv /
qkd_d2d_cal_seq_bc4_ew595_r16.sv include d2d_cal_image_mu_ew595_r16.svh).  The decode-layer (L1..L35) segment is segment 0
of each of the four calendars: entries [0, SEGn_SEG1).  The bench takes its link calendars from CALDIR/cal_{C,K}_{tx,rx}.memh
and the die masters' TXDP from CALDIR/xdie_params.svh (P_TXDP_C / P_TXDP_K).

  xdie_image_cal.py --image IMG.svh --cal CALDIR [--check-only] [--bound-txdp-c HEX --bound-txdp-k HEX]

TOK-QK-XD3 10-26 (no image override of TXDP): with --bound-txdp-c/-k (the words the two STRICT BINDS put on the D2D
masters, read by bound_txdp.py from BINDDIR/rtl), the masters' TXDP in CALDIR/xdie_params.svh is set to the BOUND words,
not to the image's, and the gate TXDP_BOUND (bound == image, per die) is recorded in image_bind.json.  A bound word that
differs from the image -> 'TXDP_BOUND_MISMATCH' on stdout and exit 4 (the bench still simulates the bound word, so the
mismatch is caught twice: statically here and by the simulation).

Compares the bench's law-compiled segment-0 calendars (xdie_exchange_cal.py output already in CALDIR) and TXDP with the
image's, writes CALDIR/image_bind.json, and (unless --check-only) REPLACES the four memh files and the two TXDP words with
the image's -- so the simulation runs on exactly what both dies bind.  The bench's stimulus constants (P_* slot ages of the
outer-pin stimuli) stay the law compile's; a disagreement between image and law then shows up as a simulation FAIL.
"""
import argparse, json, re, sys

NE = 32


def parse(path):
    t = open(path).read()
    lp = {}
    for m in re.finditer(r"localparam\s+(?:\[[^\]]*\]\s*)?(?:integer\s+)?(\w+)\s*=\s*([^;]+);", t):
        v = m.group(2).strip()
        h = re.match(r"\d+'h([0-9a-fA-F_]+)$", v)
        lp[m.group(1)] = int(h.group(1).replace('_', ''), 16) if h else (int(v) if v.isdigit() else v)
    return lp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--image', required=True)
    ap.add_argument('--cal', required=True)
    ap.add_argument('--check-only', action='store_true')
    ap.add_argument('--bound-txdp-c', default=None, help='bound compute D2D master TXDP word (hex)')
    ap.add_argument('--bound-txdp-k', default=None, help='bound KV D2D master TXDP word (hex)')
    a = ap.parse_args()
    lp = parse(a.image)
    rec = dict(image=a.image, calendars={}, mode='check' if a.check_only else 'bind')
    alleq = True
    for k in ('C_TX', 'C_RX', 'K_TX', 'K_RX'):
        img, n = lp[f'D2D_CAL_{k}_IMG'], lp[f'D2D_CAL_{k}_SEG1']
        seg0 = [(img >> (32 * i)) & 0xffffffff for i in range(n)]
        fn = f"{a.cal}/cal_{k[0]}_{k[2:].lower()}.memh"
        law = [int(x, 16) for x in open(fn).read().split()]
        law_nz = law[:max([i + 1 for i, x in enumerate(law) if x] or [0])]
        eq = law_nz == seg0
        alleq &= eq
        rec['calendars'][k] = dict(entries=n, image_seg0=[f'{x:08x}' for x in seg0], law=[f'{x:08x}' for x in law_nz],
                                   equal=eq)
        if not a.check_only:
            open(fn, 'w').write('\n'.join(f'{x:08x}' for x in seg0 + [0] * (NE - n)) + '\n')
    ps = open(f'{a.cal}/xdie_params.svh').read()
    bound = {'C': a.bound_txdp_c, 'K': a.bound_txdp_k}
    if (bound['C'] is None) != (bound['K'] is None):
        print('need both --bound-txdp-c and --bound-txdp-k'); return 2
    txdp_gate = None
    for k in ('C', 'K'):
        m = re.search(rf"P_TXDP_{k} = 32'h([0-9a-f]+);", ps)
        law_w, img_w = int(m.group(1), 16), lp[f'D2D_TXDP_{k}']
        rec[f'TXDP_{k}'] = dict(law=f'{law_w:08x}', image=f'{img_w:08x}', equal=law_w == img_w)
        alleq &= law_w == img_w
        use_w = img_w
        if bound[k] is not None:
            b_w = int(bound[k], 16)
            rec[f'TXDP_{k}'].update(bound=f'{b_w:08x}', bound_equals_image=b_w == img_w, bench=f'{b_w:08x}')
            txdp_gate = (txdp_gate is not False) and b_w == img_w
            use_w = b_w
        if not a.check_only:
            ps = ps.replace(m.group(0), f"P_TXDP_{k} = 32'h{use_w:08x};")
    rec['txdp_source'] = 'bound' if txdp_gate is not None else 'image'
    rec['TXDP_BOUND_gate'] = None if txdp_gate is None else ('PASS' if txdp_gate else 'FAIL')
    if not a.check_only:
        open(f'{a.cal}/xdie_params.svh', 'w').write(ps + f'// TOK-FUNC-QW xdie: calendars from {a.image}; TXDP from the {rec["txdp_source"]}\n')
    rec['token_period'] = lp.get('D2D_TOKEN_PERIOD')
    rec['all_equal_to_law'] = alleq
    json.dump(rec, open(f'{a.cal}/image_bind.json', 'w'), indent=1)
    print(f"IMAGE_BIND {a.image} mode={rec['mode']} law==image seg0+TXDP: {alleq} "
          + ' '.join(f"{k}:{'eq' if v['equal'] else 'DIFF'}" for k, v in rec['calendars'].items())
          + f" TXDP_C:{rec['TXDP_C']['equal']} TXDP_K:{rec['TXDP_K']['equal']}")
    if txdp_gate is not None:
        print(f"TXDP_BOUND {rec['TXDP_BOUND_gate']} bench=bound C {rec['TXDP_C']['bound']} (image {rec['TXDP_C']['image']}) "
              f"K {rec['TXDP_K']['bound']} (image {rec['TXDP_K']['image']})")
        if not txdp_gate:
            print('TXDP_BOUND_MISMATCH bound word != pair image word: the dies as bound do not run this calendar')
            return 4
    return 0


if __name__ == '__main__':
    sys.exit(main())
