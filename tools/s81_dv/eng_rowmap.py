#!/usr/bin/env python3
"""RTL-BUILD-S81 (owner 0dv 10-18): the compiler's static Engram K / V / W row map onto the DV slices (slice op ENG).

The Engram mix is an in-slice op (mix4_half deleted): every operand is beat-resident in the beat leaf that owns the
h elements (ot_s81dv_norm header: slice g owns global beats g*NVL .. g*NVL+NVL-1, i.e. elements [320 g, 320 g + 320);
leaf k of slice g holds beat 5 g + k = elements 320 g + 64 k .. +64).

engram.wkv (FP8 matvec on the ROM field, [25,600 x 6,144]) returns its 25,600 output rows through the frames' column
return trees into the OWNING slice's capture root (ot_s81sl_cap):
    row r = j * 5120 + e   (key copy j = 0..3, element e)     row r = 20480 + e   (value element e)
The capture decode is the RTL's (ot_s81sl_cap DEC, tools/s81_slice/cap_model.decode):
    e' = row - rbase; chunk = e' >> 6; leaf = chunk % 5; wrap = chunk // 5; word = obase + pos * ops + 64 wrap + e'[5:0]
so the compiler issues, per Engram layer and per slice g, FIVE capture phases (cfg_v / cfg_d), one per vector
v in (K0, K1, K2, K3, V): rbase = base(v) + 320 g, rcnt = 320, np = 0, fmt = 1 (FP32: the golden kv is FP32),
obase = 4 * (A0 + ROW_OFF[v]) (word address = {row 10, word 2}).  With rcnt = 320 the wrap is 0: element e lands in
leaf (e % 320) // 64, leaf-store row A0 + ROW_OFF[v] + (e % 64) // 4, word e % 4 -- element order, so a vs extension
row-pair read (rows a, a + 1) is 8 consecutive elements.

W = q_weight * k_weight (golden engram_layer `wgt`, FP32, [4, 5120]) is a per-layer CONSTANT: written once at load by
leaf-store row writes (vp command 5 / sw_*: {a 10, m 4, d 128}) at rows A0 + 64 + 16 j + (e % 64) // 4.  1 KiB per leaf
per Engram layer (4 copies x 64 x FP32).

Leaf-store region per Engram layer (relative to A0; vs op 14 ENG takes A0 in its command a0 field):
    K_j  rows A0 + 16 j        (j = 0..3)      16 rows each (64 FP32)
    W_j  rows A0 + 64 + 16 j                   16 rows each (constant)
    V    rows A0 + 128                         16 rows
    total 144 rows of the 1,024-row leaf store; A0 even (row-pair reads start on bank 0).
Default A0 per Engram layer: L1 -> 704, L14 -> 848 (rows 704..991; rows 992..1023 and 0..703 stay with the other ops).

Usage: eng_rowmap.py [--out results/arch/s81_dv_1016/eng/kv_rowmap.json]
"""
import argparse
import json
from pathlib import Path

D, HC, NS, NVL, BEAT = 5120, 4, 16, 5, 64
SLICE_E = NVL * BEAT                      # 320 elements per slice
VECS = ['K0', 'K1', 'K2', 'K3', 'V']
ROW_BASE = {'K0': 0, 'K1': 5120, 'K2': 10240, 'K3': 15360, 'V': 20480}   # wkv output row of element 0
ROW_OFF = {'K0': 0, 'K1': 16, 'K2': 32, 'K3': 48, 'V': 128}              # leaf-store row offset from A0
W_OFF = [64, 80, 96, 112]                                                 # W_j row offset from A0
REGION_ROWS = 144
A0 = {'L1': 704, 'L14': 848}
LEAF_ROWS = 1024


def cfg_word(obase, ops, np_, fmt, rbase, rcnt, rsplit=0, lo32=0, hi32=0):
    """ot_s81sl_cap cfg_d[159:0] (header): [11:0] obase [23:12] ops [26:24] np [28:27] fmt [44:29] rbase [55:45] rcnt
    [71:56] rsplit [72] lo32 [73] hi32"""
    return (obase | ops << 12 | np_ << 24 | fmt << 27 | rbase << 29 | rcnt << 45 | rsplit << 56 | lo32 << 72 |
            hi32 << 73)


def build():
    layers = {}
    for L, a0 in A0.items():
        assert a0 % 2 == 0 and a0 + REGION_ROWS <= LEAF_ROWS
        slices = []
        for g in range(NS):
            ph = []
            for v in VECS:
                cfg = dict(obase=4 * (a0 + ROW_OFF[v]), ops=0, np=0, fmt=1, rbase=ROW_BASE[v] + SLICE_E * g,
                           rcnt=SLICE_E, rsplit=0, lo32=0, hi32=0)
                ph.append(dict(vector=v, cfg=cfg, cfg_d=hex(cfg_word(cfg['obase'], 0, 0, 1, cfg['rbase'], SLICE_E))))
            w = [dict(copy=j, leaf=k, rows=[a0 + W_OFF[j], a0 + W_OFF[j] + 15],
                      elements=[SLICE_E * g + BEAT * k, SLICE_E * g + BEAT * k + BEAT - 1])
                 for j in range(HC) for k in range(NVL)]
            slices.append(dict(slice=g, h_beats=[g * NVL, g * NVL + NVL - 1], capture_phases=ph, w_row_writes=w))
        layers[L] = dict(A0=a0, slices=slices)
    return dict(
        schema='opentallas.s81_dv.eng_rowmap.v1', lane='RTL-BUILD-S81', date='2026-10-18',
        decision='HANDOFF 0dv (owner 10-18): mix4_half deleted, Engram mix = in-slice op ENG',
        wkv_rows='K copy j element e -> row 5120 j + e; V element e -> row 20480 + e (golden engram_layer kv split)',
        owner='element e -> slice e // 320, leaf (e % 320) // 64, element-in-beat e % 64 (= the h owner)',
        leaf_layout=dict(row_off=ROW_OFF, w_row_off=W_OFF, region_rows=REGION_ROWS, word_of_element='(e % 64) % 4',
                         row_of_element='A0 + off + (e % 64) // 4'),
        vs_op14_contract=('vs op 14 ENG: a0 = A0 (command [13:4]); reduce copy j reads row pairs K_j (A0 + 16 j + 2 i, '
                          '+1) and W_j (A0 + 64 + 16 j + 2 i, +1), i = 0..7 (8 elements a pair) with h from vn; add reads V '
                          'row pairs A0 + 128 + 2 i once per sub-beat, shared by the 4 copies'),
        capture='5 phases per slice per Engram layer: fmt 1 (FP32), np 0, rcnt 320, rbase = row of element 320 g',
        layers=layers)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='results/arch/s81_dv_1016/eng/kv_rowmap.json')
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(build(), indent=1))
    print(a.out)


if __name__ == '__main__':
    main()
