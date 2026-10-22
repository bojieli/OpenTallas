#!/usr/bin/env python3
"""QW-G5NOROOT 10-20: forwarded-clock roots and static straps in the Qwen landed-pairs judge (qwen_landed_pairs.py).

The g5 compute die (dv2f20g5 rG5) left NO_ROOT 8 + BUMP 3: the d2d link hop-0 stations clocked by the forwarded ROM-link
clock ckb_rom.pll_ck (n_pll_fwd, no clk_rx root), and the three TP8 rank strap bumps.  This excerpt reproduces those
rows; the judge must MOVE them (FWD_ROOT / FWD / RESET_XDOM / STATIC), never drop them:
  * ckb_rom -> hop-0 stations = FWD_ROOT (declared root fwd:ckb_rom), bump -> hop-0 = FWD (source-synchronous);
  * a die-root reset repeater -> hop-0 en = RESET_XDOM (unsynchronised), -> qfd_rst_rep on fwd:ckb_rom = RESET_SYNC;
  * ckb_core -> clk_rx stays FEED, ckb_rom rs -> qfd_rstsync stays RESET_SYNC (not forwarded roots);
  * strap bumps = STATIC; a non-strap bump into a die root stays BUMP (mutant: --static-net elsewhere -> BUMP 3).
    python3 tools/die_clock/test_landed_pairs_fwd.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLK = [('clk_rx/pll_d2d[0]', 'rstt_a/clk', 'qfd_rst_rep'), ('clk_rx/pll_d2d[0]', 'd2d_rom/ck', 'qfd_d2d_static'),
       ('clk_rx/pll_d2d[0]', 'rs_bump/ck', 'qfd_rstsync'), ('clk_rx/pll_d2d[0]', 'rly_ep_2/ck', 'qfd_landh_1_EW_65x30'),
       ('clk_rx/pll_coll[0]', 'rly_strap_0/ck[0]', 'qfd_rlyh0_1_SN_65x30'), ('clk_rx/pll_coll[0]', 'io_coll/clk', 'qfd_coll')]
BLK = {'ckb_rom': 'qfd_ckbump', 'ckb_core': 'qfd_ckbump', 'clk_rx': 'qfd_clkrx', 'rs_bump': 'qfd_rstsync',
       'bump_fwd_epoch': 'qfd_sigbump', 'bump_fwd_lrst': 'qfd_sigbump', 'bump_pkg_s0': 'qfd_sigbump', 'bump_odd': 'qfd_sigbump',
       'rly_ep_0': 'qfd_rlyh0_1_NS_65x30', 'rly_ep_1': 'qfd_rlyh_1_NW_65x30', 'rly_ep_2': 'qfd_landh_1_EW_65x30',
       'rly_lr_0': 'qfd_rlyr0_1_NS_65x30', 'rstt_a': 'qfd_rst_rep', 'rstt_b': 'qfd_rst_rep', 'rly_strap_0': 'qfd_rlyh0_1_SN_65x30',
       'd2d_rom': 'qfd_d2d_static', 'io_coll': 'qfd_coll'}
PAIRS = [('ckb_core', 'clk_rx', 'n_pll_core[0]'),                    # FEED
         ('ckb_rom', 'rs_bump', 'n_rst_fwd[0]'),                     # RESET_SYNC (package reset synchroniser)
         ('ckb_rom', 'rly_ep_0', 'n_pll_fwd[0]'), ('ckb_rom', 'rly_lr_0', 'n_pll_fwd[0]'),
         ('ckb_rom', 'rstt_b', 'n_pll_fwd[0]'),                      # FWD_ROOT x3 (rstt_b = the re-clocked synchroniser)
         ('bump_fwd_epoch', 'rly_ep_0', 'n_lnk_fwd_epoch[0]'), ('bump_fwd_lrst', 'rly_lr_0', 'n_lnk_fwd_lrst[0]'),  # FWD
         ('rly_ep_0', 'rly_ep_1', 'n_lnk_fwd_epoch__r1[0]'),         # FWD (station)
         ('rstt_a', 'rly_ep_0', 'n_rst_d2d__t20[0]'),                # RESET_XDOM (the g5 defect)
         ('rstt_a', 'rstt_b', 'n_rst_d2d__t19[0]'),                  # RESET_SYNC (synchroniser input)
         ('rstt_b', 'rly_ep_0', 'n_rst_d2d__t21[0]'),                # INTRA on fwd:ckb_rom
         ('bump_pkg_s0', 'rly_strap_0', 'n_sf_strap_bump_pkg_s0[0]'),  # STATIC
         ('bump_odd', 'io_coll', 'n_odd_in[0]')]                     # BUMP (undeclared off-die input)


def run(geom, extra=()):
    out = geom / 'lp.json'
    subprocess.run([sys.executable, '-I', str(HERE / 'qwen_landed_pairs.py'), '--geom', str(geom), '--lanes',
                    str(geom / 'lanes.json'), '--out', str(out), *extra], check=True, capture_output=True)
    return json.loads(out.read_text())


def main():
    with tempfile.TemporaryDirectory() as td:
        g = Path(td)
        (g / 'clknets.tsv').write_text(''.join(f'{r}\t{ld}\t{m}\t0\t0\n' for r, ld, m in CLK))
        (g / 'blocks.tsv').write_text(''.join(f'{i}\t{m}\t0\t0\t1\t1\n' for i, m in BLK.items()))
        (g / 'pairs.tsv').write_text(''.join(f'P\t{a}\t{b}\t{n}\td\n' for a, b, n in PAIRS))
        (g / 'lanes.json').write_text(json.dumps(dict(lanes=[dict(bid='lnk_fwd_epoch', stations=['rly_ep_0', 'rly_ep_1'],
                                                                   landing='rly_ep_2')])))
        d = run(g)
        p = d['summary']['pairs']
        want = dict(FEED=1, RESET_SYNC=2, FWD_ROOT=3, FWD=3, RESET_XDOM=1, INTRA=1, STATIC=1, BUMP=1)
        assert p == want, p
        assert d['summary']['no_root'] == 0 and d['summary']['bump'] == 1 and d['summary']['reset_xdom'] == 1, d['summary']
        assert d['summary']['fwd_roots'] == {'ckb_rom': {'n_pll_fwd[0]': 3}}, d['summary']['fwd_roots']
        assert sum(p.values()) == len(PAIRS)                                   # moved, never dropped
        assert any(o['cls'] == 'RESET_XDOM' and o['dst'] == 'rly_ep_0' for o in d['land_owed'])
        lag = d['lanes'][0]
        assert lag['src_root'] == 'fwd:ckb_rom' and lag['dst_root'] == 'clk_rx/pll_d2d[0]', lag
        # mutant 1: no static declaration matches -> the strap is an owed BUMP again
        p2 = run(g, ('--static-net', 'n_nothing_'))['summary']['pairs']
        assert p2.get('STATIC', 0) == 0 and p2['BUMP'] == 2, p2
        # mutant 2: without the forwarded root (ckb_rom rows removed) the hop-0 rows fall back to NO_ROOT (the g5 form)
        (g / 'pairs.tsv').write_text(''.join(f'P\t{a}\t{b}\t{n}\td\n' for a, b, n in PAIRS if a != 'ckb_rom' or b == 'rs_bump'))
        p3 = run(g)['summary']['pairs']
        assert p3.get('NO_ROOT', 0) >= 3 and 'FWD_ROOT' not in p3, p3
    print('TEST_LANDED_PAIRS_FWD PASS')


if __name__ == '__main__':
    main()
