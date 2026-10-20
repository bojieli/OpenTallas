"""Regenerate synthetic 624-bit template geometry coupons; never rf0027 closure."""
import argparse
import hashlib
import json
from pathlib import Path
from case_reach import lef
from relay_row_model import exact_contract_cost, Reservations


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('templates'); ap.add_argument('out')
    a = ap.parse_args()
    views, hashes, rows = {}, {}, []
    for flow in ('NS', 'WE'):
        p = Path(a.templates) / f'hbfd_rly_624_{flow}.lef'
        views.update(lef(p)); hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    for flow, (dx, dy) in (('WE', (300, 0)), ('NS', (0, 300))):
        m = f'hbfd_rly_624_{flow}'
        masters = {'launch': m, 'capture': m}
        pl = {'launch': dict(x=10, y=10, orient='R0'),
              'capture': dict(x=10+dx, y=10+dy, orient='R0')}
        widths = {(n, p): w for n in masters for p, w in [('i',624),('o',624),('ck',1),('rs',1)]}
        edges = [dict(source=['launch','o',0,624], sink=['capture','i',0,624], bits=624),
                 dict(source=['launch','o',0,1], sink=['capture','ck',0,1], bits=1),
                 dict(source=['launch','o',1,2], sink=['capture','rs',0,1], bits=1)]
        cost = exact_contract_cost(edges, pl, masters, views, widths)
        ok, _ = Reservations((1000,1000)).reserve(pl, views, masters)
        rows.append(dict(flow=flow, cost=cost, nonoverlap=ok,
                         note='Synthetic OUTPUT-bit to scalar clock/reset geometry only; no production topology claim'))
    Path(a.out).write_text(json.dumps(dict(status='SYNTHETIC COUPONS ONLY; not actual rf0027 or fullcandidate closure',
        actual_lef_sha256=hashes, endpoint_schema='lo,hi_exclusive', rows=rows,
        erratum='Prior1101.6um actual rf0027 attribution withdrawn; actualSYNTH land136 row396.576um. Low/high tuples corrected; all626bitpairs regenerated. Missing production forwardedclock/pin authority blocks integration.'), indent=2)+'\n')


if __name__ == '__main__':
    main()
