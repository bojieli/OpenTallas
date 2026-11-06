#!/usr/bin/env python3
"""HBM-21 (SS39-TOK) item (1): B2o VM bank ABI, read from the bound top source (no hand table).

For every hub partition module named hbm_arch_q_hub__* in <src.sv>, every hfd_vms_bank_native_q0_faces instance
u_u_vmb_Q<k>[_mu1] gives one bank row:
  role      N for u_u_vmb_Q<k>, S for u_u_vmb_Q<k>_mu1;
  calendar  the u_calendar_Q_q* whose rslot/wslot bits feed the bank, and the bit offset [3k+:3];
  read owners  0..4 = rq0..rq4 (source net + producing leaf), 5 = packet (pq);
  write owners 0,1 = wq0,wq1, 2 = coll kq, 3 = cw xq, 4 = packet pq, 5 = ccw xq2, 6 = dma dq
  (ot_vms_bank_q0_faces_body #(.RG(5),.WG(2)) g_write_leaf order); a source written as a constant is 'tied'.
The owner order is checked against the body parameters found in the same source (RG/WG of the core's body instance).

  b2o_bank_abi.py <src.sv> <out.json>
"""
import json
import re
import sys
from pathlib import Path

READ = ['rq0', 'rq1', 'rq2', 'rq3', 'rq4', 'pq']
WRITE = ['wq0', 'wq1', 'kq', 'xq', 'pq', 'xq2', 'dq']
BANK = re.compile(r'hfd_vms_bank_native_q0_faces\s+(u_u_vmb_Q(\d+)(_mu1)?)\s*\((.*?)\n\s*\);', re.S)
PIN = re.compile(r'\.(\w+)\(([^()]*(?:\([^()]*\))?[^()]*)\)')


def leaf_of(net):
    net = net.strip()
    if re.fullmatch(r"\{?\s*\d+\s*\{\s*1'b0\s*\}\s*\}?|\d+'[bdh]0+", net):
        return 'tied0'
    m = re.match(r'(?:w_|xi_)(u_\w+?)_(?:vm_)?(?:rq|wq|kq|pq|xq2?|dq|bk_pq|bk_xq2?|wq_t\d+|rq\d|wq\d)(?:_q)?(?:\[|$)', net)
    return m.group(1) if m else net.split('[')[0]


def body_params(text):
    m = re.search(r'ot_vms_bank_q0_faces_body\s*#\(\s*\.RG\((\d+)\)\s*,\s*\.WG\((\d+)\)', text)
    if not m:
        raise ValueError('bank body RG/WG instance not found')
    return int(m.group(1)), int(m.group(2))


def build(text):
    rg, wg = body_params(text)
    if (rg, wg) != (5, 2):
        raise ValueError(f'owner order here is for RG5/WG2, source has RG{rg}/WG{wg}')
    hubs = {}
    for m in re.finditer(r'^module\s+(hbm_arch_q_hub__\w+)', text, re.M):
        end = text.find('\nendmodule', m.end())
        body = text[m.end():end]
        rows = []
        for b in BANK.finditer(body):
            pins = dict((p, n.strip()) for p, n in PIN.findall(b.group(4)))
            k, role = int(b.group(2)), ('S' if b.group(3) else 'N')
            cal = re.match(r'w_(u_calendar_Q_q\d)_rslot\[(\d+):(\d+)\]', pins.get('rslot', ''))
            wcal = re.match(r'w_(u_calendar_Q_q\d)_wslot\[(\d+):(\d+)\]', pins.get('wslot', ''))
            if not cal or not wcal or cal.group(1) != wcal.group(1) or int(cal.group(3)) != 3 * k:
                raise ValueError(f'{m.group(1)}.{b.group(1)}: unexpected calendar wiring {pins.get("rslot")}')
            rows.append(dict(
                bank=b.group(1), k=k, role=role, calendar=cal.group(1), slot_lsb=3 * k,
                read={i: dict(port=p, net=pins.get(p, ''), leaf=leaf_of(pins.get(p, ''))) for i, p in enumerate(READ)},
                write={i: dict(port=p, net=pins.get(p, ''), leaf=leaf_of(pins.get(p, ''))) for i, p in enumerate(WRITE)}))
        if rows:
            hubs[m.group(1)] = sorted(rows, key=lambda r: (r['role'], r['k']))
    if not hubs:
        raise ValueError('no hub banks found')
    roles = {}
    for h, rows in hubs.items():
        cals = {(r['role'], r['calendar']) for r in rows}
        for role in ('N', 'S'):
            c = {cal for ro, cal in cals if ro == role}
            if len(c) != 1:
                raise ValueError(f'{h}: role {role} banks use calendars {sorted(c)}')
            roles.setdefault(h, {})[role] = c.pop()
    return dict(schema='opentallas.hbm.b2o_bank_abi.v1', body=dict(RG=rg, WG=wg, RB=3, WB=3,
                read_owners=READ, write_owners=WRITE, dq_owner=WRITE.index('dq')),
                calendar_roles=roles, hubs=hubs)


def main(argv):
    if len(argv) != 3:
        print(__doc__); return 2
    res = build(Path(argv[1]).read_text(errors='replace'))
    Path(argv[2]).write_text(json.dumps(res, indent=1) + '\n')
    for h, rows in res['hubs'].items():
        s = [r for r in rows if r['role'] == 'S']
        print(f"B2O_BANK_ABI {h} banks {len(rows)} S {len(s)} roles {res['calendar_roles'][h]} "
              f"S_read {[s[0]['read'][i]['leaf'] for i in range(6)]} S_write {[s[0]['write'][i]['leaf'] for i in range(7)]}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
