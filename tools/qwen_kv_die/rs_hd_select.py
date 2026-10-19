#!/usr/bin/env python3
"""KVR-VIEWS 2026-10-19: which PV result-trunk header the KV die binds (OT_KV_RS_HD = auto (default) | r | f).

  r = qkd_pv_rs_hd_r: one header stage, RS_D 49 (rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv); CLOSED view, native FAIL
      259.9 -- the documented stand-in until f qualifies.
  f = qkd_pv_rs_hd_f rev f2 (HKV-PVRS2): every input registered at its pin + the half-local select stage, header 2 edges,
      RS_D 50 (qkd_pvw_die_t_f.sv = pv_trunk_gen --rs-hd f: header module + RS_D only).  rs_* beat b leaves the pair at
      out_age + RS_D + b, so every die consumer of rs_* (pvfin p0 / p1 sample ages, the token-pass static schedule) takes
      +RS_D_DELTA[f] = +1 edge.

auto selects f ONLY when the f2 view is CLOSED and qualified on the branch: a committed native_pin_audit PASS receipt
physical/ref_tile/qkd_pv_rs_hd_f/native_qkd_pv_rs_hd_f_f2-*_PASS.json whose view_sha256 equals the view files on disk
(the f1 view also lives there and is native FAIL; a view without that receipt never switches the die).  OT_KV_RS_HD=f
forces f and FAILS CLOSED without that receipt; OT_KV_RS_HD=r pins the stand-in.

    python3 tools/qwen_kv_die/rs_hd_select.py      # prints the selection record (JSON)
"""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SR = 'rtl/qwen_sys/split_20261014'
FILES = dict(r=f'{SR}/qkd_pvw_die_t.sv', f=f'{SR}/qkd_pvw_die_t_f.sv')
HEADER = dict(r='qkd_pv_rs_hd_r', f='qkd_pv_rs_hd_f')
RS_D = dict(r=49, f=50)
RS_D_DELTA = dict(r=0, f=1)          # edges every rs_* consumer adds against the r calendar
F_VIEW = 'physical/ref_tile/qkd_pv_rs_hd_f/views/qkd_pv_rs_hd_f'
F_RECEIPTS = 'physical/ref_tile/qkd_pv_rs_hd_f'
F_RECEIPT_GLOB = 'native_qkd_pv_rs_hd_f_f2-*_PASS.json'


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def f_qualified(root=ROOT):
    """(ok, why, receipt): the f2 view is on disk with a committed native PASS receipt matching its files"""
    root = Path(root)
    vd = root / F_VIEW
    if not (vd / 'qkd_pv_rs_hd_f.lef').exists():
        return False, f'no qkd_pv_rs_hd_f view at {F_VIEW}', None
    recs = sorted((root / F_RECEIPTS).glob(F_RECEIPT_GLOB))
    if not recs:
        return False, f'no f2 native PASS receipt ({F_RECEIPTS}/{F_RECEIPT_GLOB}); the view on disk is not qualified ' \
                      f'(f1 = native FAIL)', None
    why = []
    for rp in reversed(recs):
        r = json.loads(rp.read_text())
        shas = r.get('view_sha256') or {}
        if isinstance(shas, str):
            why.append(f'{rp.name}: view_sha256 not a dict')
            continue
        if r.get('verdict') != 'PASS' or r.get('view', F_VIEW) != F_VIEW:
            why.append(f'{rp.name}: verdict {r.get("verdict")} / view {r.get("view")}')
            continue
        bad = [f for f, h in shas.items() if not (vd / f).exists() or _sha(vd / f) != h]
        if not shas or bad:
            why.append(f'{rp.name}: view files differ from the audited view {bad[:4]}')
            continue
        return True, f'{rp.name} PASS on the view on disk', str(rp.relative_to(root))
    return False, '; '.join(why), None


def select(env=None, root=ROOT):
    env = os.environ if env is None else env
    mode = env.get('OT_KV_RS_HD', 'auto').strip() or 'auto'
    if mode not in ('auto', 'r', 'f'):
        raise ValueError(f'OT_KV_RS_HD={mode!r}: auto | r | f')
    ok, why, rec = (False, 'pinned by OT_KV_RS_HD=r', None) if mode == 'r' else f_qualified(root)
    if mode == 'f' and not ok:
        raise ValueError(f'OT_KV_RS_HD=f: the qkd_pv_rs_hd_f f2 view is not CLOSED + native PASS on the branch ({why}); '
                         'bind only CLOSED views')
    hd = 'f' if ok else 'r'
    if not (Path(root) / FILES[hd]).exists():
        raise ValueError(f'OT_KV_RS_HD: {FILES[hd]} missing (pv_trunk_gen --rs-hd {hd})')
    return dict(schema='opentallas.qwen_kv.rs_hd_select.v1', mode=mode, rs_hd=hd, header=HEADER[hd], file=FILES[hd],
                rs_d=RS_D[hd], rs_d_delta=RS_D_DELTA[hd], receipt=rec, why=why,
                status='QUALIFIED' if hd == 'f' else 'STAND_IN (qkd_pv_rs_hd_r CLOSED, native FAIL; f2 not qualified)')


if __name__ == '__main__':
    print(json.dumps(select(), indent=1))
    sys.exit(0)
