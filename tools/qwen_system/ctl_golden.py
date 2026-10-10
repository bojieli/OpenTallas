#!/usr/bin/env python3
"""Golden control trace of the full-shape Qwen3-8B ROM package (stream qwen-system, 2026-10-08).

The stage loop is the C++ host's of the passing P8191 full token (tools/runtime/qwen_baseline_ar_stream4/
qwen_rom_rt_w12_stream4_fulltoken.cpp: per stage rm_layer, rm_next_layer = the next stage's layer, h_start with
{token, position}, wait s_done, consume seq_ntok at the head stage, drain the posted KV write-back after the last
stage) with an embedding stage E in front (r21c: the embedding row comes from HBM).  The token loop and the stop
condition are ot_host_if's (MODE 0): position p takes prompt[p] while p < prompt length, else the fed-back argmax; the
step at p >= plen - 1 emits a generated token; the request ends on EOS (flag + id 0 / 1), on max new tokens, or with an
error completion on a fault; admission rejects plen + max_new > CTX + 1.

Stage table (the contract ot_qfd_dctl drives and the sequencer / memory services consume):
  stage 0 E: prog 0, layer 63 (no KV), crom 63, code / scale base 0
  stage 1 + L: prog 1, layer L, crom L, code base L * 1,056, scale base L * 50,112 (the per-layer stage-image sizes of
               the P8191 run: code_words 1,056 / scale_words 50,112 a layer stage)
  stage 37 H: prog 2, layer 63, crom 36, code base 36 * 1,056, scale base 36 * 50,112 (head 1,584 / 2,376 words)

Writes, for the bench (rtl/test/qwen_system/tb_qfd_ctl_sys.sv):
  stab.svh        `define QFD_STAB <NS*(2+6+2*24) bits>
  scen_<name>.hex scenario: host requests, die argmax schedule, expected per-step stage trace and completions
  golden.json     the scenarios in readable form
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

NS, AW, NW = 38, 24, 18
VOCAB = 151936
CTX = 8192
CODE_W, SCALE_W = 1056, 50112
ST_OK, ST_EOS, ST_LENGTH, ST_BAD_LEN, ST_FAULT = 0, 1, 2, 6, 7   # ot_host_if status codes (checked below)
EV_TOKEN, EV_LAST, EV_ERROR = 1, 2, 3


def stage_table():
    t = [dict(prog=0, layer=63, crom=63, code=0, scale=0)]
    for L in range(36):
        t.append(dict(prog=1, layer=L, crom=L, code=L * CODE_W, scale=L * SCALE_W))
    t.append(dict(prog=2, layer=63, crom=36, code=36 * CODE_W, scale=36 * SCALE_W))
    assert len(t) == NS
    return t


def stab_bits(t):
    v = 0
    for i, e in enumerate(t):
        w = (e['prog'] << (6 + 2 * AW)) | (e['layer'] << (2 * AW)) | (e['code'] << AW) | e['scale']
        v |= w << (i * (2 + 6 + 2 * AW))
    return v


def next_tok(pos, salt=0):
    """The die model's argmax at position pos (deterministic, spans the 18-bit vocabulary)."""
    return (pos * 7919 + 151000 + salt) % VOCAB


def scenario(name, plen, max_new, eos=None, salt=0, eos_at=None):
    """Steps and completions of one request on slot 0 (tag 0x5A00 + scenario index)."""
    prompt = [(1000 + 37 * i) % VOCAB for i in range(plen)]
    ids = [next_tok(p, salt) for p in range(CTX)]
    eos_ids = (0x3FFFE, 0x3FFFF)
    if eos_at is not None:                      # the token generated at the eos_at-th generated step is EOS id 1
        p_eos = plen - 1 + eos_at
        eos_ids = (0x3FFFE, ids[p_eos])
    steps, cq = [], []
    if plen == 0 or max_new == 0 or plen + max_new > CTX + 1:
        cq.append(dict(kind=EV_ERROR, status=ST_BAD_LEN, pos=0, token=0, ngen=0))
        return dict(name=name, plen=plen, max_new=max_new, eos=eos_at is not None, eos_ids=eos_ids, prompt=prompt,
                    steps=steps, cq=cq, salt=salt)
    tok, ngen = None, 0
    for p in range(CTX):
        t = prompt[p] if p < plen else tok
        out = ids[p]
        steps.append(dict(pos=p, token=t, out=out))
        if p + 1 >= plen:
            ngen += 1
            is_eos = eos_at is not None and out in eos_ids
            last = is_eos or ngen == max_new
            cq.append(dict(kind=EV_LAST if last else EV_TOKEN, status=(ST_EOS if is_eos else ST_LENGTH) if last else 0,
                           pos=p, token=out, ngen=ngen))
            if last:
                break
        tok = out
    return dict(name=name, plen=plen, max_new=max_new, eos=eos_at is not None, eos_ids=eos_ids, prompt=prompt,
                steps=steps, cq=cq, salt=salt)


SCENARIOS = [
    dict(name='eos', plen=3, max_new=8, eos_at=4),
    dict(name='length', plen=2, max_new=3),
    dict(name='fullctx', plen=2, max_new=CTX - 1),          # positions 0..8,191: the context limit, every 18-bit token
    dict(name='badlen', plen=2, max_new=CTX),               # plen + max_new = CTX + 2: rejected at admission
]


def write_scen(path, sc, idx):
    """Line format (hex fields): R plen max eos eos0 eos1 tag salt / P token (plen lines) / S pos token out (steps) /
    C kind status pos token ngen (completions)."""
    with open(path, 'w') as fh:
        fh.write(f"R {sc['plen']:x} {sc['max_new']:x} {int(sc['eos']):x} {sc['eos_ids'][0]:x} {sc['eos_ids'][1]:x} "
                 f"{0x5A00 + idx:x} {sc['salt']:x}\n")
        for t in sc['prompt']:
            fh.write(f"P {t:x}\n")
        for s in sc['steps']:
            fh.write(f"S {s['pos']:x} {s['token']:x} {s['out']:x}\n")
        for c in sc['cq']:
            fh.write(f"C {c['kind']:x} {c['status']:x} {c['pos']:x} {c['token']:x} {c['ngen']:x}\n")
        fh.write("E\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    t = stage_table()
    W = NS * (2 + 6 + 2 * AW)
    (a.out / 'stab.svh').write_text(f"`define QFD_STAB {W}'h{stab_bits(t):0{W // 4}x}\n")
    scs = [scenario(**s) for s in SCENARIOS]
    for i, sc in enumerate(scs):
        write_scen(a.out / f"scen_{sc['name']}.hex", sc, i)
    import hashlib
    summ = []
    for sc in scs:
        f = a.out / f"scen_{sc['name']}.hex"
        summ.append(dict(name=sc['name'], plen=sc['plen'], max_new=sc['max_new'], eos=sc['eos'], steps=len(sc['steps']),
                         completions=len(sc['cq']), first=sc['cq'][:2], last=sc['cq'][-1],
                         file_sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    (a.out / 'golden.json').write_text(json.dumps(dict(
        schema='opentallas.qwen_ctl_golden.v1', stage_table=t, scenarios=summ), indent=1))
    for sc in scs:
        print(sc['name'], 'steps', len(sc['steps']), 'completions', len(sc['cq']), 'last', sc['cq'][-1])


if __name__ == '__main__':
    main()
