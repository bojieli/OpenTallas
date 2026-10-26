#!/usr/bin/env python3
"""HBC1 context-load -> first-HBE-header vectors for tb_hostb_stage_hbc (TEST profile, explicit values).

Records are scheduled in the receiver's boot-counter time (static host schedule):
  boot 20  HBC1 LOAD header  (stage/rank strap, seq0, len512, CRC32C(body), clock/reset id, programme, date=body edge 24)
  boot 24  HBC1 body512      (TID16/user/pos/tok/epoch32/programme64/seed/affine book, schema bootstrap_actual417_demand.json)
  boot 30  HBC1 COMMIT       (seq1, len0, repeats CRC/programme)
  boot 124 first HBE1v2 HOST_WORD header (receiver epoch = seed + boot-24 = 1100 = book first_header)
  boot 128 its 512-bit raw body (date48 = 1104)
Modes: 0 positive, 1 wrong TID, 2 wrong epoch, 3 wrong programme, 4 no COMMIT, 5 corrupt HBC body CRC.
"""
import json, sys
from pathlib import Path

def crc(value, initial=0xffffffff):  # identical to tools/s81_dv/hostb_1021/gen_crc.py (dsdv_hostb_crc512)
    q = initial
    for i in range(512):
        b = (q ^ (value >> i)) & 1
        q = (q >> 1) ^ (0x82f63b78 if b else 0)
    return q ^ 0xffffffff

def put(w, lo, width, v):
    assert 0 <= v < 1 << width, (lo, width, v)
    return w | (v << lo)

P = dict(LOCAL_STAGE=1, LOCAL_RANK=0, CLOCK_RESET_ID=0x5381C7C0DE1021, HDR=20, COMMIT=30)
BODY = P['HDR'] + 4
CTX = dict(tid=37, user=0, position=1048575, token=16754, epoch=0x1021, programme=0xf1c617d9224a57bf)
SEED = 1000
FIRST = 1100

def hbc_body(ctx):
    w = 0
    for lo, wd, v in [(0,16,ctx['tid']),(16,10,ctx['user']),(26,21,ctx['position']),(47,21,ctx['token']),
                      (68,32,ctx['epoch']),(100,64,ctx['programme']),(164,48,SEED),(212,48,FIRST),
                      (260,12,16),(272,10,417),(282,8,4),(290,8,4),(298,48,7800),(346,48,8000),
                      (394,48,7900),(442,48,7950),(490,8,P['LOCAL_STAGE']),(498,2,P['LOCAL_RANK'])]:
        w = put(w, lo, wd, v)
    return w

def hbc_header(op, seq, length, crcv, programme, date):
    w = 0
    for lo, wd, v in [(0,32,0x31434248),(32,4,1),(36,4,op),(40,8,P['LOCAL_STAGE']),(48,2,P['LOCAL_RANK']),
                      (50,16,seq),(66,16,length),(82,32,crcv),(114,64,P['CLOCK_RESET_ID']),
                      (178,64,programme),(242,48,date)]:
        w = put(w, lo, wd, v)
    return w

def hbe_header(ctx, date, crcv, host_class=0):
    w = 0
    for lo, wd, v in [(0,32,0x31454248),(32,4,2),(36,4,0),(40,8,P['LOCAL_STAGE']),(48,2,P['LOCAL_RANK']),
                      (50,16,ctx['tid']),(66,10,514),(76,2,host_class),(78,10,ctx['user']),(88,21,ctx['position']),
                      (109,21,ctx['token']),(130,32,ctx['epoch']),(162,48,date),(210,64,ctx['programme']),(274,32,crcv)]:
        w = put(w, lo, wd, v)
    return w

def build(mode):
    body = hbc_body(CTX)
    c = crc(body)
    sent_body = body ^ (1 << 300) if mode == 5 else body   # mode5: corrupt one body bit in flight
    recs = [(P['HDR'], hbc_header(0, 0, 512, c, CTX['programme'], BODY)), (BODY, sent_body)]
    if mode != 4:
        recs.append((P['COMMIT'], hbc_header(1, 1, 0, c, CTX['programme'], P['COMMIT'])))
    hctx = dict(CTX)
    if mode == 1: hctx['tid'] ^= 1
    if mode == 2: hctx['epoch'] ^= 1
    if mode == 3: hctx['programme'] ^= 1 << 63
    host_payload = int.from_bytes(bytes((0x05 + 7 * i) & 0xff for i in range(64)), 'little')  # class0 word, not a boot CSR
    hb = FIRST - SEED + BODY  # boot edge at which receiver_edge == FIRST
    recs.append((hb, hbe_header(hctx, FIRST + 4, crc(host_payload))))
    recs.append((hb + 4, host_payload))
    return recs, host_payload, hb

def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    meta = dict(params=P, context=CTX, seed=SEED, first_header=FIRST, modes={})
    for m in range(6):
        recs, payload, hb = build(m)
        (out / f'm{m}.memh').write_text(''.join(f'{e:012x}{p:0128x}\n' for e, p in recs))
        meta['modes'][m] = dict(records=len(recs), hbe_header_boot=hb, payload=f'{payload:0128x}')
    (out / 'payload.memh').write_text(meta['modes'][0]['payload'] + '\n')
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    print(json.dumps({k: meta['modes'][k]['records'] for k in meta['modes']}))

if __name__ == '__main__':
    main()
