#!/usr/bin/env python3
"""KVR-VIEWS 2026-10-19: select the CLOSED qkd_d2d_static view the KV die binds to qkd_d2ds (kvsys_prep OT_KV_D2DS_VIEW).

The die compiles the KV D2D vector TXDP_K (kv_static.d2d_txdp_k, kvs14r: 0x03030418 = pair image with OT_KV_ATTN_LAND +1 on
port 0) and NTX (kv_static.d2d_ntx_k = 3).  TXDP is a hardened parameter (one-bit delay flops inside the view), so a view
binds only when its kit was hardened at exactly the die's TXDP and NTX.  The kit's own spec.json `params` is the record of
what the view was hardened at (r7v: {NTX 3, TXDP 50529304}).

    mode 0     -> frame (prints nothing, exit 0)
    mode auto  -> the kit view exists:    TXDP/NTX match -> print the view dir (exit 0); mismatch -> FAIL CLOSED (exit 3)
                  the kit view is absent: frame (prints nothing, exit 0) -- r7v is in review / not routed yet
    mode 1     -> as auto, but an absent view FAILS (exit 2)
A view counts as present only with the closure-record files (LEF + TT/FF libs + insertion.json).
KV-BIND4 10-19: the view directory is views/<spec.json top>: qkd_d2d_static (r7t/r7v) or the KV-SRAM-D2D successor
qkd_d2d_static_sfm (r7w_sfm / r7w_sfm2, +OUTPUT rx_zero17[16:0]); kv_die.d2ds_kit binds the matching RTL module with the
kit's hardened SAFE_RC / SRAMV / FEG.  GEN9 (kvs14r) default kit: qkd_d2d_static_r7w_sfm2 (CLOSED sfm2-1c6c02ed7).

    python3 tools/qwen_kv_die/d2ds_view_select.py --mode auto [--kit qkd_d2d_static_r7v] [--json OUT]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))

DEFAULT_KIT = 'qkd_d2d_static_r7v'
TOP = 'qkd_d2d_static'
TOPS = ('qkd_d2d_static', 'qkd_d2d_static_sfm')


def select(mode, kit=DEFAULT_KIT, root=ROOT, die_txdp=None, die_ntx=None):
    rec = dict(schema='opentallas.qwen_kv.d2ds_view_select.v1', mode=mode, kit=kit, bind=None)
    if mode in ('0', '', 'off'):
        rec.update(decision='FRAME', why='OT_KV_D2DS_VIEW=0')
        return 0, rec
    if die_txdp is None or die_ntx is None:
        import kv_die as K
        die_txdp, die_ntx = K.d2d_txdp_k(), K._ks_ntx()
    rec.update(die_txdp=f'0x{die_txdp:08x}', die_ntx=die_ntx)
    kd = Path(root) / 'physical/ref_tile' / kit
    sp = kd / 'spec.json'
    spec = json.loads(sp.read_text()) if sp.exists() else {}
    top = spec.get('top', TOP)
    if top not in TOPS:
        rec.update(decision='FAIL', why=f'{kit} top {top} is not a KV d2ds master {TOPS}')
        return 3, rec
    rec.update(top=top)
    vd = kd / 'views' / top
    need = [vd / f'{top}.lef', vd / f'{top}_tt.lib', vd / f'{top}_ff.lib', vd / 'insertion.json']
    missing = [str(p.relative_to(root)) for p in need if not p.exists()]
    if missing:
        rec.update(decision='FRAME', why=f'no CLOSED view of {kit} on the branch (missing {missing[0]}): frame kept')
        return (2 if mode == '1' else 0), rec
    params = spec.get('params', {})
    v_txdp, v_ntx = params.get('TXDP'), params.get('NTX')
    rec.update(view_params=params)
    rec.update(view=str(vd.relative_to(root)), view_txdp=None if v_txdp is None else f'0x{int(v_txdp):08x}', view_ntx=v_ntx)
    if v_txdp is None or int(v_txdp) != die_txdp or v_ntx is None or int(v_ntx) != die_ntx:
        rec.update(decision='FAIL', why=f'{kit} view hardened at TXDP {rec["view_txdp"]} NTX {v_ntx} != die TXDP '
                                         f'{rec["die_txdp"]} NTX {die_ntx}: re-harden, never bind a mismatched view')
        return 3, rec
    rec.update(decision='BIND', bind=rec['view'], why='closed view hardened at the die TXDP / NTX')
    return 0, rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='auto', choices=('0', '1', 'auto'))
    ap.add_argument('--kit', default=DEFAULT_KIT)
    ap.add_argument('--json')
    a = ap.parse_args(argv)
    rc, rec = select(a.mode, a.kit)
    if a.json:
        Path(a.json).write_text(json.dumps(rec, indent=1) + '\n')
    print(f"D2DS_VIEW {rec['decision']}: {rec['why']}", file=sys.stderr)
    if rec['bind']:
        print(rec['bind'])
    return rc


if __name__ == '__main__':
    sys.exit(main())
