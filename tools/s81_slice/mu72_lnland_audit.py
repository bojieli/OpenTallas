#!/usr/bin/env python3
"""STW-S81-LAND 10-21: structural landing audit of the four MU72 end-parent tops (L0/L1 lane regions).

Elaborates each top with yosys 0.68 (children = blackboxes from their real sources via read_verilog -lib, so ports and
widths are the real ones) and checks, from the netlist JSON:
  1. every lane u_ln<i> has its clock pin on a top input ck_N<i> (its own region, not ck_K / ck_S);
  2. every lane pin except ck / rs / chb / rx / tx connects ONLY to the N side of exactly one ot_s81_mu72_lnland cell
     whose ck_n is the lane's clock net and whose ck_k is u_lep's clk net (ck_K) -- no lane <-> lep net without landing;
  3. every u_lep lane-facing pin (lo*/li*/rxv*/l*_f/l*_st) connects only to the K side of a lnland cell;
  4. lane CORE_CRED == lep CRED == lep DR == 12 (matched credit depths after the +6 edge round trip); u_lep RX_SRAM /
     IN_PIPE / NATIVE32 == 1 (the lepmu kit params: default-param leps fail the native 32 census);
  5. lane rs pin driven from an N-region reset forest (u_lpr_N<i>), not a K-region pad.
  6. regional-lep successor top (u_lep = ot_s81sl_lep_mu_ab_regional_r4l): lanes 0/1 land on u_lep.clk_a (top port ck_KA),
     lanes 2/3 on u_lep.clk_b (ck_KB); clk / clk_a / clk_b on three distinct top ports; rst_n_a / rst_n_b from the
     u_lpr_KA / u_lpr_KB forests (mutant lane2_on_KA: lane-2 landing clocked by the pair-A clock must FAIL).
Usage (cwd = repo root): mu72_lnland_audit.py OUTDIR [--mutants]   ->  'MU72_LNLAND_AUDIT PASS' or FAIL lines.
--mutants additionally builds 3 mutated copies of each top (lane 0 lo_v wired straight to the lep; lane 1 clock on
ck_K; lane 0 CORE_CRED 8) and requires the audit to FAIL each one."""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path.cwd()
YOSYS = str(Path.home() / '.local/opentallas-tools/yosys-0.68/bin/yosys')
MU = 'rtl/dsrom_sys/s81_dv/slice/mu72'
TOPS = {'ot_s81sl_slice_lepe_mu_72': 2, 'ot_s81sl_slice_lepe_nh_mu_72': 2, 'ot_s81sl_slice_lepw_mu_72': 2,
        'ot_s81sl_slice_lepw_mab_mu_72': 4, 'ot_s81sl_slice_lepw_mab_r4l_mu_72': 4}
LIB = ['rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv',
       'rtl/dsrom_sys/s81_dv/slice/landed/c1x_k8_cap5r/ot_s81sl_slice_c1x_k8_cap5r_lp.sv',
       'rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv', 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_lep_mu_ab_regional.sv',
       'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_lep_mu_ab_regional_r3r.sv',
       'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_lep_mu_ab_regional_r4l.sv', f'{MU}/ot_s81_mu72_land.sv', f'{MU}/ot_s81_mu72_lnland.sv'] + \
      sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'rtl/common/landed_parent').glob('*.sv'))
LANE_FREE = {'ck', 'rs', 'chb', 'rx', 'tx'}


