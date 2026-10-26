#!/usr/bin/env python3
"""Expose only the production-shape TKM root cut for static_p/static_pd lockstep.

The tile chain is external to this hardened cut. Drive the same up0 at both cuts
and compare emitted entries/control and qualified writes at the actual CB21
root parameters. This is root equivalence, not whole-chain token qualification.
"""
import argparse
from pathlib import Path


def build(repo, out, mutant_sort=False):
    out.mkdir(parents=True, exist_ok=True)
    for mode in ('p', 'pd'):
        source = repo / f'rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_static_{mode}.sv'
        text = source.read_text()
        port = 'output reg busy,done,fault,output reg[31:0]stat_cycles'
        first = ' for(genvar t=0;t<NT;t=t+1)begin:g_tiles'
        after = ' reg[31:0]ids'
        if any(text.count(marker) != 1 for marker in (port, first, after)):
            raise ValueError(f'{source}: root cut source changed; review extraction')
        text = text.replace(port, port + ', input wire[343:0]probe_up, output wire[343:0]probe_down, output wire probe_dv,probe_clr,probe_conv')
        a, b = text.index(first), text.index(after)
        text = text[:a] + ''' assign up[0]=probe_up;
 assign probe_down=down[0];assign probe_dv=dv[0];assign probe_clr=t_clr;assign probe_conv=t_conv;
''' + text[b:]
        if mode == 'pd' and mutant_sort:
            marker = 'stable_key={e[EW-1:1],~tag};'
            if text.count(marker) != 1:
                raise ValueError('stable-sort mutant source changed')
            text = text.replace(marker, 'stable_key={e[EW-1:1],tag};')
        (out / f'root_{mode}.sv').write_text(text)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--mutant-sort', action='store_true')
    args = parser.parse_args()
    build(Path(__file__).resolve().parents[3], args.out, args.mutant_sort)
