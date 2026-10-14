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
                    f"R {r.get('reference_ps')} ps ({r.get('reference_src')}), boundary spread {r.get('boundary_spread_ps')} ps; "
                    f"o = clk->pin - R worst {r['worst_out_ps']} ps on {r['worst_out_bus']}, s = setup@pin + R worst "
                    f"{r['worst_in_ps']} ps on {r['worst_in_bus']}, C = o + s {r.get('pair_cost_ps')} ps -> reach against its own "
                    f"kind {r.get('reach_self_um')} um; comb bits {r['comb_bits']}, FF L {r['L_min_ps']} / H {r['H_max_ps']} -> "
                    f"L-H {r['min_delay_margin_ps']} ps. FIX: " + '; '.join(r.get('fix') or ['-']))
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
    ranked.sort(key=lambda r: (-(r['comb_bits'] > 0), -(r.get('pair_cost_ps') or 0)))
    for i, r in enumerate(ranked):
        r['rank'] = i + 1
    Path(a.out).write_text(json.dumps(dict(schema='opentallas.pinreg_audit.ranked.v1', generated=now, dies=dies, ranked=ranked),
                                      indent=1) + '\n')
    L = ['# Die timing by construction: pin-register audit, ranked (insertion-compensated clock entry)', '',
         'Rule (owner 2026-10-13): register at the pin -> wire <= 500 um -> register at the pin. Die statement: clock at each '
         'tile clock pin = phi - R (R = mean boundary-register insertion); hop A -> B: o_A + 0.76 L + s_B <= 833.3 - 60 - 90 = '
         '683.3 ps (TT); per tile C = o + s, reach = (683.3 - C) / 0.76 against its own kind. The sign-off SDC (IO 0.2 T outside) '
         'proves only o, s <= 516.7 ps each. Tool: `tools/hier_contract/pinreg_audit.py`; each die file states which views '
         'still predate the export-SDC fix.', '',
         '| die | contract | cells | audited | violating | not auditable (cells / inst) | hops > 500 um (data + reset) | max um |',
         '|---|---|---:|---:|---:|---|---|---:|']
    L += [f"| {d['die']} | v{d['contract_version']} | {d['contract_cells']} | {d['audited']} | {d['violating']} | {d['not_auditable']} / "
          f"{d['instances_not_auditable']} | {d['data_hops_over']} + {d['reset_nets_over']} | {d['hop_max_um']} |" for d in dies]
    L += ['', '| # | die | cell | inst | flags | R ps | spread | o ps (bus) | s ps (bus) | C | reach um | L-H ps | corner | binding | owner log | fix |',
          '|---|---|---|---:|---|---:|---:|---|---|---:|---:|---:|---|---|---|---|']
    L += [f"| {r['rank']} | {r['die']} | {r['cell']} | {r['instances']} | {' '.join(r['flags'])} | {r.get('reference_ps')} | "
          f"{r.get('boundary_spread_ps')} | {r['worst_out_ps']} ({r['worst_out_bus']}) | {r['worst_in_ps']} ({r['worst_in_bus']}) | "
          f"{r.get('pair_cost_ps')} | {r.get('reach_self_um')} | {r['min_delay_margin_ps']} | {r['setup_corner']} | {r['binding']} | "
          f"{r['owner_log']} | {'; '.join(r.get('fix') or [])} |" for r in ranked]
    Path(a.md).write_text('\n'.join(L) + '\n')
    for lg, items in posts.items():
        txt = (f"{now} [pinreg-audit] DIE TIMING BY CONSTRUCTION audit v2 (owner 10-13: register at the pin, wire <= 500 um; judged on "
               f"the pair equation o_A + 0.76 L + s_B <= 683.3 ps with insertion-compensated clock entry, NOT 166.7 ps a side: the "
               f"earlier out_over / in_over lists are withdrawn). Full tables: results/arch/pinreg_audit_1013/*_compensated.md "
               f"(tool tools/hier_contract/pinreg_audit.py).\n"
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
