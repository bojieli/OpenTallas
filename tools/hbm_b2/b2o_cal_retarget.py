#!/usr/bin/env python3
"""HBM-21 (SS39-TOK) item (3): re-target compiled d4g quadrant VM-calendar programmes onto the B2o hub calendars.

Why this is a remap and not a new compiler (facts, each checked on the vh1 bound top and on main):
  * targets: B2o keeps the d4g calendar target ids 96+QID (QID SW0 SE1 NW2 NE3, layer_images SW_TARGETS calendar_SW 96):
      SW 0x60 -> NW_hub.u_calendar_Q_q0 (S)   SE 0x61 -> NE_hub.u_calendar_Q_q0 (S)
      NW 0x62 -> NW_hub.u_calendar_Q_q1 (N)   NE 0x63 -> NE_hub.u_calendar_Q_q1 (N)          (b2o_tgt_table.py)
  * word: both use the universal hfd_hgi_vm_calendar layout (187-b payload, 0xc7a1 header, pc at [233:224]);
  * banks: every B2o bank is ot_vms_bank_q0_faces_body #(.RG(5),.WG(2)) with read owners
      0 rq0 (N: SU lg; S: FUSED pair u_fvp), 1 DMA back, 2 SM xload, 3 COLL, 4 IDX, 5 packet
    and write owners 0 wq0, 1 SM result writer, 2 coll kq, 3 cw, 4 packet, 5 ccw, 6 dma dq      (b2o_bank_abi.py).
  The d4g quadrant ABIs (results/arch/hbm_vm_static_1014/quadrant_abi.json) differ per quadrant, so owner indices are
  renumbered here:
      SW RG5/WG2: identity.
      SE RG4/WG2: read 0..3 identity, 4 (packet) -> 5.
      NW RG5/WG3: read 3 (quant) has NO B2o owner, 4 (COLL) -> 3, 5 (packet) -> 5; write 2 (quant) has NO owner,
                  3..7 -> 2..6.
      NE RG5/WG3: read 3 (HC engine) NO owner, 4 (COLL) -> 3, 5 -> 5; write 2 (HC engine) NO owner, 3..7 -> 2..6.
  A grant to an owner with no B2o equivalent is refused (UNMAPPED), never dropped silently.  All other fields
  (client_seq, response_*, bank_*, hub_ring_*, ring_tx_*, replay_*, lg_local_*) are copied bit-exact; on an S
  calendar any lg_local bit or group-0 grant is left for b2o_cal_static_check.py to judge (FUSED allow-list).

  b2o_cal_retarget.py <quadrant SW|SE|NW|NE> <d4g programme.json> <out programme.json>
Input/output: tools/hbm_vm_static_calendar.compile_schedule result (configuration_writes [{addr,data}], start ...).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b2o_cal_static_check as K  # noqa: E402  (field layout reader)

TARGET = {'SW': ('NW_hub', 'u_calendar_Q_q0', 'S', 0x60), 'SE': ('NE_hub', 'u_calendar_Q_q0', 'S', 0x61),
          'NW': ('NW_hub', 'u_calendar_Q_q1', 'N', 0x62), 'NE': ('NE_hub', 'u_calendar_Q_q1', 'N', 0x63)}
X = None  # no B2o owner
READ_MAP = {'SW': {i: i for i in range(6)},
            'SE': {0: 0, 1: 1, 2: 2, 3: 3, 4: 5},
            'NW': {0: 0, 1: 1, 2: 2, 3: X, 4: 3, 5: 5},
            'NE': {0: 0, 1: 1, 2: 2, 3: X, 4: 3, 5: 5}}
WRITE_MAP = {'SW': {i: i for i in range(7)},
             'SE': {i: i for i in range(7)},
             'NW': {0: 0, 1: 1, 2: X, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6},
             'NE': {0: 0, 1: 1, 2: X, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}}
B = 3


def remap_slots(valid, owners, table, kind, pc, errors):
    out = 0
    for bank in range(8):
        own = owners >> (bank * B) & 7
        if not valid >> bank & 1:
            if own:
                out |= own << (bank * B)   # owner bits without valid are inert; keep them bit-exact
            continue
        new = table.get(own, X)
        if new is X:
            errors.append(dict(kind='UNMAPPED_' + kind, pc=pc, bank=bank, d4g_owner=own))
            continue
        out |= new << (bank * B)
    return out


def retarget(quadrant, prog, f=None):
    if quadrant not in TARGET:
        raise ValueError(f'quadrant {quadrant}')
    f = f or K.field_layout()
    errors, writes = [], []
    for w in prog['configuration_writes']:
        pc, word = int(w['addr']), int(w['data'], 16)
        if word >> 240 != 0xc7a1 or (word >> 224) & 0x3ff != pc:
            raise ValueError(f'bad header at pc {pc}')
        new = word
        for kind, vf, of, table in (('READ', 'rslot_v', 'rslot', READ_MAP[quadrant]),
                                    ('WRITE', 'wslot_v', 'wslot', WRITE_MAP[quadrant])):
            lo, bits = f[of]
            v = K.get(word, f, vf)
            o = K.get(word, f, of)
            n = remap_slots(v, o, table, kind, pc, errors)
            new = (new & ~(((1 << bits) - 1) << lo)) | (n << lo)
        writes.append(dict(addr=pc, data=f'{new:064x}'))
    hub, cal, role, tgt = TARGET[quadrant]
    out = dict(prog)
    out.update(configuration_writes=writes,
               b2o_target=dict(instance=hub, leaf=cal, role=role, tgt=tgt, from_quadrant=quadrant,
                               read_map={str(k): v for k, v in READ_MAP[quadrant].items()},
                               write_map={str(k): v for k, v in WRITE_MAP[quadrant].items()}),
               b2o_retarget_errors=errors)
    return out


def main(argv):
    if len(argv) != 4:
        print(__doc__); return 2
    res = retarget(argv[1], json.loads(Path(argv[2]).read_text()))
    Path(argv[3]).write_text(json.dumps(res, indent=1) + '\n')
    t = res['b2o_target']
    print(f"B2O_CAL_RETARGET {argv[1]} -> {t['instance']}.{t['leaf']} tgt 0x{t['tgt']:02x} role {t['role']} "
          f"words {len(res['configuration_writes'])} unmapped {len(res['b2o_retarget_errors'])}")
    return 1 if res['b2o_retarget_errors'] else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
