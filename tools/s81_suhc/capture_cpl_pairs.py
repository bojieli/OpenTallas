#!/usr/bin/env python3
"""Per-bit captured broadcast -> CLOSED CPL timing, with explicit evidence scope."""
import argparse, hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hier_contract'))
import pinreg_audit as A


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-view', required=True, type=Path)
    ap.add_argument('--source-cell', required=True)
    ap.add_argument('--diagnostic', action='store_true', help='source is placement-only; never qualify')
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    target = ROOT / 'physical/ref_tile/s81hc_ctpl_ref/views/ot_s81_hc_ctpl'
    geometry = ROOT / 'physical/s81_die_pins/v20_hc_capture/cpl_geometry.json'
    hashes = {str(geometry.relative_to(ROOT)): hashlib.sha256(geometry.read_bytes()).hexdigest()}
    def load(view, cell):
        ins = json.loads((view / 'insertion.json').read_text())
        metrics = {}
        for corner in ['tt', 'ff']:
            path = view / f'{cell}_{corner}.lib'
            lib = A.parse_lib(path)
            metrics[corner] = A.pin_metrics(lib, A.clock_refs(lib, ins, corner))
            hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return metrics, ins['tt']['boundary']['mean']
    src, sr = load(args.source_view, args.source_cell)
    dst, dr = load(target, 'ot_s81_hc_ctpl')
    rtl = (ROOT / 'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv').read_text()
    cpl = re.search(r'^module ot_s81_hc_ctpl\b.*?^endmodule', rtl, re.M | re.S).group()
    # Production S_RD=2: rd_k=fdq[1:0], rd_s=fdq[2], rowdecode[36:5],
    # post controls[40:37], payload[1127:104], fv only[2:0]. Other command
    # metadata belongs to return/NORM tiles, not any CPL consumer.
    for required in ['rd_v = fvq[S_RD-1:0]', 'pb_v = fvq[S_RD]',
                     'rd_k = fdq[O_RK +: 2]', 'rd_s = fdq[O_RS]',
                     'O_RK = 0, O_RS = 2, O_RC = 5']:
        assert required in cpl, 're-audit CPL unused bits after RTL changes'
    assert hashlib.sha256(cpl.encode()).hexdigest() == '117683828eb1917e3919459e0bede10a499a0d373cbb7579394243e79410b49f', 're-audit unused CPL fields after any module change'
    hashes['CPL module RTL'] = hashlib.sha256(cpl.encode()).hexdigest()
    unused = {f'fv[{bit}]' for bit in range(3, 7)} | {f'fdx[{bit}]' for bit in [3, 4, *range(41, 104)]}
    results = []
    hops = json.loads(geometry.read_text())['hops']
    assert len(hops) == 9080
    for hop in hops:
        port, bit, length = hop['port'], hop['bit'], hop['length_um']
        sp = f'{port}[{bit}]'
        dp = f'{port.removesuffix("_local")}[{bit}]'
        row = dict(hop, source_pin=sp, sink_pin=dp)
        try:
            launch = src['tt'][sp]['out']; capture = dst['tt'][dp]['inp']
            lmin = src['ff'][sp]['lmin']; hold = dst['ff'][dp]['hold']
            if capture is None and hold is None and dp in unused:
                row.update(status='UNUSED_RTL', basis='Production S_RD2 CPL reads fv[2:0] and fdx[2:0],[40:5],[1127:104] only; no sink timing arc in CLOSED ETM')
                results.append(row)
                continue
            if None in [launch, capture, lmin, hold]:
                raise ValueError('missing registered timing arc')
            setup = 833.333 - 60 - (150 if max(sr, dr) > 300 else 90) - launch - capture - .76 * length
            hmargin = lmin + .112 * length - hold - 100
            row.update(launch_ps=round(launch, 4), capture_ps=round(capture, 4),
                       setup_margin_ps=round(setup, 4), hold_margin_ps=round(hmargin, 4),
                       status='PASS' if setup >= 0 and hmargin >= 0 and length <= 500 else 'FAIL')
        except (KeyError, ValueError) as exc:
            row.update(status='MISSING', why=str(exc))
        results.append(row)
    counts = {status: sum(r['status'] == status for r in results) for status in ['PASS', 'FAIL', 'MISSING', 'UNUSED_RTL']}
    report = dict(schema='opentallas.s81.capture_cpl_pairs.v1',
                  qualification_status='UNQUALIFIED_PLACEMENT_ONLY' if args.diagnostic else 'ROUTED_PAIR_SCREEN_ONLY',
                  scope='CPL captures only. CTRa/b, clock/reset delivery and full native die composition remain separate gates.',
                  source_R_ps=sr, target_R_ps=dr, counts=counts, hashes=hashes, joins=results)
    for name in ['setup_margin_ps', 'hold_margin_ps']:
        rows = [r for r in results if name in r]
        report['worst_' + name] = min(rows, key=lambda r: r[name]) if rows else None
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'joins' and k != 'hashes'}, indent=2))
    return int(bool(counts['FAIL'] or counts['MISSING']))


if __name__ == '__main__':
    sys.exit(main())
