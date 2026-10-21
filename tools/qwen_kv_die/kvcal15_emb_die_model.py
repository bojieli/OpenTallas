#!/usr/bin/env python3
"""KV-CAL15 10-20: die-composed embedding calendar model for tb_kvcal15_emb_die.sv.

The production es_cfg images (kv_static_programme.es_cfg_words) are compiled by kvjc3_pc_chain.emb_calendar.  On the
route-A static die the PC chain sees per-stack DOWN relays (kvs_ctl.o_hroot -> hroot [+ HROOT_LAND chain] -> kvpc_31) and
RETURN relays (kvpc_31 -> hroot [+ HROOT_LAND embedding] -> kvs_emb), the join start reaches join4_cal `skew` edges before
the fan root, and OT_KV_EMB_PJ delays every join word one edge.  This writes the bench inputs:

  boot.memh   the es_cfg bus words the compiler emits for (down, ret + skew)      [= kv_static_programme law]
  words.memh  expected join word edges relative to the JOIN start (+ PIPE_JOIN)
  bench.svh   `defines: per-stack DUT delay lines (the die's real relays), root-start skew, PIPE_JOIN

Mutants (--mut): 1 = compile without the root/join skew, 2 = compile one return edge short (the HROOT_LAND return
+1 missed), 3 = expectation without the PIPE_JOIN edge, 4 = compile at relays 0 (today's production es_cfg).  Each must FAIL.

    kvcal15_emb_die_model.py --down 83,25,72,16 --ret 67,21,77,32 --skew 1 --pj 1 --out DIR [--mut N]
"""
import argparse
import json
from pathlib import Path

import kvjc3_pc_chain as C3


def build(down, ret, skew, pj, mut=0, ctrl_lat=92):
    m_down = [0] * 4 if mut == 4 else list(down)
    m_ret = [0] * 4 if mut == 4 else [r + (0 if mut == 1 else skew) - (1 if mut == 2 else 0) for r in ret]
    cal = C3.emb_calendar(ctrl_lat, m_down, return_relay=m_ret)
    words = C3.boot_words(cal)
    exp_pj = 0 if mut == 3 else pj
    exp = [dict(edge=w['edge'] + exp_pj, scale=w['scale'], word=w['word']) for w in cal['words']]
    return cal, words, exp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--down', required=True)
    ap.add_argument('--ret', required=True)
    ap.add_argument('--skew', type=int, default=0)
    ap.add_argument('--pj', type=int, default=0)
    ap.add_argument('--mut', type=int, default=0)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    down = [int(x) for x in a.down.split(',')]
    ret = [int(x) for x in a.ret.split(',')]
    if len(down) != 4 or len(ret) != 4 or min(down + ret) < 0 or a.skew < 0 or a.pj not in (0, 1):
        raise SystemExit('need 4 nonnegative down / ret, skew >= 0, pj 0|1')
    cal, words, exp = build(down, ret, a.skew, a.pj, a.mut)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / 'boot.memh').write_text(''.join(f'{ad:02x}{dt:016x}\n' for ad, dt in words))
    (a.out / 'words.memh').write_text(''.join(f'{w["edge"]:04x}{w["scale"]:01x}{w["word"]:02x}\n' for w in exp))
    (a.out / 'bench.svh').write_text(''.join(f'`define OT_KC15_DN{s} {d}\n' for s, d in enumerate(down)) +
                                     ''.join(f'`define OT_KC15_RT{s} {r}\n' for s, r in enumerate(ret)) +
                                     f'`define OT_KC15_SKEW {a.skew}\n`define OT_KC15_PJ {a.pj}\n'
                                     f'`define OT_KC15_LAST {exp[-1]["edge"]}\n')
    (a.out / 'model.json').write_text(json.dumps(dict(down=down, ret=ret, skew=a.skew, pj=a.pj, mut=a.mut,
                                                      last_word=exp[-1]['edge'], calendar={k: cal[k] for k in (
                                                          'issue', 'code_return', 'first_root_beat', 'scale_root_beat',
                                                          'last_word', 'beat_segments', 'relay', 'return_relay')}), indent=1) + '\n')
    print(f'down {down} ret {ret} skew {a.skew} pj {a.pj} mut {a.mut}: last join word {exp[-1]["edge"]} '
          f'(rel join start), boot words {len(words)}')


if __name__ == '__main__':
    main()
