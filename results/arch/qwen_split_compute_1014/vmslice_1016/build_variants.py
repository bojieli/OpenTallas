#!/usr/bin/env python3
"""Q-VMSLICE (10-16): distributed VM slices beside the b2 port pairs, as graph surgery on the generator's relay-skip
graph (q3h final corrected smoke, 178 inst; same buses as q2o3a0).  Evaluation only: no RTL, no GEN.

Variants (slice k sits beside sp_halfres_k / sp_port_tiles_*, k = 0..5: W/E x band 0..2):
  A  6 VM slices, ROW-INTERLEAVED (compiler puts port k's output rows at row = k mod 6); SU / seq_su / native59 /
     xs_tap / tt_ctlm stay central.  rb_k becomes slice-local.  An SU operand window (64 lanes, <= 5 rows) takes <= 1
     row per slice, so sq is 6 x (3 operands x 512 b) and the SU gets the 6-row -> 64-lane rotator; an SU write is
     <= 1 row per slice (512 data + 16 mask + 20 row) + the 150-b read descriptors + 57-b reducer write (multicast).
     Row-serial service ports (one 512-b row a cycle: mx, vwr, ar, svq, q export, write commit, xs_aw) need their full
     width at every slice (writes multicast, reads 6 legs into the consumer's mux).
  C  6 VM slices in BLOCK layout + the SU split into 6 lane slices beside them (each SU slice serves its own block;
     constant ROM absorbed into the SU slice).  VM<->SU local (sq 1024 / sa 395 per slice).  seq_su / native59 /
     xs_tap / tt_ctlm stay central: seq_su command multicast, its operand / address buses split 1/6 per slice, SU->KV
     write split 1/6, SU->xs_tap x stream split 6 x 357 b (equal-rate gather, optimistic), RMSNorm partial sums
     6 x 32 b -> a central reducer -> 32 b multicast back.  Row-serial service ports as A.
  -> m/<base>_<variant>.json (insts + buses, metrics.py schema) and a receipt of the rewiring."""
import json, math, sys, copy, collections
from pathlib import Path
H = Path(__file__).resolve().parent
VM, SU = 'sp_vector_memory', 'sp_su64_sfu'
SW, SH = 1296.0, 2240.0          # VM slice 2.90 mm2 = 15.78 / 6 + ~10 % (decode, merge, row rotator share)
SUW, SUH = 1270.0, 2180.0        # SU lane slice 2.77 mm2 = (11.90 SU + 16 crom groups 1.30) / 6 + ~25 % (crom copies)
GAP = 21.6

def ctr(i): return (i['x'] + i['w'] / 2, i['y'] + i['h'] / 2)

def slice_homes(I, variant):
    """slice k beside halfres_k: W slices against the W port column's inner face, E against the E one; y spans the
    port's output (halftrain) end so rb_k is short.  Band 0: halftrain below the port (y 2.46 mm) -> slice from the
    io_collective top edge up; bands 1 / 2: halftrain above the port -> slices stacked in the free centre column."""
    pw = I['sp_port_tiles_0']; pe = I['sp_port_tiles_0_f1']
    xw = pw['x'] + pw['w'] + GAP; xe = pe['x'] - GAP - SW
    io = I['io_collective']
    y0 = io['y'] + io['h'] + GAP
    y1 = I['sp_halfres_2']['y'] - 300.0          # band 1 halftrain at the port's N end
    y2 = I['sp_port_tiles_2']['y']                # band 2
    ys = [y0, y0, y1, y1, y2, y2]
    out = {}
    occ = [i for n, i in I.items() if n not in (VM,) + ((SU,) if variant == 'C' else ()) and not (variant == 'C' and n.startswith(('cbuf_g_', 'crom_g_')))]
    def free(x, y, w, h):
        return y >= 21.6 and all(min(x + w, o['x'] + o['w']) - max(x, o['x']) <= 0 or min(y + h, o['y'] + o['h']) - max(y, o['y']) <= 0 for o in occ)
    def place(x, y, w, h):
        for d in range(0, 400):
            for yy in (y + d * 21.6, y - d * 21.6):
                if free(x, yy, w, h): return yy
        raise SystemExit(f'no spot near {x},{y}')
    for k in range(6):
        x = xw if k % 2 == 0 else xe
        xs = x + SW + GAP if k % 2 == 0 else x - GAP - SUW
        if variant == 'C':
            y = ys[k]
            for d in range(0, 400):
                cand = [yy for yy in (ys[k] + d * 21.6, ys[k] - d * 21.6) if free(x, yy, SW, SH) and free(xs, yy, SUW, SUH)]
                if cand: y = cand[0]; break
            else: raise SystemExit('no spot')
        else:
            y = place(x, ys[k], SW, SH)
        out[f'vm_s{k}'] = dict(n=f'vm_s{k}', m='qfd_vm_slice_model', x=round(x, 3), y=round(y, 3), w=SW, h=SH); occ.append(out[f'vm_s{k}'])
        if variant == 'C':
            out[f'su_s{k}'] = dict(n=f'su_s{k}', m='qfd_su_slice_model', x=round(xs, 3), y=round(y, 3), w=SUW, h=SUH); occ.append(out[f'su_s{k}'])
    return out

