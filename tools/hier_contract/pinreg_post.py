#!/usr/bin/env python3
"""Rank pinreg_audit.py results across dies and post each tile's violations to its owner's stream log.

Owner of a tile: the ownership-ledger row whose element is the contract cell or the view's Liberty cell
(owner "Claude:<stream>" -> <log dir>/<stream>.log when that log exists), else the first --route REGEX=LOG that
matches the cell, else the die lead's log (--lead DIE=LOG).  One line per (log, view); the die lead's log also gets the
die summary and the hop classes.  --dry-run prints instead of appending.

    pinreg_post.py --audit A.json [--audit B.json ...] --ledger L.json --log-dir DIR --lead DIE=LOG [--route RE=LOG]
                   --out RANKED.json --md RANKED.md [--dry-run]
"""
import argparse
import collections
import datetime
import json
import re
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--audit', action='append', required=True)
    ap.add_argument('--ledger')
    ap.add_argument('--log-dir', required=True)
    ap.add_argument('--lead', action='append', default=[])
    ap.add_argument('--route', action='append', default=[])
    ap.add_argument('--out', required=True)
    ap.add_argument('--md', required=True)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    logs = Path(a.log_dir)
    lead = dict(x.split('=', 1) for x in a.lead)
    routes = [x.rsplit('=', 1) for x in a.route]
    owners = {}
    if a.ledger:
        for r in json.loads(Path(a.ledger).read_text())['rows']:
            owners[r['element']] = r.get('owner') or ''
    now = datetime.datetime.now().strftime('%F %H:%M')
    posts, ranked, dies = collections.OrderedDict(), [], []
    for f in a.audit:
        d = json.loads(Path(f).read_text())
        die, tiles = d['die'], {t['cell']: t for t in d['tiles']}
        hp = d.get('hops') or {}
        dies.append(dict(die=die, contract_version=d['contract_version'], audit=f, status=d['status'], **d['counts'],
                         data_hops_over=hp.get('data_hops_over'), reset_nets_over=hp.get('reset_nets_over'),
                         hop_max_um=hp.get('max_um'), hop_source=hp.get('source')))
        dl = lead.get(die, 'el1013-pinreg-audit.log')
        for r in d['ranked_violations']:
            t = tiles[r['cell']]
            own, how = None, None
            for k in (r['cell'], t.get('lib_cell')):
                o = owners.get(k)
                if o and (logs / (o.split(':', 1)[-1].replace('/', '-') + '.log')).exists():
                    own, how = o.split(':', 1)[-1].replace('/', '-') + '.log', f'ledger {o}'
                    break
                if o and how is None:
                    how = f'ledger {o} (no stream log by that name)'
            if own is None:
                for rx, lg in routes:
                    if re.search(rx, r['cell']):
                        own, how = lg, (how + '; ' if how else '') + f'route {rx}'
                        break
            if own is None:
                own, how = dl, (how + '; ' if how else '') + 'die lead'
            line = (f"{r['cell']} x{r['instances']} [{' '.join(r['flags'])}] view {r['view']} ({r['binding']}; {r['setup_corner']}): "
                    f"clk->pin worst {r['worst_out_ps']} ps on {r['worst_out_bus']} ({r['out_over_bits']} bits > 166.7), "
                    f"pin->flop worst {r['worst_in_ps']} ps on {r['worst_in_bus']} ({r['in_over_bits']} bits > 166.7), "
                    f"comb bits {r['comb_bits']}, FF L {r['L_min_ps']} / H {r['H_max_ps']} -> L-H {r['min_delay_margin_ps']} ps")
            ranked.append(dict(r, die=die, owner_log=own, owner_basis=how))
            posts.setdefault(own, collections.OrderedDict()).setdefault(r['view'], [die, line])
            if own != dl:
                posts.setdefault(dl, collections.OrderedDict()).setdefault(r['view'], [die, line])
        s = (f"DIE {die} v{d['contract_version']}: cells {d['counts']['contract_cells']}, audited {d['counts']['audited']}, violating "
             f"{d['counts']['violating']} {d['counts']['by_flag']}, NOT AUDITABLE (no closed view) {d['counts']['not_auditable']} cells / "
             f"{d['counts']['instances_not_auditable']} instances; hops > 500 um: {hp.get('data_hops_over')} data + "
             f"{hp.get('reset_nets_over')} reset nets, max {hp.get('max_um')} um; worst classes: "
             + '; '.join(f"{k} x{v['hops']} {v['max_um']} um" for k, v in (hp.get('by_class') or [])[:8]))
        posts.setdefault(dl, collections.OrderedDict())[f'__die__{die}'] = [die, s]
    b = 833.333 * 0.2
    ranked.sort(key=lambda r: (-(r['comb_bits'] > 0), -max((r['worst_out_ps'] or 0) - b, (r['worst_in_ps'] or 0) - b, 0)))
    for i, r in enumerate(ranked):
        r['rank'] = i + 1
    Path(a.out).write_text(json.dumps(dict(schema='opentallas.pinreg_audit.ranked.v1', generated=now, dies=dies, ranked=ranked),
                                      indent=1) + '\n')
    L = ['# Die timing by construction: pin-register audit, ranked (PROVISIONAL)', '',
         'Rule (owner 2026-10-13): register at the pin -> wire <= 500 um -> register at the pin, IO 0.2 T of 833.333 ps '
         '(166.7 ps a side). Tool: `tools/hier_contract/pinreg_audit.py`. Every view audited here was exported before the '
         'export-SDC fix (main abc334b14), so each number may move by tens of ps: re-run once the views are re-exported.', '',
         '| die | contract | cells | audited | violating | not auditable (cells / inst) | hops > 500 um (data + reset) | max um |',
         '|---|---|---:|---:|---:|---|---|---:|']
    L += [f"| {d['die']} | v{d['contract_version']} | {d['contract_cells']} | {d['audited']} | {d['violating']} | {d['not_auditable']} / "
          f"{d['instances_not_auditable']} | {d['data_hops_over']} + {d['reset_nets_over']} | {d['hop_max_um']} |" for d in dies]
    L += ['', '| # | die | cell | inst | flags | clk->pin worst ps (bits over) | pin->flop worst ps (bits over) | L-H ps | corner | binding | owner log |',
          '|---|---|---|---:|---|---|---|---:|---|---|---|']
    L += [f"| {r['rank']} | {r['die']} | {r['cell']} | {r['instances']} | {' '.join(r['flags'])} | {r['worst_out_ps']} ({r['out_over_bits']}) | "
          f"{r['worst_in_ps']} ({r['in_over_bits']}) | {r['min_delay_margin_ps']} | {r['setup_corner']} | {r['binding']} | {r['owner_log']} |"
          for r in ranked]
    Path(a.md).write_text('\n'.join(L) + '\n')
    for lg, items in posts.items():
        txt = (f"{now} [pinreg-audit] DIE TIMING BY CONSTRUCTION audit (owner 10-13: register at the pin, wire <= 500 um, IO 0.2 T = "
               f"166.7 ps a side; a miss is a defect to fix, not to waive). PROVISIONAL: views pre export-SDC fix abc334b14, re-run "
               f"after re-export. Full tables: results/arch/pinreg_audit_1013/ (tool tools/hier_contract/pinreg_audit.py).\n"
               + ''.join(f"  - [{die}] {line}\n" for die, line in items.values()))
        if a.dry_run:
            print('==>', lg, len(items))
            print(txt[:1500])
        else:
            with open(logs / lg, 'a') as fh:
                fh.write(txt)
    print(f'{len(ranked)} ranked rows, {len(posts)} logs')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
