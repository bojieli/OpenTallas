#!/usr/bin/env python3
"""QW-TLPROD 10-20: the per-layer slice-table load PRODUCER pass of the CALR10 calendar image (static schedule).

Why.  With PRIVATE_CALR = 1 the CTLM calendar (qfd_dv_cmd_cal_mu TABLE_ROM) turns an issued LOCAL kind-4 entry into the
registered table_req {valid, stage, user} that the slices' qfd_dv_slice_tload loaders turn into the per-layer PROG / BTAB /
CROM table install (norm gains and post-scales differ per layer).  The CALR10 capsule (finite_calendar_body) only has 36
caller-selected one-entry preload RANGES (first 868..1008): user 0 starts its layers from the face's dh stage starts, which
carry no range, and the OPSEG leaf refuses user-0 entries -> nothing issued them and layers 2..36 ran with stale tables.

What this pass emits.  ONE stage-relative LOCAL4 entry (bit 10 = REL, field [9:4] = 0; the RTL takes the stage its playhead
was started on) as the FIRST entry of the decode-layer descriptor.  The decode descriptor is shared by stages 1..36, so the
static calendar issues table_req {stage s, user u} at S_s + T_REL of EVERY layer segment s of EVERY user u (user 0 from the
face start, fillers from their OPSEG leaf start that opens the layer's first op group): 36 loads per user, no handshake.
The layer's first original entry (an SU issue, the first possible table consumer) moves to T_REL + CONSUMER_GAP, every later
entry keeps its delta, so the whole layer body shifts by (T_REL + CONSUMER_GAP - T_first) edges (PRICED, see record).

CONSUMER_GAP (edges from the REL entry's issue to the first consumer's issue), from the RTL edge contract
(tools/qwen_static_schedule/f16_calr_edges.py, tools/qwen_layerbench/table_load_contract.py, f16_tload bench):
  table_req rides the cmd lane: same CTLM output register (treq_q beside cmd), same die lane (GEN constraint: equal
  latency), same per-slice row hop (treq_o beside cmd_o) -> the request and an SU word issued d edges later reach slice k
  exactly d edges apart; then tload face register 1 + loader sample 1 + first-read bound 92 after the sample
  (LOADER_FIRST_READ_BOUND: last VM write 91 + read age) = 94 edges after the request's arrival; the SU word is sampled by
  the slice cmd pin register (+1) before it can read a table, credited 0 here (1 edge margin) -> CONSUMER_GAP = 94.
LIFETIME (owed by the layer compiler, tools/qwen_layerbench/table_load_windows.validate): the install of layer s overwrites
the user's table bank; the previous layer's last table read must retire before S_s + T_REL + first write (>= 5 + T_die).
Modes: rel (release), abs1 (mutant: absolute LOCAL4 stage 1 at the same edge -> every layer loads layer 1's tables),
none (mutant: the original capsule, no producer).
usage: calr_table_producer.py --image DIR --out DIR [--mode rel|abs1|none] [--t-rel 8] [--gap 94]
"""
import argparse, hashlib, json, sys
from pathlib import Path

BITS, MUX, NU = 266, 8, 4
T0_MIN = 5 + (NU - 1)                # CALR: first entry of a segment / range T_0 >= 5 + (NU - 1)
TLOAD_FACE, LOADER_SAMPLE, LOADER_FIRST_READ_BOUND, LOADER_LAST_WRITE = 1, 1, 92, 91
CONSUMER_GAP = TLOAD_FACE + LOADER_SAMPLE + LOADER_FIRST_READ_BOUND   # 94
LOCAL, K_TABLE, REL_BIT = 14, 4, 1 << 10
EMASK = (1 << 128) - 1


