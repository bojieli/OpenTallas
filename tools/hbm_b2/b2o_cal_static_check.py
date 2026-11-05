#!/usr/bin/env python3
"""HBM-21 (SS39-TOK, COORD 11-05 14:30 ruling (A)): static check of compiled B2o calendar images, no simulation.

Proof conditions of ledger row HBM-21 (SS33-TOK 11-05 07:33 (4)), checked on the words the programme SRAM will hold:
  1. no slot-0 grant on vmb_S* : an S-role VM calendar word that grants read group 0 (rq0) or write group 0 (wq0) on a
     bank FAILS, unless that word is in the calendar's declared FUSED allow-list (C2 option (a), COORD 11-05 08:01: the
     FUSED pair leaf ot_hnx_fused_vm_pair now owns rq0/wq0 of the S banks, so its slots are the only legal group-0
     grants there).  Any lg_local_read/lg_local_write bit on an S calendar FAILS (su lg = C4b tie, no local SU).
  2. no dq fill : an S-role word granting write owner WG+4 (the DMA/dq leaf, g_dma in ot_vms_bank_q0_faces_body) FAILS
     (C4c: vmb_*_mu1 .dq is tied 281'b0 on the top).
  3. qctl_S nq = 0 : ot_hbm_idx_qctl_static computes nq = (nkeys <= base) ? 0 : min(nkeys-base, 2736); an S-role qctl
     descriptor with nkeys > base FAILS.

B2o facts used (vh1 top v0dl/sel.sv, hbm_arch_q_hub__q_hub_{ne,nw}):
  u_vmb_Q<k>      (N role) takes rslot/wslot from u_calendar_Q_q1 bits [3k+:3];
  u_vmb_Q<k>_mu1  (S role) takes rslot/wslot from u_calendar_Q_q0 bits [3k+:3], rq0/wq0 from u_fvp_Q<k>, dq = 0;
  bank body ot_vms_bank_q0_faces_body #(.RG(5),.WG(2)): read owners 0..4 = rq0..rq4, 5 = packet; write owners
  0,1 = wq0,wq1, 2 = coll kq, 3 = cw, 4 = packet, 5 = ccw, 6 = dma dq.
  Calendar master hfd_hgi_vm_calendar_f20 = universal layout of hfd_hgi_vm_calendar.sv (word: 0xc7a1 at [255:240],
  pc at [233:224], payload [186:0]).

Input manifest (JSON, schema opentallas.hbm.b2o_cal_check.v1):
  {"calendars": [{"name": "NW.u_calendar_Q_q0", "role": "S"|"N", "programme": <compile_schedule output json path or
                  inline object>, "allow_group0": {"read": [pc...], "write": [pc...]}}],
   "qctl": [{"name": "NW.u_hb_idx_qctl_Q_q0", "role": "S"|"N", "nkeys": int, "base": int}]}
N-role entries are decoded (header/pc/payload checks) but carry no HBM-21 rule.
Output: verdict JSON {verdict PASS|FAIL, findings[...], counts}.  Exit 0 on PASS, 1 on FAIL, 2 on bad input.
Scope: only the finite images given; it does not prove the images match the producers' requests (the tokens-vs-reference
run on vh1 does that).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAL_SRC = ROOT / 'rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar.sv'
RG, WG = 5, 2
RB, WB = 3, 3
DQ_OWNER = WG + 4
PAYLOAD_BITS = 187
NQ_MAX = 2736


def field_layout(src=CAL_SRC):
    text = Path(src).read_text()
    f = {n: (int(lo), int(b)) for n, lo, b in re.findall(r'assign\s+(\w+)\s*=\s*calendar\[(\d+)\+:(\d+)\]', text)}
    need = ('rslot_v', 'wslot_v', 'rslot', 'wslot', 'lg_local_read', 'lg_local_write')
    missing = [n for n in need if n not in f]
    if missing:
        raise ValueError(f'calendar source lacks fields {missing}')
    return f


def get(word, f, name):
    lo, bits = f[name]
    return (word >> lo) & ((1 << bits) - 1)


def check_calendar(entry, f, findings, counts):
    name, role = entry['name'], entry['role']
    prog = entry['programme']
    if not isinstance(prog, dict):
        prog = json.loads(Path(prog).read_text())
    writes = prog['configuration_writes']
    start = prog.get('start', {})
    lo_pc = start.get('base', 0)
    hi_pc = start.get('limit', lo_pc + len(writes))
    allow = entry.get('allow_group0', {})
    allow_r, allow_w = set(allow.get('read', [])), set(allow.get('write', []))
    seen = set()
    for w in writes:
        pc, word = int(w['addr']), int(w['data'], 16)
        seen.add(pc)
        if word >> 240 != 0xc7a1 or (word >> 224) & 0x3ff != pc or (word >> 234) & 0x3f:
            findings.append(dict(kind='HEADER', calendar=name, pc=pc))
            continue
        if word & (((1 << 224) - 1) ^ ((1 << PAYLOAD_BITS) - 1)):
            findings.append(dict(kind='PAYLOAD_HIGH_BITS', calendar=name, pc=pc))
        counts['words'] += 1
        if role != 'S' or not lo_pc <= pc < hi_pc:
            continue
        counts['s_words'] += 1
        rv, wv = get(word, f, 'rslot_v'), get(word, f, 'wslot_v')
        rs, ws = get(word, f, 'rslot'), get(word, f, 'wslot')
        for bank in range(8):
            if rv >> bank & 1:
                owner = rs >> (bank * RB) & ((1 << RB) - 1)
                if owner == 0:
                    counts['s_group0_read'] += 1
                    if pc not in allow_r:
                        findings.append(dict(kind='S_GROUP0_READ', calendar=name, pc=pc, bank=bank))
            if wv >> bank & 1:
                owner = ws >> (bank * WB) & ((1 << WB) - 1)
                if owner == 0:
                    counts['s_group0_write'] += 1
                    if pc not in allow_w:
                        findings.append(dict(kind='S_GROUP0_WRITE', calendar=name, pc=pc, bank=bank))
                if owner == DQ_OWNER:
                    findings.append(dict(kind='S_DQ_FILL', calendar=name, pc=pc, bank=bank))
        if get(word, f, 'lg_local_read') or get(word, f, 'lg_local_write'):
            findings.append(dict(kind='S_LG_LOCAL', calendar=name, pc=pc))
    stray = sorted((allow_r | allow_w) - seen)
    if stray:
        findings.append(dict(kind='ALLOW_UNUSED_PC', calendar=name, pcs=stray[:16]))


def check_qctl(entry, findings, counts):
    nk, base = int(entry['nkeys']), int(entry.get('base', 0))
    nq = 0 if nk <= base else min(nk - base, NQ_MAX)
    counts['qctl'] += 1
    if entry['role'] == 'S' and nq != 0:
        findings.append(dict(kind='S_QCTL_NQ', qctl=entry['name'], nq=nq))


def run(manifest, src=CAL_SRC):
    f = field_layout(src)
    findings, counts = [], dict(words=0, s_words=0, s_group0_read=0, s_group0_write=0, qctl=0)
    for c in manifest.get('calendars', []):
        if c.get('role') not in ('S', 'N'):
            raise ValueError(f"calendar {c.get('name')}: role must be S or N")
        check_calendar(c, f, findings, counts)
    for q in manifest.get('qctl', []):
        if q.get('role') not in ('S', 'N'):
            raise ValueError(f"qctl {q.get('name')}: role must be S or N")
        check_qctl(q, findings, counts)
    if not manifest.get('calendars') and not manifest.get('qctl'):
        raise ValueError('empty manifest: nothing checked')
    return dict(schema='opentallas.hbm.b2o_cal_check_result.v1',
                verdict='FAIL' if findings else 'PASS', findings=findings, counts=counts,
                scope='finite compiled images only; producer/request agreement is the vh1 token run')


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__.split('\n')[0]); print('usage: b2o_cal_static_check.py manifest.json [out.json]'); return 2
    try:
        res = run(json.loads(Path(argv[1]).read_text()))
    except (ValueError, KeyError, OSError) as e:
        print(f'B2O_CAL_CHECK INPUT_ERROR {e}'); return 2
    text = json.dumps(res, indent=2) + '\n'
    if len(argv) == 3:
        Path(argv[2]).write_text(text)
    print(f"B2O_CAL_CHECK {res['verdict']} findings {len(res['findings'])} counts {json.dumps(res['counts'])}")
    return 0 if res['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
