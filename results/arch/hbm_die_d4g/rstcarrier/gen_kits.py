#!/usr/bin/env python3
"""L2H-RRL 10-19: ref_tile specs for the compact HBM reset carrier tiles (rtl/hbm_accel/die_glue/hbfd_rrl_c.sv).

    python3 gen_kits.py [--outline W H] [--suffix S] TOP...        write tools/ref_tile/specs_hbfd_rrlc/<kit>.json
    python3 gen_kits.py --from-layer layer.json.gz [--outline W H]    every hbfd_rrl_c* master a forest layer instantiates

Outline: the ref_tile flow keeps a fixed 2.16 um core margin (tools/ref_tile CORE_MARGIN, ref_route.sh --core-area) and a
leaf needs M5 PG stripe spread >= 0.52 of W (child_lint), so the planning body 8.64 x 2.16 um is the CORE of the smallest
legal hard view 12.96 x 6.48 um (aspect 2:1, 8 rows, M5 PG at 2.7 um pitch = 4 stripes / net spread 0.625).  Fallback
17.28 x 6.48 (core 12.96 x 2.16) for a pin- or density-limited result.  Pins as the planning LEF (gen_lef.py): clk and
rst_n on N, rst_n_in on S.  Every kit runs the same bench (all of csync / chop / cpad1..255) and the counter-early mutant
with the committed witness fail_witness_mut_counter_early.log."""
import argparse, gzip, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RC = 'results/arch/hbm_die_d4g/rstcarrier'
OUT = ROOT / 'tools/ref_tile/specs_hbfd_rrlc'


def age(top):
    if top == 'hbfd_rrl_csync':
        return 'sync (2 sync flops + 1 relay flop, release age 3)'
    if top == 'hbfd_rrl_chop':
        return 'one registered carrier stage (age 1)'
    n = int(re.fullmatch(r'hbfd_rrl_cpad(\d+)', top).group(1))
    return (f'face landing, release age {n}: ' + (f'{n} flops' if n <= 2 else
            f'2 landing flops + {(n - 2 - 1).bit_length() if n > 3 else 1}-bit count of {n - 2} edges + sticky output flop'))


def spec(top, w, h, suffix, branch, tag):
    name = top + suffix
    return dict(
        name=name, top=top, kind='tile',
        sources=['rtl/hbm_accel/die_glue/hbfd_rrl_c.sv', 'rtl/lib/ot_rst_relay.sv'],
        clock_port='clk', reset_ports=['rst_n_in'],
        outline=dict(w=w, h=h, exact=True),
        pins=dict(N=['clk', 'rst_n'], S=['rst_n_in'], W=[], E=[]),
        recipe=2, layer_cap='M5', io_flop_at_pins=dict(cols=4, allow_none=True),
        route=dict(pd=0.5, threads=4, peak_ram_gb=6, hold_margin_ns=0.03, io_hold_margin_ns=0.03, m5_pg_pitch=2.7,
                   macro_halo_um=5.4),
        structural_change=(f'L2H-RRL 10-19 (H.RST): hard view of the compact HBM reset carrier tile {top} ({age(top)}); '
                           'asynchronous assertion of every flop, synchronous release on the tile clk; no flop delay '
                           'line >= 3 (counted padding); outline = planning body 8.64 x 2.16 core + the 2.16 flow margin.'),
        job=dict(owner='Claude:LEAD2-HBM/L2H-RRL', branch=branch, tag=tag,
                 purpose=f'HBM d4g dedicated reset carrier tile {top}: {age(top)}',
                 extra_paths=['tools/hbm_die_v16', RC],
                 benches=[
                     dict(name='reset_carrier_exact', cmd='python3 tools/hbm_die_v16/reset_carrier_bench.py',
                          expect='pass', pass_regex='RESET_CARRIER PASS checks=', min_count_regex='checks=([0-9]+)',
                          threads=1, peak_ram_gb=2),
                     dict(name='reset_carrier_mutant', cmd='python3 tools/hbm_die_v16/reset_carrier_bench.py --mutant',
                          expect='fail', fail_regex='RELEASE age pad', fail_witness=f'{RC}/fail_witness_mut_counter_early.log',
                          threads=1, peak_ram_gb=2)]),
        params={}, macros=[], children=[], inter=[], inhold=True, outhold=True, keep_pin_regs=True,
        pin_reg_split=True, hold_pad=dict(cell='HB2xp67_ASAP7_75t_R'),
        pin_regs=dict(enable=False, reason=(
            'Reset-only tile (as the closed hbfd_rrl_sync/hop): rst_n_in is the asynchronous clear of every flop and '
            'rst_n is flop-driven; the tile IS the 2-stage registered face landing. A flow pin register would add a '
            'release edge the die schedule does not price and delay assertion.')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tops', nargs='*')
    ap.add_argument('--from-layer', type=Path)
    ap.add_argument('--outline', nargs=2, type=float, default=(12.96, 6.48))
    ap.add_argument('--suffix', default='')
    ap.add_argument('--branch', default='claude/hbfd-rrlc-kits-1019')
    ap.add_argument('--tag', default='r1')
    a = ap.parse_args()
    tops = list(a.tops)
    if a.from_layer:
        raw = a.from_layer.read_bytes()
        txt = (gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw).decode()
        tops += sorted(set(re.findall(r'"(hbfd_rrl_c(?:sync|hop|pad\d+))"', txt)))
    OUT.mkdir(parents=True, exist_ok=True)
    for t in dict.fromkeys(tops):
        s = spec(t, *a.outline, a.suffix, a.branch, a.tag)
        (OUT / f"{s['name']}.json").write_text(json.dumps(s, indent=1) + '\n')
        print(s['name'], s['outline'])


if __name__ == '__main__':
    main()
