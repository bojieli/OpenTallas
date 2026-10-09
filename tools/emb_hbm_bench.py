#!/usr/bin/env python3
"""Qwen3-8B input embedding in attached HBM (emb-hbm 2026-10-08): bench images, runs and records.

  image  --out D [--ntok N]   golden + boot image for rtl/test/emb_hbm/tb_emb_hbm_e2e.sv from the shipped Qwen3-8B
                              safetensors through the deployed W8 quantizer (qwen3_deployment_quality.quantize_w8, the
                              RTL contract C1: signed per-row INT8 codes + one BF16 row scale).  Tokens: the edge rows
                              (0, the 16-token scale-group and 512-token scale-stack edges, the 1,024-token row-index
                              edges, the last row index 148, the last token 151,935) plus seeded random ids.
  full   --out F              the WHOLE table as the boot load writes it: sector count, bytes, the boot checksum
                              (sum mod 2^32 of zlib.crc32({E LE32, 32 data bytes})) and the HBM footprint.
  run    --img D --out R      compile (iverilog -g2012) and run the bench variants in parallel; PASS / FAIL, latency
                              and refresh statistics; the mutants must FAIL.
  rom    --out R              the replaced ROM path's fill latency (ot_qfd_io_embedding_rom r21f, PINREG 1, with the
                              r21f emb_a / emb relay counts) through the same SU requester, for the cycle comparison.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
SNAP = Path(os.environ.get('QWEN3_8B_SNAPSHOT', str(Path.home() / '.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/'
                                                                     'b968826d9c46dd6066d109eabc6255188de91218')))
VOCAB, HID = 151936, 4096
E_SCALE = VOCAB * 128
NSCALE = VOCAB // 16
RTL = 'rtl/qwen_sys/emb_hbm_20261008'
EDGE_TOKENS = [0, 1, 15, 16, 17, 511, 512, 513, 1023, 1024, 1025, 2047, 2048, 8191, 8192, 65535, 65536, 131071, 131072,
               151551, 151552, 151919, 151920, 151934, 151935]


def emb_rows(start, count):
    """(codes uint8 [count, 4096], scale bf16 bits uint16 [count]) of embedding rows start .. start + count - 1."""
    import torch
    from safetensors import safe_open
    from qwen3_deployment_quality import quantize_w8
    torch.set_num_threads(int(os.environ.get('EMB_THREADS', '4')))
    index = json.loads((SNAP / 'model.safetensors.index.json').read_text())['weight_map']
    key = 'model.embed_tokens.weight'
    with safe_open(str(SNAP / index[key]), framework='pt', device='cpu') as sf:
        rows = sf.get_slice(key)[start:start + count]
    codes, scales, _ = quantize_w8(rows.float())
    return codes.numpy().view(np.uint8), scales.view(torch.int16).numpy().view(np.uint16).reshape(-1)


def decode_fp32(code_u8, scale_bits):
    """ot_hdc_qwen_int8_embed_decode: the exact FP32 code x BF16 scale, +0 for a zero code (bit pattern)."""
    c = code_u8.view(np.int8).astype(np.float32)
    s = (np.uint32(scale_bits) << np.uint32(16)).astype(np.uint32).view(np.float32)
    v = (c * s).astype(np.float32).view(np.uint32)
    v[code_u8 == 0] = 0
    return v


def crc_sector(e, data32):
    return zlib.crc32(int(e).to_bytes(4, 'little') + bytes(data32))


def image(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(20261008)
    toks = list(EDGE_TOKENS)
    while len(toks) < a.ntok:
        t = rnd.randrange(VOCAB)
        if t not in toks:
            toks.append(t)
    toks = toks[:a.ntok]
    # the UE test is the last fetch (fail closed ends the run); the CE test an early edge token
    ce_ix, ue_ix = 5, len(toks) - 1
    groups = sorted({t >> 4 for t in toks})
    code = {}
    scale_bits = {}
    for g in groups:
        c, s = emb_rows(g * 16, min(16, VOCAB - g * 16))
        for j in range(len(s)):
            scale_bits[g * 16 + j] = int(s[j])
            if g * 16 + j in toks:
                code[g * 16 + j] = c[j]
    boot = []                      # (E, 32 data bytes)
    for t in toks:
        row = code[t]
        for i in range(128):
            boot.append((t * 128 + i, row[32 * i:32 * i + 32].tobytes()))
    for g in groups:
        sec = bytearray(32)
        for j in range(16):
            sb = scale_bits.get(g * 16 + j, 0)
            sec[2 * j:2 * j + 2] = sb.to_bytes(2, 'little')
        boot.append((E_SCALE + g, bytes(sec)))
    cnt = len(boot)
    csum = sum(crc_sector(e, d) for e, d in boot) & 0xffffffff
    with open(out / 'boot.hex', 'w') as f:
        for e, d in boot:
            f.write('%071x\n' % ((int.from_bytes(d, 'little') << 25) | e))
    with open(out / 'tokens.hex', 'w') as f:
        f.write(''.join('%05x\n' % t for t in toks))
    with open(out / 'gcode.hex', 'w') as gc, open(out / 'gfp.hex', 'w') as gf:
        for t in toks:
            row = code[t]
            for w in range(64):
                gc.write('%0128x\n' % int.from_bytes(row[64 * w:64 * w + 64].tobytes(), 'little'))
            gc.write('%0128x\n' % scale_bits[t])
            gf.write(''.join('%08x\n' % v for v in decode_fp32(row, scale_bits[t])))
    meta = [cnt, csum, len(toks), cnt, ce_ix, ue_ix]
    (out / 'meta.hex').write_text(''.join('%08x\n' % m for m in meta + [0] * (16 - len(meta))))
    rec = dict(schema='opentallas.emb_hbm_bench_image.v1', snapshot=str(SNAP.name), tokens=toks, ce_index=ce_ix,
               ue_index=ue_ix, boot_sectors=cnt, boot_checksum=csum, scale_groups=len(groups),
               quantizer='qwen3_deployment_quality.quantize_w8 (W8, C1)',
               sha256={n: hashlib.sha256((out / n).read_bytes()).hexdigest()
                       for n in ('boot.hex', 'tokens.hex', 'gcode.hex', 'gfp.hex', 'meta.hex')})
    (out / 'image.json').write_text(json.dumps(rec, indent=1) + '\n')
    gen_svh(out)
    print(json.dumps({k: rec[k] for k in ('boot_sectors', 'boot_checksum', 'scale_groups')}))


def gen_svh(out):
    """the bench's per-PC hierarchical case lists (generate-block indices must be constants)."""
    fl, vs = [], []
    for k in range(4):
        for q in range(32):
            p = f'g_stk[{k}].g_pc[{q}].u_dram'
            fl.append(f"                7'd{k * 32 + q}: begin {p}.flip(lc[17:13], rw, lc[12:8], ba, bb);"
                      f" if (TWIN != 0) {p}.flip(lc[17:13] ^ 5'd2, 19'(rw + 19'(TWIN_ROFF)), lc[12:8], ba, bb); end\n")
            vs.append(f'            vt = vt + {p}.viol;\n')
    d = ROOT / 'rtl/test/emb_hbm'
    (d / 'tb_emb_flip_cases.svh').write_text(''.join(fl))
    (d / 'tb_emb_viol_sum.svh').write_text(''.join(vs))


