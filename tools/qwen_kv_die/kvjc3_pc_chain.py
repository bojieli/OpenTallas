#!/usr/bin/env python3
"""KVJ-C3 2026-10-17: the static PC chain's join model (kv_static_join_plan.md items 6 + 7).

Ages and the embedding token-run calendar for qkd_kv_es_fan_root -> 4 x 32 qkd_kv_pc_chain_station (inside
qkd_static_kv_pc_path_fan) -> qkd_static_kv_pc_es_merge -> controller, and back over the four return trains
(qkd_embedding_static_return_head + 31 hops) into qkd_embedding_static_join4_cal.  Edge convention: "after edge t" =
the value a register drives once edge t has happened; r = the edge after which the d2d kind-15 RESULT start is present
at the root and join4_cal inputs; w = the edge after which the native writer's outputs of one high-half slot are present.

Every number here is a compiler constant; nothing stretches at run time.  The bench
rtl/test/qwen_static_kv/tb_kvjc3_emb_player.sv plays this calendar on the RTL and checks every join word edge.

    python3 tools/qwen_kv_die/kvjc3_pc_chain.py --ctrl-lat 92 --out DIR [--relay 0,0,0,0]
"""
import argparse
import json
from pathlib import Path

STACKS = ('WS', 'WN', 'ES', 'EN')
N = 32                       # PCs per stack chain (slot 31 nearest the root)
ROOT = 2                     # writer / RESULT output -> root pin flop (+1) -> chain register (+1)
HOP = 1                      # one registered edge per station
PLAYER = 3                   # chain input present -> pin flop (+1) -> counter 0 (+1) -> output register (+1)
MERGE = 2                    # player issue -> strap endpoint es (+1) -> es merge (+1): controller es present
TRAIN_HOP = 2                # return station: two sampled edges per station
REGS = ('ISS', 'RET', 'CAP', 'TRN', 'SISS', 'SRET', 'SCAP', 'STRN')


def chain_in(stack, slot, relay):
    """Edges from the root input to the chain input of PC `slot` of `stack`."""
    return ROOT + relay[stack] + HOP * (N - 1 - slot)


def writer_ages(relay):
    """Writer output edge w -> the PC face (wes) and -> the controller es (after the es merge, +1)."""
    out = {}
    for s, st in enumerate(STACKS):
        for p in range(N):
            a = chain_in(s, p, relay) + 2      # hop pin flop + PC face register
            out[f'{st}_{p}'] = dict(wes_lane01=a, wes_lane23=a + 1, ctrl_es_lane01=a + 1, ctrl_es_lane23=a + 2,
                                    context_lag=1)
    return out


def emb_calendar(ctrl_lat, relay, stack_order=(0, 1, 2, 3)):
    """Absolute edges relative to r, and each PC's 8 player offsets.  ctrl_lat: controller es -> er (exact)."""
    L = ctrl_lat
    issue = PLAYER + max(chain_in(s, 0, relay) for s in range(4))       # earliest edge the farthest player can issue
    ret = issue + MERGE + L
    cap = ret + 1                                                        # strap beat_v = return_slot + 1
    j0 = cap + 1 + TRAIN_HOP * N                                         # first stack's slot 0: T = J0 - 64 = cap + 1
    pcs, beats = {}, []
    u_scale = j0 + 4 * N + 1                                             # one-edge gap after the 128 code beats
    for k, s in enumerate(stack_order):
        for p in range(N):
            u = j0 + N * k + p
            t = u - TRAIN_HOP * (N - p)                                  # transfer: root word at u = t + 2 + 2(31-p)
            i2 = max(ret + 1, t - 2 - L)                                 # scale issue: after the code return, and its
            r2 = i2 + MERGE + L                                          # capture after the code transfer
            c2 = r2 + 1
            t2 = u_scale - TRAIN_HOP * (N - p)
            assert t >= cap + 1 and c2 >= t + 1 and t2 >= c2 + 1, (s, p)
            a = chain_in(s, p, relay)
            ab = dict(ISS=issue, RET=ret, CAP=cap, TRN=t, SISS=i2, SRET=r2, SCAP=c2, STRN=t2)
            off = {x: ab[x] - a - PLAYER for x in REGS}
            assert all(0 <= v < 0xffff for v in off.values()), (s, p, off)
            pcs[f'{STACKS[s]}_{p}'] = dict(stack=s, pc=p, chain_in=a, absolute=ab, offsets=off)
            beats.append(dict(u=u, stack=s, pc=p, word=(s << 4) | (p >> 1), half=p & 1, scale=0))
    # join4_cal: beat_slot after edge r + 3 + off; join word_v after edge u + 2 (join4 pin capture + join register)
    segs = [dict(off=j0 - 3, len=4 * N), dict(off=u_scale - 3, len=1)]
    words = [dict(edge=b['u'] + 2, word=b['word'], scale=0) for b in beats if b['half'] == 1]
    words.append(dict(edge=u_scale + 2, word=0, scale=1))
    return dict(ctrl_lat=L, relay=list(relay), stack_order=list(stack_order), issue=issue, code_return=ret,
                first_root_beat=j0, scale_root_beat=u_scale, last_word=u_scale + 2, beat_segments=segs, words=words,
                pcs=pcs)


def boot_words(cal):
    """(cfg_addr, cfg_data) on the shared boot bus: PC player constants (target 0), join beat calendar (target 1)."""
    out = []
    for d in cal['pcs'].values():
        for reg, x in enumerate(REGS):
            out.append(((d['pc'] << 3) | reg, (d['stack'] << 16) | d['offsets'][x]))
    for k, sgm in enumerate(cal['beat_segments']):
        out.append((k, (1 << 62) | (sgm['len'] << 16) | sgm['off']))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ctrl-lat', type=int, default=92)
    ap.add_argument('--relay', default='0,0,0,0')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    relay = [int(x) for x in a.relay.split(',')]
    cal = emb_calendar(a.ctrl_lat, relay)
    a.out.mkdir(parents=True, exist_ok=True)
    words = boot_words(cal)
    (a.out / 'boot.memh').write_text(''.join(f'{ad:02x}{dt:016x}\n' for ad, dt in words))
    (a.out / 'words.memh').write_text(''.join(f'{w["edge"]:04x}{w["scale"]:01x}{w["word"]:02x}\n' for w in cal['words']))
    rep = dict(schema='opentallas.qwen_kv.kvjc3_pc_chain.v1', model=__doc__.split('\n\n')[0],
               constants=dict(root=ROOT, hop=HOP, player=PLAYER, merge=MERGE, train_hop=TRAIN_HOP),
               writer_ages=writer_ages(relay), embedding=cal, boot_words=len(words))
    (a.out / 'kvjc3_pc_chain.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(f'issue {cal["issue"]} first_root_beat {cal["first_root_beat"]} last_word {cal["last_word"]} '
          f'boot_words {len(words)}')


if __name__ == '__main__':
    main()
