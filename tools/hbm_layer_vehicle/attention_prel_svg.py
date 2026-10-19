#!/usr/bin/env python3
"""Opt-in DS csum8 attention -> real relative SVG + XC event lists.

Each complete independent 8-row op fits one <=64-line cache block. A packet's
cache read is encoded in its own programme word. All configure, probability
store reads, BE clears/publications and mode-only tail words are preserved.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
import att_images as A
import smb_unit as S
from attention_prel_model import model
from hbm_svc_packed136_image import sector_address


def compile_attention(rec, sm=0, mut=''):
    ops, nrun = A.plan_d4g(rec, sub=8)
    ops = [o for o in ops if o[5] == sm]
    store = S.Store(0)
    blocks = []
    for op in ops:
        cal, exp = A.E.compile_op(rec, op[:5], dict(A.E.DEFAULT_LAT), op[1] == 'pv')
        first = min(c for c, f in enumerate(cal.cyc) if f)
        lines = A.op_lines(rec, op[3])
        if not 1 <= len(lines) <= 64:
            raise ValueError('attention block exceeds cache capacity')
        svg, xc = [], []
        for c in range(first, exp['end'] + 1):
            f = cal.cyc[c] if c < len(cal.cyc) else {}
            cmd = A.E.cmd_word(**f)
            rd = None
            if f.get('pkt'):
                packet = cal.pkt[c]
                tag = (packet >> 1088) & 1023
                assert (packet >> 1098) == 1 and tag == f['pkt_tag']
                assert lines[tag] == (packet & ((1 << 1088) - 1))
                rd = (tag, tag)
                if mut == 'wrong_row':
                    rd = ((tag + 1) % len(lines), tag)
            svg.append(S.svg_word(cmd & ((1 << 83) - 1), rd, retire=c == exp['end']))
            xc.append((cmd >> 83) | (cal.kvd.get(c, 0) << 109))
        pb, pl = store.add(svg, xc)
        blocks.append(dict(op=op, cal=cal, exp=exp, first=first, lines=lines, prog=(pb, pl), words=len(svg)))
    if len(blocks) > S.TBL:
        raise ValueError('descriptor overflow')
    ing, xw, mem = [], [], {}
    t = 10
    for a in range(store.top):
        for target, w, width in ((S.SVG_TGT, store.svg[a], 135), (S.XC_TGT, store.xc[a], 173)):
            ing.append((t, S.ingress(cfg=(((0 if a < 1024 else 2) << 10) | (a & 1023), S.prog_row(a, w, width)), target=target)))
            t += 1
    dt = t
    arm = dt + 2 * len(blocks) + 8
    launch, rc0 = arm + 2, arm + 2 + S.OFF
    previous_end = rc0
    for i, b in enumerate(blocks):
        first = max(rc0 + S.FIRST_GO + 8, previous_end + 256)
        # External x-loader completes before this op's first command.
        if b['cal'].xw:
            first = max(first, previous_end + max(b['cal'].xw) + 32)
        offset = first - b['first']
        b.update(offset=offset, go_at=first - rc0 - S.LAT_GO, first_abs=first,
                 end_abs=offset + b['exp']['end'], descriptor=i)
        previous_end = b['end_abs']
        xw.extend((offset + c, w) for c, w in b['cal'].xw.items())
        d = S.desc_row(i, row_base=i * 8, landing=i % 4, epoch=i + 1, rows=len(b['lines']),
                       tag_base=0, prog_base=b['prog'][0], prog_limit=b['prog'][1], go_at=b['go_at'],
                       row_off=0, loops=1, lstep=0, mode=0, mrel=0, fl=0)
        for j, target in enumerate((S.SVG_TGT, S.XC_TGT)):
            ing.append((dt + 2 * i + j, S.ingress(cfg=((1 << 10) | i, d), target=target)))
        raw = b''.join(int(x).to_bytes(136, 'little') for x in b['lines'])
        total = ((len(raw) + 127) // 128) * 4
        raw += bytes(32 * total - len(raw))
        alloc = dict(pcs=[0, 1, 2, 3], row_base=i, stack_bytes=1 << 35)
        for o in range(total):
            sa = sector_address(o, alloc)
            assert sa not in mem
            mem[sa] = int.from_bytes(raw[32 * o:32 * (o + 1)], 'little')
    for j, target in enumerate((S.SVG_TGT, S.XC_TGT)):
        ing.append((arm + j, S.ingress(desc=(0, len(blocks), 1), target=target)))
    ing.append((launch, S.ingress(launch=True)))
    ing.sort(); xw.sort()
    assert len(set(t for t, _ in ing)) == len(ing)
    assert len(set(t for t, _ in xw)) == len(xw)
    return dict(ing=ing, xw=xw, ids=[], mem=mem, n_end=previous_end + 128,
                blocks=blocks, budget=dict(model=model(len({r for o in ops if o[1] == 'qk' for r in o[3]}), kv4=bool(ops[0][2])),
                descriptors=len(blocks), distinct_programmes=len(store.progs), resident_words=store.top,
                available_words=S.PSTORE, attention_reserved_legacy=S.ATT_RESERVED,
                fits_legacy_attention_reservation=store.top <= S.ATT_RESERVED,
                ingress_install_edges=2 * store.top + 2 * len(blocks), run_edges=previous_end - rc0,
                rows_per_sm=sum(len(o[3]) for o in ops if o[1] == 'qk'),
                hbm_lines=sum(len(b['lines']) for b in blocks), provider_gap_edges=0))


def run(a):
    rec, src = A.load_ds(Path(a.kv), a.layer)
    c = compile_attention(rec, a.sm, a.mut)
    d = Path(a.work).resolve() / a.name
    d.mkdir(parents=True, exist_ok=True)
    counts = S.write_events(c, d)
    (d / 'compile.json').write_text(json.dumps(dict(source=src, budget=c['budget'], events=counts,
        blocks=[{k:b[k] for k in ('op','prog','words','go_at','first_abs','end_abs')} for b in c['blocks']]), indent=2) + '\n')
    if not a.exe:
        print(json.dumps(c['budget'], indent=2)); return
    exe = Path(a.exe).resolve()
    r = subprocess.run([str(exe), *(f'+{k}={d}/{v}.hex' for k,v in (('ING','ing'),('XW','xw'),('IDS','ids'),('MEM','mem'))),
                        *(f'+{k}={v}' for k,v in counts.items())], capture_output=True, text=True, cwd=d)
    log = r.stdout + r.stderr
    (d / 'run.log').write_text(log)
    _, gos, _, fault, done = S.parse(log)
    results, pv_nodes, pv_rows = [], [], []
    for b in c['blocks']:
        lo, hi = b['first_abs'], b['end_abs'] + 80
        subset = '\n'.join(line for line in log.splitlines() if line.startswith('R ') and lo <= int(line.split()[1]) <= hi)
        chk = A.E.check(rec, b['op'][:5], b['exp'], subset)
        results.append(dict(name=b['op'][0], **chk))
        if b['op'][1] == 'pv':
            words = [(int(z[1]), int(z[2],16), int(z[3],16)) for z in (line.split() for line in subset.splitlines())]
            pv_nodes.append(A.node_from_words(words).astype(A.np.uint32).view(A.F))
            pv_rows.extend(b['op'][3])
    nnode = 1 << (len(pv_nodes)-1).bit_length()
    merged = A.pv_merge(pv_nodes, nnode)
    golden_chunks = A.B.chunk_sums(rec['p'][pv_rows], rec['K'][pv_rows])
    golden_node = A.B.A.pairwise([golden_chunks[i] for i in range(len(golden_chunks))] +
                               [A.np.zeros(512, A.F)] * (nnode-len(golden_chunks)))
    pv_merge_exact = bool(A.np.array_equal(A.zb(merged), A.zb(golden_node)))
    fixed_go_exact = [(g[1],g[2]) for g in gos] == [(b['prog'][0],b['go_at']) for b in c['blocks']]
    ok = pv_merge_exact and fixed_go_exact and r.returncode == 0 and not fault and bool(done) and len(gos) == len(c['blocks']) and all(x['mismatches'] == 0 and x['results'] == x['expected'] for x in results)
    doc = dict(pass_=ok, mutation=a.mut, source=src, compiler_sha256=S.sha(Path(__file__)),
               event_sha256={p.name:S.sha(p) for p in sorted(d.glob('*.hex'))},
               budget=c['budget'], executable=str(exe),
               executable_sha256=S.sha(exe), rc=r.returncode, fault=fault, done=done, fixed_go_count=len(gos), fixed_go_exact=fixed_go_exact,
               pv_merge=dict(exact=pv_merge_exact, rows=len(pv_rows), nodes=len(pv_nodes), pad=nnode,
                             scope='Python golden-tree composition of actual RTL subrun nodes, no on-die merge claim'), results=results)
    Path(a.out).write_text(json.dumps(doc, indent=2) + '\n')
    print(json.dumps(doc, indent=2))
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--kv', required=True); p.add_argument('--layer', type=int, default=2)
    p.add_argument('--sm', type=int, default=0); p.add_argument('--work', required=True)
    p.add_argument('--name', default='attention'); p.add_argument('--exe'); p.add_argument('--out', default='attention.json')
    p.add_argument('--mut', default='', choices=['','wrong_row'])
    run(p.parse_args())