def full(a):
    """count / bytes / checksum of the whole table as the boot load writes it (rows in windows of 4,096)."""
    t0 = time.time()
    cnt, csum, nbytes = 0, 0, 0
    h = hashlib.sha256()
    scales = np.zeros(VOCAB, dtype=np.uint16)
    for r0 in range(0, VOCAB, 4096):
        n = min(4096, VOCAB - r0)
        c, s = emb_rows(r0, n)
        scales[r0:r0 + n] = s
        h.update(c.tobytes()); h.update(s.tobytes())
        flat = c.reshape(n, 128, 32)
        for j in range(n):
            base = (r0 + j) * 128
            row = flat[j]
            for i in range(128):
                csum += zlib.crc32((base + i).to_bytes(4, 'little') + row[i].tobytes())
        cnt += n * 128
        nbytes += c.nbytes
    for g in range(NSCALE):
        d = scales[16 * g:16 * g + 16].astype('<u2').tobytes()
        csum += crc_sector(E_SCALE + g, d)
        cnt += 1
    nbytes += VOCAB * 2
    rec = dict(schema='opentallas.emb_hbm_full_table.v1', snapshot=str(SNAP.name), rows=VOCAB, hidden=HID,
               sectors=cnt, code_sectors=VOCAB * 128, scale_sectors=NSCALE, table_bytes=nbytes,
               boot_checksum=csum & 0xffffffff, table_sha256=h.hexdigest(),
               hbm=dict(row_indices_a_copy=149, bytes_a_copy=149 * 128 * 32 * 1024,
                        ecc_sideband_bits_a_sector=32,
                        die_hbm_bytes=4 * 24 * 2**30, share_a_copy=149 * 128 * 32 * 1024 / (4 * 24 * 2**30)),
               seconds=round(time.time() - t0, 1))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec))


