#!/usr/bin/env python3
"""Golden streams for qkd_kv_landing_cal from the compiler model (tools/qwen_static_schedule/kv_calendar.py).

For a group (stack s, group e) and context T: the K sector sequence (k_streams of the group's quarter-0 PC, in stream
order) and the V sector sequence (pv16_v_streams, writer VMAP=1 sector of each row), and the put spacing of both
passes (pc_schedule / pc_schedule_paced: put[i] - put[0]).  The bench checks the leaf's closed forms and its timing
arithmetic against these.  Writes one case file per (s, e, T): line 1 = s e T PH0 XU H0 RC LD KGO VGO nk nv KP0 KGAP VP0 VGAP (the pacing constants fitted to the offsets and
asserted exact: off(i) = i before P0, then GAP more before every 8-block),
line 2 = K sectors, line 3 = K put offsets, line 4 = V sectors, line 5 = V put offsets (decimal).

    landing_cal_golden.py OUTDIR  [T ...]
"""
import random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.qwen_static_schedule import kv_calendar as K
from tools.qwen_kv_die import static_kv_calendar as S

P = dict(K.SOURCED, ring_cdc_core_edges=3, layer_period_core=6639, write_ready_core=0, front_nblk=10, ring_depth=64,
         refresh=K.refresh_from_table())


def vsec(t):
    return 512 + ((t >> 6) & 1) * 128 + ((t >> 9) & 15) * 8 + ((t >> 1) & 7)


def pacing(offs):
    """(P0, GAP) with off(i) = i + GAP * (i >= P0 ? 1 + (i - P0) // 8 : 0), asserted exact; (511, 0) if unpaced"""
    p0 = next((i for i in range(1, len(offs)) if offs[i] != offs[i - 1] + 1), None)
    if p0 is None:
        return 511, 0
    gap = offs[p0] - offs[p0 - 1] - 1
    want = [i + (gap * (1 + (i - p0) // 8) if i >= p0 else 0) for i in range(len(offs))]
    if want != offs or p0 % 8 or not 0 < gap < 16:
        raise SystemExit(f'put offsets are not the regular paced form: p0 {p0} gap {gap}')
    return p0, gap


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    Ts = [int(x) for x in sys.argv[2:]] or [1, 77, 700, 2048, 4097, 4300, 4500, 6000, 8192]
    rng = random.Random(1016)
    n = 0
    for T in Ts:
        ks = K.k_streams(T, P); vs = K.pv16_v_streams(T)
        for s in range(4):
            for e in range(8):
                pc = S.physical_pc(s, e, 0)
                kst = ks.get(pc, []); vst = vs.get(pc, [])
                kp = K.pc_schedule(kst, P, 0)['put'] if kst else []
                if vst:
                    start = K._layer_pc_paced(vst, P)[0]
                    vp = K.pc_schedule_paced(vst, P, start)['put']
                else:
                    vp = []
                ksec = [x for x, _, _ in kst]; vsc = [vsec(t) for _, _, t in vst]
                ph0, xu, h0, rc, ld = rng.randrange(768), rng.randrange(768), rng.choice([68, 70, 75]), rng.choice([3, 4]), rng.choice([2, 3, 5])
                kgo = 40 + rng.randrange(768)
                vgo = kgo + 120 + len(ksec) * 2 + rng.randrange(40)
                kp0, kg = pacing([x - kp[0] for x in kp]) if kp else (511, 0)
                vp0, vg = pacing([x - vp[0] for x in vp]) if vp else (511, 0)
                f = out / f'c_{T}_{s}_{e}.txt'
                f.write_text(f'{s} {e} {T} {ph0} {xu} {h0} {rc} {ld} {kgo} {vgo} {len(ksec)} {len(vsc)} {kp0} {kg} {vp0} {vg}\n'
                             + ' '.join(map(str, ksec + [0])) + '\n'
                             + ' '.join(str(x - kp[0]) for x in kp + kp[:1]) + '\n'
                             + ' '.join(map(str, vsc + [0])) + '\n'
                             + ' '.join(str(x - vp[0]) for x in vp + vp[:1]) + '\n')
                n += 1
    print(f'{n} cases in {out}')


if __name__ == '__main__':
    main()
