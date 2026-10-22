#!/usr/bin/env python3
"""RTLGAP-G9 (10-22) G-KV-LEAF: the production D512 KV-leaf programme (GK gain load + KV norm/RoPE/QDQ, opcode 15) on
the G9 KV cut (cut_3N_kv: u_s_3N = ot_s81sl_slice_kv512, KV_ENABLE 1 on leaf 0), through the slice's REAL control path.

Every word enters at the cut boundary as a W-bound tier-line CTL beat on u_s_3N.ri_e (= i__w_xrW_3N_l0..l3_src, the
u_s_4N line-out register, column-4 injector convention of dv_cut_replay.ctl_beat: hops col + 1 = 4, src sid 9):
  target 5 row writes  -> xrt -> leaf 0 store (vp SRAM)          (operand / parameter rows of the SU golden VM images)
  target 0 vp command  -> vp -> s_v/s_d -> ot_s81sl_kv_leaf          (op 15: kind 7 GK at a1 676, kind 1 KV at a1 692)
  target 4 send config + target 0 vp RDOUT (op 6) -> lo row pairs -> xrt pack -> E line beat (kind RD) on ro_e
The results are read back from the cut's output port o__w_xrE_3N_l0..l3_src (trace) and compared bit-exactly with the
SU-golden expected.mem (tools/s81_dv/kv_bank_1021/gate.py, Codex run_286841a83).  Inputs: gain_vm.mem, kv_vm.mem (same
images as the leaf bench).  --mut-row R: flip bit 0 of KV operand row R (negative control: the check must FAIL).
Writes IN (TB replay events "cycle port hex") and plan.json.
"""
import argparse, json
from pathlib import Path

SID, SRC_SID, HOPS = 7, 9, 4            # u_s_3N sid 7; injector u_s_4N sid 9; W-bound arrival at column 3 = col + 1
PORT_L = [1452, 1453, 1454, 1455]       # i__w_xrW_3N_l0..l3_src in tb_slice_top.sv (cut_3N_kv)
K_CTL, K_RD = 0, 4


def mem(p):
    return [int(l, 16) for l in Path(p).read_text().split() if l and not l.startswith('//')]


def vp_cmd(op, a0=0, a1=0, n=0, imm=0):                 # == tools/s81_dv/layer_prog/lower_vs.vp_cmd
    return (op & 0xF) | (a0 & 0x3FF) << 4 | (a1 & 0x3FF) << 14 | (n & 0xFF) << 24 | (imm & ((1 << 128) - 1)) << 32


def ctl_payload(slice_mask, target, leaf_mask, body160):  # == lower_vs.ctl_payload
    return (slice_mask & 0xFFFF) | (target & 0x1F) << 16 | (leaf_mask & 0x1F) << 21 | (body160 & ((1 << 160) - 1)) << 26


def row_write(a10, m4, d128):                             # == lower_vs.row_write
    return (a10 & 0x3FF) | (m4 & 0xF) << 10 | (d128 & ((1 << 128) - 1)) << 14


def beat(target, body):
    p = ctl_payload(1 << SID, target, 0b00001, body)
    return 1 | K_CTL << 1 | HOPS << 4 | SRC_SID << 9 | p << 21


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gain', required=True); ap.add_argument('--kv', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--t0', type=int, default=400)
    ap.add_argument('--mut-row', type=int, default=None)
    ap.add_argument('--in-ports', default=','.join(map(str, PORT_L)),
                    help='tb port indices of i__w_xrW_3N_l0..l3_src (cut-specific; G9 1452..1455, cap22 1760..1763)')
    ap.add_argument('--out-ports', default='1444,1445,1446,1447',
                    help='tb port indices of the E line out o__w_xrE_3N_l0..l3 (G9 _src 1444.., cap22 _lnd 1752..)')
    a = ap.parse_args()
    pin = [int(x) for x in a.in_ports.split(',')]
    assert len(pin) == 4
    G, KV = mem(a.gain), mem(a.kv)
    ev, plan, t = [], [], a.t0

    def put(b, what):
        nonlocal t
        for l, port in enumerate(pin):
            ev.append((t, port, (b >> (276 * l)) & ((1 << 276) - 1)))
            ev.append((t + 1, port, 0))                   # a ONE-cycle pulse of the producer register (dv_cut_replay)
        plan.append(dict(cycle=t, what=what))
        t += 2                                            # one CTL beat every 2 edges (never two in one cycle)

    for r in range(672, 804):                             # GK: parameter rows 672..675 + gain operand rows 676..803
        put(beat(5, row_write(r, 0xF, G[r])), f'row {r} gain image')
    imm_gk = 7 | 1024 << 16                               # kind 7, gain set 0, job 0, DRAIN_AGE 1024
    put(beat(0, vp_cmd(15, 672, 676, 32, imm_gk)), 'op15 GK a0 672 a1 676')
    t += 1300                                             # GK command-to-done 1025 (+ path); one op per leaf at a time
    for r in range(672, 820):                             # KV: parameter rows 672..691 + FP32 operand rows 692..819
        d = KV[r] ^ ((1 << 30) if a.mut_row == r else 0)   # exponent bit 30 of word 0
        put(beat(5, row_write(r, 0xF, d)), f'row {r} kv image' + (' MUTANT word0 bit30' if a.mut_row == r else ''))
    imm_kv = 1 | 1024 << 16                               # kind 1 KV
    put(beat(0, vp_cmd(15, 672, 692, 32, imm_kv)), 'op15 KV a0 672 a1 692')
    t += 1500                                             # KV command-to-done 1130 + drain margin
    send = 0b0001 | K_RD << 4 | 0 << 7 | 0 << 12 | 0 << 28 | 0 << 31 | 3 << 41   # dir E, kind RD, line default hops, 4 pairs
    put(beat(4, send), 'send config E RD 4 pairs')
    t += 8
    rd = []
    for i in range(13):                                   # rows 672..775 (results 672..771) as 13 x 4 row pairs
        rd.append(dict(cycle=t, a0=672 + 8 * i))
        put(beat(0, vp_cmd(6, 672 + 8 * i, 0, 4)), f'RDOUT a0 {672 + 8 * i} n 4')
        t += 18
    o = Path(a.out); o.mkdir(parents=True, exist_ok=True)
    ev.sort(key=lambda x: (x[0], x[1]))
    (o / 'in.txt').write_text(''.join(f'{c}.0 {p} {v:x}\n' for c, p, v in ev))
    (o / 'plan.json').write_text(json.dumps(dict(sid=SID, src_sid=SRC_SID, hops=HOPS, mut_row=a.mut_row, end=t, in_ports=pin, out_ports=[int(x) for x in a.out_ports.split(',')],
                                                 rdout=rd, events=plan), indent=0) + '\n')
    print(f'kvleaf_prog: {len(plan)} CTL beats, last at {t}, NCYC >= {t + 200}')


if __name__ == '__main__':
    main()