SRCS = [f'{RTL}/ot_qfd_emb_pkg.sv', f'{RTL}/ot_hbm_r14_stream_pc_srow.sv', f'{RTL}/ot_qwen_ctrl_pc_emb.sv',
        f'{RTL}/ot_qfd_emb_pcport.sv', f'{RTL}/ot_qfd_emb_strip.sv', f'{RTL}/ot_qfd_link_far.sv', f'{RTL}/ot_qfd_emb_gw.sv',
        f'{RTL}/ot_qwen_die_hub_emb.sv', 'rtl/physical/ot_qwen_die_cdc_ch.sv', 'rtl/lib/ot_async_fifo.sv',
        'rtl/lib/ot_reset_sync.sv', 'rtl/hdc/ot_hdc_delay.sv', 'rtl/qwen_sys/rtl_finish_20261007/ot_qfd_su_master.sv',
        'rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv', 'rtl/test/emb_hbm/tb_emb_dram_pc.sv', 'rtl/test/emb_hbm/tb_emb_hbm_e2e.sv']
VARIANTS = {  # name: (params, expect)
    'base_kv1': (dict(TWIN=0, KVMODE=1), 'PASS'),
    'twin_kv1': (dict(TWIN=1, KVMODE=1), 'PASS'),
    'base_kv2': (dict(TWIN=0, KVMODE=2), 'PASS'),
    'twin_kv2': (dict(TWIN=1, KVMODE=2), 'PASS'),
    'base_kv0': (dict(TWIN=0, KVMODE=0), 'PASS'),
    'mut_row': (dict(MUT_STRIP=1), 'FAIL'),
    'mut_scale': (dict(MUT_STRIP=2), 'FAIL'),
    'mut_ecc': (dict(MUT_STRIP=3), 'FAIL'),
    'mut_gate': (dict(MUT_GW=4), 'FAIL'),
}


def run_one(name, params, img, work):
    wd = Path(work) / name
    wd.mkdir(parents=True, exist_ok=True)
    vvp = wd / 'tb.vvp'
    ps = [f'-Ptb_emb_hbm_e2e.{k}={v}' for k, v in params.items()]
    cmd = ['iverilog', '-g2012', '-I', 'rtl/test/emb_hbm', '-s', 'tb_emb_hbm_e2e', '-o', str(vvp)] + ps + SRCS
    t0 = time.time()
    c = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if c.returncode:
        return name, dict(status='COMPILE_ERROR', log=c.stderr[-3000:])
    r = subprocess.run(['vvp', '-n', str(vvp), f'+dir={img}'], cwd=ROOT, capture_output=True, text=True)
    (wd / 'sim.log').write_text(r.stdout + r.stderr)
    lines = r.stdout.splitlines()
    verdict = 'PASS' if any(l.startswith('PASS emb_hbm_e2e') for l in lines) else 'FAIL'
    stats = next((l for l in lines if l.startswith('STATS')), '')
    st = {m.group(1): m.group(2) for m in re.finditer(r'(\w+)=([^\s]+)', stats)}
    lat = []
    lp = Path(img) / 'lat.txt'
    return name, dict(status=verdict, stats=st, seconds=round(time.time() - t0, 1),
                      tail=[l for l in lines if l.startswith(('FAIL', 'PASS', 'BOOT', 'UE', 'STATS'))][-12:])


def run(a):
    img = Path(a.img).resolve()
    names = a.only.split(',') if a.only else list(VARIANTS)
    res = {}
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futs = [ex.submit(run_one, n, VARIANTS[n][0], img, a.work) for n in names]
        for f in cf.as_completed(futs):
            n, r = f.result()
            r['expect'] = VARIANTS[n][1]
            r['ok'] = r['status'] == r['expect']
            res[n] = r
            print(n, r['status'], 'expect', r['expect'], r.get('stats', {}).get('lat_mean'), flush=True)
    rec = dict(schema='opentallas.emb_hbm_bench_run.v1', image=json.loads((img / 'image.json').read_text()),
               variants=res, all_ok=all(r['ok'] for r in res.values()))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('image'); p.add_argument('--out', required=True); p.add_argument('--ntok', type=int, default=48)
    p = sp.add_parser('full'); p.add_argument('--out', required=True)
    p = sp.add_parser('run'); p.add_argument('--img', required=True); p.add_argument('--out', required=True)
    p.add_argument('--work', default='/tmp/emb/runs'); p.add_argument('--jobs', type=int, default=6)
    p.add_argument('--only', default='')
    a = ap.parse_args()
    dict(image=image, full=full, run=run)[a.cmd](a)


if __name__ == '__main__':
    main()