def read_viamap(path):
    rows = [int(l, 16) for l in Path(path).read_text().split()]
    words = []
    for a in range(len(rows) * MUX):
        r, s, v = rows[a // MUX], a % MUX, 0
        for b in range(BITS):
            if (rows[a // MUX] >> (b * MUX + s)) & 1:
                v |= 1 << b
        words.append(v)
    return words, len(rows)


def write_viamap(words, nrows):
    out = []
    for r in range(nrows):
        v = 0
        for s in range(MUX):
            w = words[r * MUX + s]
            for b in range(BITS):
                if (w >> b) & 1:
                    v |= 1 << (b * MUX + s)
        out.append(f'{v:0{(BITS * MUX + 3) // 4}x}\n')
    return ''.join(out)


def load(img):
    m0, n0 = read_viamap(img / 'calendar_m0.viamap.hex'); m1, n1 = read_viamap(img / 'calendar_m1.viamap.hex')
    dw = [int(l, 16) for l in (img / 'dw.hex').read_text().split()]
    if dw[0] >> 32 != 0x43414C52:
        raise SystemExit('not a CALR10 image')
    nent = dw[0] & 0x3FF
    ents = []
    for r in range(len(m0)):
        w = m0[r] | (m1[r] << BITS)
        if w >> 512:
            raise SystemExit(f'row {r}: spare bits non-zero')
        ents += [(w >> (128 * k)) & EMASK for k in range(4)]
    return dict(m0=m0, m1=m1, nrows=(n0, n1), dw=dw, nent=nent, ents=ents)


def store(img, ents, dw, nrows):
    m0, m1 = [], []
    for r in range(len(ents) // 4):
        w = 0
        for k in range(4):
            w |= ents[4 * r + k] << (128 * k)
        m0.append(w & ((1 << BITS) - 1)); m1.append(w >> BITS)
    return {'calendar_m0.viamap.hex': write_viamap(m0, nrows[0]), 'calendar_m1.viamap.hex': write_viamap(m1, nrows[1]),
            'dw.hex': ''.join(f'{x:016x}\n' for x in dw)}


def is_table_load(e):
    c = e & ((1 << 116) - 1)
    return (c >> 112) == LOCAL and ((c >> 1) & 7) == K_TABLE


def produce(img, mode='rel', t_rel=T0_MIN, gap=CONSUMER_GAP):
    I = load(img)
    ents, dw = list(I['ents']), list(I['dw'])
    nent = I['nent']
    desc = [((d >> 16) & 0x3FF, d & 0x3FF) for d in dw[1:5]]          # stage0, decode, last (head), boot
    df, dn = desc[1]
    if any(is_table_load(ents[k]) for k in range(df, df + dn)):
        raise SystemExit('decode descriptor already holds a table-load entry')
    t_first = ents[df] >> 116
    rec = dict(schema='opentallas.qwen.calr-table-producer.v1', mode=mode, source_dw0=f'{dw[0]:016x}',
               decode_first=df, decode_count_in=dn, t_first_in=t_first)
    if mode == 'none':
        return I, ents, dw, dict(rec, shift_edges=0, loads_per_user=0)
    if t_rel < T0_MIN:
        raise SystemExit(f'T_REL {t_rel} < T0_MIN {T0_MIN} (late = FAULT)')
    stage_f = 0 if mode == 'rel' else 1
    word = (t_rel << 116) | (LOCAL << 112) | (REL_BIT if mode == 'rel' else 0) | (stage_f << 4) | (K_TABLE << 1) | 1
    t_new = max(t_first, t_rel + gap)
    d_new = t_new - t_rel
    if not 1 <= d_new <= 4095:
        raise SystemExit('shifted first delta outside 12 bits')
    body = [((d_new << 116) | (ents[df] & ((1 << 116) - 1)))] + ents[df + 1:df + dn]
    new_dec = [word] + body
    nxt = desc[2][0] if desc[2][1] else nent
    if df + len(new_dec) > nxt:
        raise SystemExit(f'decode grows into the next descriptor ({df + len(new_dec)} > {nxt}): re-pack owed')
    for i, e in enumerate(new_dec):
        ents[df + i] = e
    dw[2] = (dw[2] & ~((1 << 32) - 1)) | (df << 16) | len(new_dec)
    rec.update(decode_count_out=len(new_dec), t_rel=t_rel, consumer_gap=gap, t_first_out=t_new,
               shift_edges=t_new - t_first, loads_per_user=36 if mode == 'rel' else 0,
               table_word=f'{word & ((1 << 116) - 1):029x}', nent=nent, nent_max=1023)
    return I, ents, dw, rec


def check(ents, dw, mode):
    """the produced image as qfd_dv_cmd_cal_mu TABLE_ROM / TABLE_REL reads it: exactly one REL LOCAL4 in decode at T_0 >= 8,
    every descriptor 4-aligned inside nent, the 36 legacy preload ranges intact."""
    fails = []
    nent = dw[0] & 0x3FF
    desc = [((d >> 16) & 0x3FF, d & 0x3FF) for d in dw[1:5]]
    for i, (f, n) in enumerate(desc):
        if n and (f % 4 or f + n > nent):
            fails.append(f'descriptor {i} ({f},{n}) misaligned / outside nent')
        if n and (ents[f] >> 116) < T0_MIN:
            fails.append(f'descriptor {i} first entry T_0 < {T0_MIN}')
    df, dn = desc[1]
    rel = [k for k in range(df, df + dn) if is_table_load(ents[k]) and ents[k] & REL_BIT]
    if mode == 'rel' and (rel != [df] or (ents[df] >> 4) & 63 or (ents[df] & ((1 << 112) - 1)) >> 11):
        fails.append(f'REL table entries in decode: {rel} (want exactly [{df}], field 0)')
    return fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--image', required=True, type=Path); ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--mode', default='rel', choices=['rel', 'abs1', 'none'])
    ap.add_argument('--t-rel', type=int, default=T0_MIN); ap.add_argument('--gap', type=int, default=CONSUMER_GAP)
    a = ap.parse_args()
    I, ents, dw, rec = produce(a.image, a.mode, a.t_rel, a.gap)
    # exact round trip of the source image through this packer (the packer is the RTL's ROM layout)
    rt = store(a.image, I['ents'], I['dw'], I['nrows'])
    for f, txt in rt.items():
        if txt != (a.image / f).read_text():
            raise SystemExit(f'round-trip mismatch on {f}: packer != image layout')
    fails = check(ents, dw, a.mode)
    files = store(a.image, ents, dw, I['nrows'])
    a.out.mkdir(parents=True, exist_ok=True)
    for f, txt in files.items():
        (a.out / f).write_text(txt)
    rec.update(verdict='PASS' if not fails else 'FAIL', fails=fails,
               sha256={f: hashlib.sha256(t.encode()).hexdigest() for f, t in files.items()})
    (a.out / 'producer.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec))
    return 0 if not fails else 1


if __name__ == '__main__':
    sys.exit(main())
