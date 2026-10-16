#!/usr/bin/env python3
"""Q-NETLIST 2026-10-16: compiler image of the compute-die system face's config ROM (rtl/qwen_split/qfd_sys_face.sv).

The ROM is one ot_rom_4096x72_m8 (logical address a -> arr[a//8][bit*8 + a%8], the S81 pq_calendar viamap convention):
  rows 0..1031     program image (PW0..1023 then DW0..7), 64-b words, [71:64] = 0
  rows 2048..      boot records {target4, addr8 = {seg1-base flag, entry7}, 28'd0, data32}; END = target 15 (all else 0)
                   targets: 3 token calendar T (NE 64), 4 layer calendar L (NE 32), 5 embedding calendar E (NE 16),
                            6 first-token offset (events 'first_token', edges after the epoch strobe)
Face calendar events (the face decodes {port3 = class, kind4|beat5 = arg9}; see the RTL header):
  T: STAGE (class 0, arg = stage | 64 L start | 128 token-run | 256 result-capture), MARK (class 5, 64 / 128 without an
     h_start), LEVEL/END (class 1, arg bit0 kok, bit1 kwd, bit2 END -- END must be the last T event).  T's layer / token-run
     flags must coincide with qfd_d2d_cal_seq's cal_start (the face faults otherwise).
  L: LEVEL (1), QSLOT (2, arg = beat; consecutive beats merge into one burst), KVSLOT (3, arg = index),
     VIS (4, arg 0 visibility / 1 complete)
  E: EMBW (6, arg = word 0..63, or 64 = the row-header/scale slot; consecutive words merge per 32), FILL (7)
Every event cycle is the cycle its consumer pin sees the signal, relative to the calendar's start strobe edge; the
calendar + face output registers take CAL_OUT_EDGES edges, which this compiler subtracts (an event earlier than that is
rejected).

usage: sys_face_image.py --events EVENTS.json --program PROGRAM.hex|--bench-program --out DIR
  -> DIR/sys_face_cfg.viamap.hex (the ROM via map), DIR/sys_face_image.json (rows, digest, expected cfg writes / events)
"""
import argparse, json, re, sys
from pathlib import Path

NE = dict(T=64, L=32, E=16)
TARGET = dict(T=3, L=4, E=5, FIRST=6)
BOOT_BASE, PW, DW = 2048, 1024, 8
CAL_OUT_EDGES = 1           # start-sampling edge -> calendar ev register (dt edges) -> face output register (+1): pin = start + cycle
CLASS_OF = dict(T={0, 1, 5}, L={1, 2, 3, 4}, E={6, 7})
BURST = {2, 6}              # classes whose consecutive-cycle events may merge into one burst entry (beat increments)
SEED = 0x51484f5354505247
GO_OFS = 3                  # qfd_sys_face GO_OFS default: the T token-run flag (arg 128) sits at this cycle


def rol7(x):
    return ((x << 7) | (x >> 57)) & (2**64 - 1)


def image_digest(words):
    d = SEED
    for i, w in enumerate(words):
        d = rol7(d) ^ w ^ (i if i < PW else (1 << 10) | (i - PW))
    return d


def entry(dt, last, port, kind, beat, rep=0):
    if not (1 <= dt < (1 << 14) and 0 <= port < 8 and 0 <= kind < 16 and 0 <= beat < 32 and 0 <= rep < 32 and beat + rep < 32):
        raise ValueError(f'calendar entry out of range: dt {dt} port {port} kind {kind} beat {beat} rep {rep}')
    return (dt << 18) | (last << 17) | (port << 14) | (kind << 10) | (beat << 5) | rep


def compile_cal(name, events):
    """events: [(cycle, class, arg)] relative to the calendar start edge (consumer-pin cycles)."""
    ev = sorted((int(c) - CAL_OUT_EDGES, int(k), int(a)) for c, k, a in events)
    if not ev:
        return []
    if ev[0][0] < 1:
        raise ValueError(f'{name}: first event earlier than start + {CAL_OUT_EDGES + 1}')
    cyc = [e[0] for e in ev]
    if len(set(cyc)) != len(cyc):
        raise ValueError(f'{name}: two events on one edge (one calendar plays one event per edge)')
    for c, k, a in ev:
        if k not in CLASS_OF[name] or not 0 <= a < 512:
            raise ValueError(f'{name}: class {k} / arg {a} not legal in this calendar')
    if name == 'T' and not (ev[-1][1] == 1 and ev[-1][2] & 4):
        raise ValueError('T: the last event must be END (class 1, arg bit 2)')
    bursts = []
    for c, k, a in ev:
        if bursts:
            c0, k0, a0, r0 = bursts[-1]
            if k in BURST and k == k0 and c == c0 + r0 + 1 and a == a0 + r0 + 1 and (a0 & 31) + r0 + 1 < 32 and r0 < 31:
                bursts[-1] = (c0, k0, a0, r0 + 1)
                continue
        bursts.append((c, k, a, 0))
    out, prev = [], 0
    for i, (c, k, a, r) in enumerate(bursts):
        out.append(entry(c - prev, int(i == len(bursts) - 1), k, a >> 5, a & 31, r))
        prev = c + r
    if len(out) > NE[name]:
        raise ValueError(f'{name}: {len(out)} entries > NE {NE[name]}')
    return out


