"""mtp-lead 2026-10-09: die-graph check of the generic-die MTP master (R25GM = R25G + mtp_master 'hgi_native').

Builds R25GM as a network probe (R25G's retiled SM grid has no qualified full build) and checks, without ties:
  * every MTP bus width equals the port width of BOTH ends' real RTL / port records: hgi_mtp_native ports (parsed from
    rtl/hbm_accel/generic/hgi_mtp_native.sv), MX1 t_mtp / f_mtp / f_am (collar_mx1 ports.json + RTL);
  * each contract field lies inside its group (no overlap, no gap) and matches the facade's port binding;
  * the slot holds the controller + the ARGMAX unit outline;
  * lists the MX1 endpoints that have no die producer yet (unbound) and the peer pins the die graph asks of blocks
    whose closed views do not have them (router f_mtp / t_mtp, coll f_mtp / t_mtp, su_red t_am_stream, VM f_am_o).
Usage: python3 tools/hgi_mtp_die_check.py --out results/rtl/mtp_hbmdie_20261009/die_check.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_accel_die_fp as die  # noqa: E402
from hbm_mtp_native_contract import generic_model  # noqa: E402


def sv_ports(path, module):
    s = Path(path).read_text()
    s = s[s.index(f'module {module}'):]
    s = s[:s.index(');')]
    out = {}
    for d, msb, names in re.findall(r'(input|output)\s+wire\s*(?:\[(\d+):0\])?\s*([\w\s,]+?)(?=,\s*(?:input|output)|\s*$)', s):
        for n in names.replace('\n', ' ').split(','):
            n = n.strip()
            if n:
                out[n] = (d, int(msb) + 1 if msb else 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    m = die.build(die.R25GM, network_probe=True)
    g = m['mtp_generic']
    buses = {b[0]: b for b in m['buses']}
    ctrl = sv_ports(ROOT / 'rtl/hbm_accel/generic/hgi_mtp_native.sv', 'hgi_mtp_native')
    mx1 = sv_ports(ROOT / 'physical/hbm_cp_mtp_native/rtl/hfd_cmdproc_s_mtp_native_mx1.sv', 'hfd_cmdproc_s_mtp_native_mx1')
    mx1_rec = json.loads((ROOT / 'physical/hbm_cp_mtp_native/collar_mx1/hfd_cmdproc_s_mtp_native_mx1/ports.json').read_text())['ports']
    checks, fails, obligations = [], [], []

    def chk(name, ok, detail):
        checks.append(dict(check=name, ok=bool(ok), detail=detail))
        if not ok:
            fails.append(name)

    real = {'hb_mtp': ctrl, 'hb_cmdproc_mx1': mx1}
    for bn in g['buses']:
        _, _, bits, eps = buses[bn]
        for inst, port in eps:
            if inst in real:
                if inst == 'hb_mtp' and port not in ctrl:
                    obligations.append(f'{inst}.{port} ({bits} b): ARGMAX unit wrapper in the slot (hgi-takeover)')
                    continue
                if port.startswith(('t_hgi_', 'f_hgi_')) and port not in real[inst]:
                    obligations.append(f'{inst}.{port} ({bits} b): hgi dispatch ECO port on the CP south band RTL '
                                       '(hfd_cmdproc_s_mtp_native_mx1 has none yet; hgi-takeover pin plan only)')
                    continue
                w = real[inst].get(port, (None, None))[1]
                chk(f'{bn}:{inst}.{port}', w == bits, dict(bus_bits=bits, rtl_bits=w))
    for p in ('t_mtp', 'f_mtp', 'f_am'):
        rec = mx1_rec.get(p)
        rb = rec.get('bits') if isinstance(rec, dict) else (rec[1] if isinstance(rec, (list, tuple)) else None)
        chk(f'mx1 ports.json {p}', rb == mx1[p][1], dict(record=rb, rtl=mx1[p][1]))
    gm = generic_model(ROOT)
    for name, grp in gm['groups'].items():
        lsb = 0
        for f in grp['fields']:
            chk(f'contract {name}.{f["port"]} contiguous', f['lsb'] == lsb, f)
            lsb += f['width']
        chk(f'contract {name} width = facade port', ctrl[name][1] == grp['bits'], dict(contract=grp['bits'], rtl=ctrl[name][1]))
    fac = (ROOT / 'physical/hbm_mtp/rtl/hfd_mtp_native_cp_stop.sv').read_text()
    for name, grp in gm['groups'].items():
        for f in grp['fields']:
            chk(f'facade binds {f["port"]}', f'.{f["port"]}({name}[{f["lsb"]} +: {f["width"]}])' in fac, f)
    slot = m['hub']['mtp']
    chk('slot master', slot.master == 'hgi_mtp_native', slot.master)
    slot_um2 = slot.w * slot.h
    argmax_um2 = 180 * 140             # ot_hgi_argmax18_m route outline (hgi_argmax18 cfg FW 180 / FH 140)
    ctrl_um2 = 11611.86 / 0.45         # historical hfd_mtp_x mapped cells at 45 % (cp_stop adds 18 pin flops)
    chk('slot fits controller + ARGMAX unit', ctrl_um2 + argmax_um2 <= slot_um2,
        dict(slot_um2=round(slot_um2), controller_at_45pct_um2=round(ctrl_um2), argmax_outline_um2=argmax_um2))
    peer_pins = sorted({f'{inst}.{port}' for bn in g['buses'] for inst, port in buses[bn][3] if inst not in real})
    rec = dict(schema='opentallas.hgi_mtp_die_check.v1', verdict='PASS' if not fails else 'FAIL', variant='r25gm (R25G + mtp_master hgi_native)',
               build='network_probe (R25G retiled SM grid: full build unqualified)', default_on_now=g['default_on'],
               buses={bn: dict(bits=buses[bn][2], ends=buses[bn][3]) for bn in g['buses']},
               signal_bits=sum(buses[bn][2] for bn in g['buses']),
               r25g_hfd_mtp_bits=sum(x[2] for x in die.MTP_HUB_LINKS),
               unbound_mx1_endpoints=g['unbound'], unbound_owner=g['unbound_owner'],
               peer_pins_required_on_closed_views=peer_pins, rtl_port_obligations=obligations, checks=checks, failed=fails)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(rec['verdict'], len(checks), 'checks', fails, 'signal bits', rec['signal_bits'], 'vs r25m', rec['r25g_hfd_mtp_bits'])
    raise SystemExit(0 if not fails else 1)


if __name__ == '__main__':
    main()