def build(base, variant):
    g = json.load(open(base)); I = {i['n']: i for i in g['insts']}
    new = slice_homes(I, variant)
    drop = {VM} | ({SU} | {n for n in I if n.startswith(('cbuf_g_', 'crom_g_'))} if variant == 'C' else set())
    insts = [i for i in g['insts'] if i['n'] not in drop] + list(new.values())
    if variant == 'C':
        su = I[SU]; insts.append(dict(n='su_red', m='qfd_su_norm_reducer_model', x=su['x'] + su['w'] / 2 - 108, y=su['y'] + su['h'] / 2 - 108, w=216.0, h=216.0))
    S = [f'vm_s{k}' for k in range(6)]; U = [f'su_s{k}' for k in range(6)]
    split = lambda w: [w // 6 + (1 if j < w % 6 else 0) for j in range(6)]
    buses, log = [], collections.defaultdict(list)
    rr = collections.Counter()
    def rrmap(e, pool, key):
        k = rr[key] % 6; rr[key] += 1; return pool[k]
    for b in g['buses']:
        name, cl, w, eps = b
        eps = [e if isinstance(e, str) else e[0] for e in eps]
        touches_vm = VM in eps; touches_su = SU in eps and variant == 'C'
        if cl in ('clock_trunk', 'reset'):
            if touches_vm or touches_su or (variant == 'C' and any(e.startswith(('cbuf_g_', 'crom_g_')) for e in eps)):
                ne = []
                for e in eps:
                    if e == VM: ne.append(rrmap(e, S, 'vmck'))
                    elif e == SU and variant == 'C': ne.append(rrmap(e, U, 'suck'))
                    elif variant == 'C' and e.startswith(('cbuf_g_', 'crom_g_')): continue
                    else: ne.append(e)
                if len(ne) >= 2: buses.append([name, cl, w, ne])
            else:
                buses.append(b)
            continue
        if variant == 'C' and any(e.startswith(('cbuf_g_', 'crom_g_')) for e in eps):
            log['C: constant ROM absorbed into SU slices (bus dropped)'].append((name, w)); continue
        if not touches_vm and not touches_su:
            buses.append(b); continue
        src, sinks = eps[0], eps[1:]
        # --- rb: slice-local
        if name.startswith('b2_rb_'):
            k = int(name.rsplit('_', 1)[1]); buses.append([name, cl, w, [src, S[k]]]); log['rb_k -> slice k (local)'].append((name, w)); continue
        if variant == 'A':
            if name == 'ng_vm_sq_2048':
                for k in range(6): buses.append([f'{name}_s{k}', cl, 1024, [S[k], SU]])
                log['A: SU operands 1,2 = 1 row x 2 per slice'].append((name, w, '6x1024')); continue
            if name == 'ng_vm_sq_0':
                for k in range(6): buses.append([f'{name}_s{k}', cl, 512, [S[k], SU, 'seq_su']])
                log['A: SU operand 0 = 1 row per slice (SU + seq_su)'].append((name, w, '6x512')); continue
            if name == 'ng_su_va_0':
                for k in range(6): buses.append([f'{name}_s{k}', cl, 755, [SU, S[k]]])
                log['A: SU descriptors 150 + 1 write row 548 + rd 57 per slice'].append((name, w, '6x755')); continue
        if variant == 'C':
            if name in ('ng_vm_sq_2048', 'ng_vm_sq_0', 'ng_su_va_0'):
                for k, wk in enumerate(split(w)):
                    buses.append([f'{name}_s{k}', cl, wk, [S[k], U[k]] if src == VM else [U[k], S[k]]])
                    if name == 'ng_vm_sq_0': buses.append([f'{name}_seq_s{k}', cl, wk, [S[k], 'seq_su']])
                log['C: VM<->SU slice-local, 1/6 width'].append((name, w)); continue
            if touches_su and not touches_vm:
                other = [e for e in eps if e != SU]
                if name in ('ng_seq_su_0', 'ng_tt_cp_0'):                       # command words: every slice
                    buses.append([name, cl, w, [src] + U]); log['C: command multicast to 6 SU slices'].append((name, w)); continue
                if name == 'xs_sw':
                    for k, wk in enumerate(split(w)): buses.append([f'{name}_s{k}', cl, wk, [U[k], 'xs_tap']])
                    log['C: x stream gather 6 x 1/6 (equal rate)'].append((name, w)); continue
                if name in ('ng_embed_fault_0',):
                    buses.append([name, cl, w, [src, U[0]]]); continue
                for k, wk in enumerate(split(w)):                               # lane-split operand / address / KV buses
                    if wk == 0: continue
                    ne = [U[k] if e == SU else e for e in eps]
                    buses.append([f'{name}_s{k}', cl, max(wk, 1), ne])
                log['C: SU<->centre bus split 1/6 per slice'].append((name, w)); continue
        # --- row-serial service ports: writes into VM multicast, reads out of VM 6 legs at full width
        if src == VM:
            for k in range(6): buses.append([f'{name}_s{k}', cl, w, [S[k]] + sinks])
            log['row-serial read port: 6 full-width legs'].append((name, w))
        else:
            ne = [src] + [x for e in sinks for x in (S if e == VM else [e])]
            buses.append([name, cl, w, ne]); log['row-serial write port: multicast to 6 slices'].append((name, w))
    if variant == 'C':
        for k in range(6):
            buses.append([f'norm_part_s{k}', 'spine_local', 32, [U[k], 'su_red']])
        buses.append(['norm_scale', 'spine_local', 32, ['su_red'] + U])
        log['C: RMSNorm partial sums + scale broadcast (NEW)'].append(('norm', 32))
    out = dict(insts=insts, buses=buses)
    return out, {k: v for k, v in log.items()}

if __name__ == '__main__':
    base = sys.argv[1]; tag = sys.argv[2]
    rec = {}
    for v in ('A', 'C'):
        d, log = build(base, v)
        p = H / 'm' / f'{tag}_{v}.json'; json.dump(d, open(p, 'w')); rec[v] = log
        # overlap check
        bl = d['insts']; bad = []
        for i in range(len(bl)):
            for j in range(i + 1, len(bl)):
                a, b = bl[i], bl[j]
                if min(a['x'] + a['w'], b['x'] + b['w']) - max(a['x'], b['x']) > 1 and min(a['y'] + a['h'], b['y'] + b['h']) - max(a['y'], b['y']) > 1:
                    if a['m'].endswith('_model') or b['m'].endswith('_model'): bad.append((a['n'], b['n']))
        print(p, 'insts', len(bl), 'buses', len(d['buses']), 'overlaps', bad)
    json.dump(rec, open(H / 'm' / f'{tag}_rewire_receipt.json', 'w'), indent=1)
