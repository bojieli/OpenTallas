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
    ap.add_argument('--variant', default='r25g4m', choices=['r25gm', 'r25g4m'])
    a = ap.parse_args()
    # r25g4m: R25G4 (qualified 4 x 2 SM grid) = full network build; r25gm: R25G fmt3 retile = network probe only
    m = die.build(die.R25G4M) if a.variant == 'r25g4m' else die.build(die.R25GM, network_probe=True)
    g = m['mtp_generic']
    buses = {b[0]: b for b in m['buses']}
    ctrl = sv_ports(ROOT / 'rtl/hbm_accel/generic/hgi_mtp_native.sv', 'hgi_mtp_native')
    VIEWS = ROOT / 'physical/hbm_accel_die_views'
    vctrl_pc = json.loads((VIEWS / 'mtp_hgi/port_check.json').read_text())
    vam_pc = json.loads((VIEWS / 'argmax_hgi/port_check.json').read_text())
    vctrl = {k: (v['dir'], v['bits']) for k, v in vctrl_pc['ports'].items()}
    vam = {k: (v['dir'], v['bits']) for k, v in vam_pc['ports'].items()}
    mx1 = sv_ports(ROOT / 'physical/hbm_cp_mtp_native/rtl/hfd_cmdproc_s_mtp_native_mx1.sv', 'hfd_cmdproc_s_mtp_native_mx1')
    mx1_rec = json.loads((ROOT / 'physical/hbm_cp_mtp_native/collar_mx1/hfd_cmdproc_s_mtp_native_mx1/ports.json').read_text())['ports']
    checks, fails, obligations = [], [], []

    def chk(name, ok, detail):
        checks.append(dict(check=name, ok=bool(ok), detail=detail))
        if not ok:
            fails.append(name)

    chk('mtp_hgi view LEF == routed netlist', vctrl_pc['verdict'] == 'MATCH', vctrl_pc['lef_pin_bits'])
    chk('argmax_hgi view LEF == routed netlist', vam_pc['verdict'] == 'MATCH', vam_pc['lef_pin_bits'])
    chk('mtp_hgi view ports == hgi_mtp_native RTL ports', {k: v[1] for k, v in vctrl.items()} == {k: v[1] for k, v in ctrl.items()},
        dict(view=len(vctrl), rtl=len(ctrl)))
    real = {'hb_mtp': vctrl, 'hb_mtp_am': vam, 'hb_cmdproc_mx1': mx1}
    src = {'hb_mtp': 'view mtp_hgi', 'hb_mtp_am': 'view argmax_hgi', 'hb_cmdproc_mx1': 'MX1 RTL'}
    for bn in g['buses']:
        _, _, bits, eps = buses[bn]
        for inst, port in eps:
            if inst in real:
                if port not in real[inst]:
                    if inst == 'hb_mtp_am':
                        obligations.append(f'{inst}.{port} ({bits} b): record dispatch adapter in front of the bare '
                                           'ARGMAX view (683-b record -> cfg_rank 7 / cfg_imm_a 18 + in_v gating; '
                                           'ret {ready, done, fault}) (hgi-takeover)')
                    elif port.startswith(('t_hgi_', 'f_hgi_')):
                        obligations.append(f'{inst}.{port} ({bits} b): hgi dispatch ECO port on the CP south band RTL '
                                           '(hfd_cmdproc_s_mtp_native_mx1 has none yet; hgi-takeover pin plan only)')
                    else:
                        chk(f'{bn}:{inst}.{port}', False, f'port missing on {src[inst]}')
                    continue
                w = real[inst][port][1]
                chk(f'{bn}:{inst}.{port}', w == bits, dict(bus_bits=bits, port_bits=w, source=src[inst]))
    used_am = {p for bn in g['buses'] for i, p in buses[bn][3] if i == 'hb_mtp_am'}
    am_open = sorted(set(vam) - used_am - {'clk', 'rst_n'})
    for p in am_open:
        obligations.append(f'hb_mtp_am.{p} ({vam[p][1]} b): driven by the dispatch adapter (not a die bus)')
    for p in ('t_mtp', 'f_mtp', 'f_am'):
        rec = mx1_rec.get(p)
        rb = rec.get('bits') if isinstance(rec, dict) else (rec[1] if isinstance(rec, (list, tuple)) else None)
        chk(f'mx1 ports.json {p}', rb == mx1[p][1], dict(record=rb, rtl=mx1[p][1]))
    # mtp-lead 2026-10-10: MX1 face clock taps (design standard 2026-10-09): every tap is an MX1 RTL + record port, rides the
    # die clock net with MX1's ck, and has a clock-leaf offset row (resolved or PENDING) in the die clock plan
    mx1_inst = [i.name for i in m['insts'] if i.master == 'hfd_cmdproc_s_mtp_native_mx1']
    ck_nets = [b_ for b_ in m['buses'] if any(i in mx1_inst and pp == 'ck' for i, pp in b_[3])]
    offs = {(r['inst'], r['pin']) for r in m.get('clock_leaf_offsets', [])}
    for tp in ('cks', 'ckn', 'cke', 'ckw'):
        chk(f'mx1 face tap {tp}: RTL + record port', tp in mx1 and tp in mx1_rec, dict(rtl=tp in mx1, record=tp in mx1_rec))
        for i in mx1_inst:
            chk(f'mx1 face tap {i}.{tp} on the die ck net', any((i, tp) in b_[3] for b_ in ck_nets), [b_[0] for b_ in ck_nets])
            chk(f'mx1 face tap {i}.{tp} clock-leaf offset row', (i, tp) in offs, 'clock_leaf_offsets')
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
    hub = m['hub']
    chk('slot instance 1 = hgi_mtp_native view size', (hub['mtp'].master, hub['mtp'].w, hub['mtp'].h) ==
        ('hgi_mtp_native', *vctrl_pc['size_um']), (hub['mtp'].master, hub['mtp'].w, hub['mtp'].h))
    chk('slot instance 2 = ot_hgi_argmax18_m view size', (hub['mtp_am'].master, hub['mtp_am'].w, hub['mtp_am'].h) ==
        ('ot_hgi_argmax18_m', *vam_pc['size_um']), (hub['mtp_am'].master, hub['mtp_am'].w, hub['mtp_am'].h))
    W_, H_ = die.R25GM['spine_slots_low']['mtp']
    x0 = hub['mtp'].x
    chk('two instances inside the MD-7 slot, no overlap', hub['mtp_am'].x >= hub['mtp'].x + hub['mtp'].w - 1e-6 and
        hub['mtp_am'].x + hub['mtp_am'].w <= x0 + W_ + 1e-6 and max(hub['mtp'].h, hub['mtp_am'].h) <= H_ + 1e-6,
        dict(slot=[W_, H_], used_w=round(hub['mtp'].w + hub['mtp_am'].w, 3)))
    peer_pins = sorted({f'{inst}.{port}' for bn in g['buses'] for inst, port in buses[bn][3] if inst not in real})
    rec = dict(schema='opentallas.hgi_mtp_die_check.v1', verdict='PASS' if not fails else 'FAIL', variant=a.variant,
               build='full network build (R25G4, qualified 4 x 2 SM grid)' if a.variant == 'r25g4m' else 'network_probe (R25G fmt3 retile: full build unqualified)', default_on_now=g['default_on'],
               buses={bn: dict(bits=buses[bn][2], ends=buses[bn][3]) for bn in g['buses']},
               signal_bits=sum(buses[bn][2] for bn in g['buses']),
               r25g_hfd_mtp_bits=sum(x[2] for x in die.MTP_HUB_LINKS),
               slot_content=g['slot_content'], argmax_unbound_ports=am_open,
               unbound_mx1_endpoints=g['unbound'], unbound_owner=g['unbound_owner'],
               peer_pins_required_on_closed_views=peer_pins, rtl_port_obligations=obligations, checks=checks, failed=fails)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(rec['verdict'], len(checks), 'checks', fails, 'signal bits', rec['signal_bits'], 'vs r25m', rec['r25g_hfd_mtp_bits'])
    raise SystemExit(0 if not fails else 1)


if __name__ == '__main__':
    main()