def elaborate(src: Path, top: str, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    ys = [f'read_verilog -sv -lib {ROOT / p}' for p in LIB]
    ys += [f'read_verilog -sv {src}', f'hierarchy -check -top {top}', 'proc', 'opt_clean',
           f'write_json {out / "net.json"}']
    (out / 'a.ys').write_text('\n'.join(ys) + '\n')
    r = subprocess.run([YOSYS, '-q', '-s', str(out / 'a.ys')], capture_output=True, text=True)
    (out / 'yosys.log').write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        return None
    return json.loads((out / 'net.json').read_text())['modules'][top]


def audit(mod, nl):
    errs = []
    cells = mod['cells']; ports = mod['ports']
    portbit = {}
    for pn, pd in ports.items():
        for i, b in enumerate(pd['bits']):
            portbit[b] = pn
    users = {}
    for cn, c in cells.items():
        for pn, bits in c['connections'].items():
            for b in bits:
                if isinstance(b, int):
                    users.setdefault(b, []).append((cn, pn))
    def net(cn, pn):
        return tuple(cells[cn]['connections'][pn])
    lep = cells.get('u_lep')
    if lep is None:
        return ['no u_lep']
    lep_ck = net('u_lep', 'clk')
    regional = 'clk_a' in lep['connections']
    pair_ck = {}
    if regional:
        for i, (pn, rp, top_ck) in enumerate([('clk_a', 'rst_n_a', 'ck_KA'), ('clk_b', 'rst_n_b', 'ck_KB')]):
            c = net('u_lep', pn)
            if len(c) != 1 or portbit.get(c[0]) != top_ck:
                errs.append(f'u_lep.{pn} on {portbit.get(c[0], c)} not {top_ck}')
            r = net('u_lep', rp)
            if not any(u[0] == f'u_lpr_K{top_ck[-1]}' for u in users.get(r[0], []) if u[0] != 'u_lep'):
                errs.append(f'u_lep.{rp} not from u_lpr_K{top_ck[-1]}')
            pair_ck[2 * i] = pair_ck[2 * i + 1] = c
        if len({lep_ck, pair_ck[0], pair_ck[2]}) != 3:
            errs.append('u_lep clk / clk_a / clk_b not three distinct roots')
    lnl = {cn: c for cn, c in cells.items() if c['type'].lstrip('\\').startswith('ot_s81_mu72_lnland')
           or 'ot_s81_mu72_lnland' in c['type']}
    lep_par = {k: int(v, 2) if set(str(v)) <= {'0', '1'} else v for k, v in lep.get('parameters', {}).items()}
    if lep_par.get('CRED') != 12 or lep_par.get('DR') != 12:
        errs.append(f'u_lep CRED/DR {lep_par.get("CRED")}/{lep_par.get("DR")} != 12/12')
    for k in ('RX_SRAM', 'IN_PIPE', 'NATIVE32'):            # = every lepmu kit spec (native32 kept copies, census PASS)
        if lep_par.get(k) != 1:
            errs.append(f'u_lep {k} {lep_par.get(k)} != 1 (lepmu kit params)')
    for i in range(nl):
        ln = f'u_ln{i}'
        if ln not in cells:
            errs.append(f'{ln} missing'); continue
        c = cells[ln]
        par = {k: int(v, 2) if set(str(v)) <= {'0', '1'} else v for k, v in c.get('parameters', {}).items()}
        if par.get('CORE_CRED') != 12:
            errs.append(f'{ln} CORE_CRED {par.get("CORE_CRED")} != 12')
        ck = net(ln, 'ck')
        if len(ck) != 1 or portbit.get(ck[0]) != f'ck_N{i}':
            errs.append(f'{ln}.ck on {portbit.get(ck[0], ck)} not ck_N{i}')
        if ck == lep_ck:
            errs.append(f'{ln}.ck == u_lep.clk')
        rs = net(ln, 'rs')
        drv = [u for u in users.get(rs[0], []) if u[0] != ln]
        if not any(u[0] == f'u_lpr_N{i}' for u in drv):
            errs.append(f'{ln}.rs not from u_lpr_N{i} ({drv[:3]})')
        mates = set()
        for pn, bits in c['connections'].items():
            if pn in LANE_FREE:
                continue
            for b in bits:
                if not isinstance(b, int):
                    errs.append(f'{ln}.{pn} constant bit'); break
                others = [u for u in users.get(b, []) if u[0] != ln]
                if b in portbit:
                    errs.append(f'{ln}.{pn} on top port {portbit[b]}'); break
                bad = [u for u in others if u[0] not in lnl or not u[1].startswith('n_')]
                if bad or not others:
                    errs.append(f'{ln}.{pn} unlanded -> {bad[:2] or "no sink"}'); break
                mates.update(u[0] for u in others)
        if len(mates) != 1:
            errs.append(f'{ln} landed by {sorted(mates)} (need exactly one lnland)')
            continue
        m = mates.pop()
        if net(m, 'ck_n') != ck:
            errs.append(f'{m}.ck_n != {ln}.ck')
        want = pair_ck[i] if regional else lep_ck
        if net(m, 'ck_k') != want:
            errs.append(f'{m}.ck_k != u_lep.{("clk_a", "clk_a", "clk_b", "clk_b")[i] if regional else "clk"}')
    lane_pins = re.compile(r'^(lo\d_|li\d_|rxv|l\d_f|l\d_st)')
    for pn, bits in lep['connections'].items():
        if not lane_pins.match(pn):
            continue
        for b in bits:
            if not isinstance(b, int):
                continue                                  # tied l*_st on a host-less top
            others = [u for u in users.get(b, []) if u[0] != 'u_lep']
            bad = [u for u in others if u[0] not in lnl or not u[1].startswith('k_')]
            if bad:
                errs.append(f'u_lep.{pn} unlanded -> {bad[:2]}'); break
    return errs


def mutate(text, k):
    if k == 'lo_v_direct':
        t, n = re.subn(r'(u_ln0 \([^;]*?)\.lo_v\(n0lv\)', r'\1.lo_v(l0v)', text, 1)
    elif k == 'lane1_ck_K':
        t, n = re.subn(r'(u_ln1 \()\.ck\(ck_N1\)', r'\1.ck(ck_K)', text, 1)
    elif k == 'lane0_cred8':
        t, n = re.subn(r'#\(\.CORE_CRED\(12\)\) u_ln0', '#(.CORE_CRED(8)) u_ln0', text, 1)
    elif k == 'lane2_on_KA':
        t, n = re.subn(r'u_lnl2 \(\.ck_k\(ck_KB\)', 'u_lnl2 (.ck_k(ck_KA)', text, 1)
    assert n == 1, k
    return t


def main():
    out = Path(sys.argv[1]).resolve(); muts = '--mutants' in sys.argv
    rc = 0; res = {}
    for top, nl in TOPS.items():
        src = ROOT / MU / f'{top}.sv'
        mod = elaborate(src, top, out / top)
        if mod is None:
            print(f'FAIL {top}: elaboration (see {out / top / "yosys.log"})'); rc = 1; continue
        e = audit(mod, nl); res[top] = e
        print(('PASS ' if not e else 'FAIL ') + top + ('' if not e else ': ' + '; '.join(e[:6])))
        rc |= bool(e)
        if muts:
            for k in ('lo_v_direct', 'lane1_ck_K', 'lane0_cred8') + (('lane2_on_KA',) if 'r4l' in top else ()):
                ms = out / f'{top}.{k}.sv'; ms.write_text(mutate(src.read_text(), k))
                mm = elaborate(ms, top, out / f'{top}.{k}')
                me = ['elab'] if mm is None else audit(mm, nl)
                caught = bool(me)
                print(f'MUTANT {top} {k}: {"CAUGHT" if caught else "NOT CAUGHT"} ({"; ".join(me[:2])})')
                res[f'{top}.{k}'] = me
                rc |= (not caught)
    (out / 'audit.json').write_text(json.dumps(res, indent=1) + '\n')
    print('MU72_LNLAND_AUDIT ' + ('PASS' if rc == 0 else 'FAIL'))
    sys.exit(rc)


if __name__ == '__main__':
    main()