def viamap(rows):
    phys = [0] * 512
    for a, w in rows.items():
        if not 0 <= w < 1 << 72:
            raise ValueError('ROM word72')
        for b in range(72):
            if (w >> b) & 1:
                phys[a // 8] |= 1 << (b * 8 + a % 8)
    return ''.join(f'{r:0144x}\n' for r in phys)


def bench_program():
    """Deterministic bench image: PW i = i * 0x9e3779b97f4a7c15 (mod 2^64), footer PW1023 sealed, DW j = 0x5157 << 48 | j."""
    w = [((i + 1) * 0x9e3779b97f4a7c15) & (2**64 - 1) for i in range(PW)]
    w[PW - 1] = (0x58504631 << 32) | (1 << 12) | (1 << 6) | (1 << 2) | 2       # XPF1, cap 1, stage 1, xpf_count 1
    w += [(0x5157 << 48) | j for j in range(DW)]
    return w


def build(events, program, d2d_image=None):
    if len(program) != PW + DW:
        raise ValueError('program image must be PW1024 + DW8 words')
    rows = {i: w for i, w in enumerate(program)}
    recs, writes = [], []
    # the D2D link calendars are qfd_d2d_cal_seq constants (d2d_cal_image.svh), not ROM records
    first = int(events.get('first_token', 0))
    if not 66 < first < 1 << 32:
        raise ValueError('first_token (edges from the epoch strobe) must exceed the D2D sequencer init (2 NE + 2)')
    recs.append((TARGET['FIRST'], 0, first))
    if d2d_image:
        # one value per program shared with the D2D sequencers (Q-LINK d2d_cal_image.svh): the token go lands the token
        # cal_start on D2D_FIRST_TOKEN, and the T calendar's END is the compiled token period
        img = Path(d2d_image).read_text()
        iv = lambda n: int(re.search(rf'{n} = (\d+)', img).group(1))
        if first + GO_OFS != iv('D2D_FIRST_TOKEN'):
            raise ValueError(f'first_token {first} + GO_OFS {GO_OFS} != D2D_FIRST_TOKEN {iv("D2D_FIRST_TOKEN")}')
        ends = [c for c, k, a in events.get('T', []) if k == 1 and a & 4]
        if ends != [iv('D2D_TOKEN_PERIOD')]:
            raise ValueError(f'T END {ends} != D2D_TOKEN_PERIOD {iv("D2D_TOKEN_PERIOD")}')
    tr = [c for c, k, a in events.get('T', []) if k in (0, 5) and a & 128]
    if tr and tr[0] != GO_OFS:
        raise ValueError(f'T token-run flag at cycle {tr[0]}, the RTL D2D sequencer starts at GO_OFS {GO_OFS}')
    cal = {n: compile_cal(n, events.get(n, [])) for n in ('T', 'L', 'E')}
    for n, img in cal.items():
        for i, v in enumerate(img):
            recs.append((TARGET[n], i, v))
    for k, (t, a, d) in enumerate(recs):
        rows[BOOT_BASE + k] = (t << 68) | (a << 60) | d
        writes.append(dict(target=t, addr=a, data=d))
    rows[BOOT_BASE + len(recs)] = 15 << 68
    if BOOT_BASE + len(recs) >= 4096:
        raise ValueError('boot records overflow the ROM')
    return rows, dict(schema='opentallas.qwen.sys-face-image.v1', boot_records=len(recs), cfg_writes=writes,
                      calendars={n: [f'{v:08x}' for v in img] for n, img in cal.items()},
                      program_digest=f'{image_digest(program):016x}', program_footer=f'{program[PW - 1]:016x}',
                      cal_out_edges=CAL_OUT_EDGES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--events', required=True)
    ap.add_argument('--program')
    ap.add_argument('--bench-program', action='store_true')
    ap.add_argument('--d2d-image', help='d2d_cal_image.svh: enforce D2D_FIRST_TOKEN / D2D_TOKEN_PERIOD')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ev = json.loads(Path(a.events).read_text())
    if a.bench_program:
        prog = bench_program()
    else:
        prog = [int(x, 16) for x in Path(a.program).read_text().split()]
    rows, rec = build(ev, prog, a.d2d_image)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / 'sys_face_cfg.viamap.hex').write_text(viamap(rows))
    (out / 'program.memh').write_text(''.join(f'{w:016x}\n' for w in prog))
    (out / 'cfg_writes.memh').write_text(''.join(f"{w['target']:x}{w['addr']:02x}{w['data']:08x}\n" for w in rec['cfg_writes']))
    rec['events'] = ev
    (out / 'sys_face_image.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(boot_records=rec['boot_records'], entries={n: len(v) for n, v in rec['calendars'].items()},
                          digest=rec['program_digest'])))


if __name__ == '__main__':
    sys.exit(main())
