"""D-QC-CB-STRAPS: expose existing per-instance IDs at the parent (zero cycles).

Values are the exact representative defaults from the native bound CB modules;
the binder retains each replica's actual values at the parent. tile_id low bits
that are driven by internal tie cells remain those original internal connections.
COORD 2026-10-26 approved all nine CB types under the same IDs-only rule.
"""
import re


def apply(raw):
    report = {}
    for tn, typ in raw['partition_types'].items():
        if not re.fullmatch(r'cb[fnx]_q[01][01](?:_s2)?', tn):
            continue
        near = tn.startswith('cbn_')
        tile_default = 0 if tn.endswith('_s2') else (400 if near else 384)
        rows = []
        for d in typ.get('contents', []):
            m = re.fullmatch(r'u_(t|xstn)([0-3])([0-3])', d['inst'])
            if not m:
                continue
            kind, x, y = m.groups()
            if kind == 't':
                leaf, port, width, value = f'u_t_{x}_{y}', 'tile_id', 16, tile_default
            else:
                leaf, port, width = f'u_fab.u_x_{x}_{y}', 'sidx', 3
                value = int(y) if near else 7-int(y)
            d['parent_id_leaf'] = leaf
            d['parent_id_straps'] = {port: dict(width=width, value=value)}
            rows.append(dict(inst=d['inst'], leaf=leaf, port=port, width=width, value=value))
        if len(rows) != 8:
            raise ValueError(f'{tn}: expected exactly four tiles and four fabric stations, got {rows}')
        # A tile hard macro is a different interface, whose tile_id wires remain
        # entirely inside the parent wrapper. It must not inherit these soft-leaf
        # declarations: no new pins or constant permissions are added to the macro.
        report[tn] = rows
    if len(report) != 9:
        raise ValueError(f'expected nine CB types, found {list(report)}')
    return dict(types=report, declarations=sum(map(len, report.values())), cycles=0,
                fixed_primitive='cbf_q00 S_u_fab_not_*_A remains the same literal 1 in every replica; not an ID exemption')
