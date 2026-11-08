"""HBM plan event PMA-EYE-1108 (COORD R3 11-08 04:28, OWNER 12.24 optimistic academic model).

There is no native PLL/PMA clock-eye view.  This event writes the eye as an
ASSUMPTION (not a measurement) into the existing pad_clock contract rows:

* RX: data valid centred on the recovered-clock (pma_rck) edge, +-T/4.  The
  data launched for capture edge k changes T/4 after edge k-1 ... it is valid
  from k-T/4 to k+T/4, so relative to the launching edge k-1:
  set_input_delay -max = 3T/4, -min = T/4 (setup margin T/4, hold margin T/4).
* TX: pads timed against the forwarded clock (pma_tck) with setup = hold = 0
  at the pad: set_output_delay -max 0 -min 0.

Only pad_clock pins that already exist are touched; the data pad must exist
with the matching direction (io_lk_<L>_pma_rck <-> io_lk_<L>_pma_rx,
io_lk_<L>_pma_tck <-> io_lk_<L>_pma_tx).  A row that is already present must
match exactly (idempotent); anything else fails closed.  Pad positions, typed
sinks and the clock export itself belong to the PHY pad event, not this one.
"""
import argparse
import copy
import hashlib
import json
import re
import sys

EVENT = 'PMA-EYE-1108'
EVIDENCE = ('ASSUMPTION, not a measurement: COORD R3 2026-11-08 04:28 / OWNER 12.24 optimistic academic '
            'model, no native PLL/PMA clock-eye view. {what}. Plan event ' + EVENT + '.')
RX_WHAT = 'RX data valid centred on the pma_rck edge +-T/4 (T={T:g} ps): input delay max 3T/4, min T/4'
TX_WHAT = 'TX data timed at the pad against the forwarded pma_tck with setup = hold = 0: output delay max 0, min 0'
PAD_RE = re.compile(r'^(io_lk_[A-Za-z0-9]+)_pma_(rck|tck)$')


def rows_for(pin):
    T = float(pin['period_ps'])
    if pin['dir'] == 'in':
        return 'data_inputs', dict(max_ps=round(0.75 * T, 4), min_ps=round(0.25 * T, 4),
                                   evidence=EVIDENCE.format(what=RX_WHAT.format(T=T)))
    return 'data_outputs', dict(max_ps=0.0, min_ps=0.0, evidence=EVIDENCE.format(what=TX_WHAT))


def apply(plan):
    """Return (new_plan, changes).  plan is the raw die_plan dict."""
    out = copy.deepcopy(plan)
    changes = []
    for tn, t in sorted(out.get('partition_types', {}).items()):
        pc = (t.get('clock') or {}).get('pad_clock')
        if not pc:
            continue
        pads = {p['name']: p for p in t.get('pads', [])}
        for pin in pc['pins']:
            m = PAD_RE.match(pin['name'])
            if not m:
                continue
            want_dir = 'in' if m.group(2) == 'rck' else 'out'
            if pin['dir'] != want_dir:
                raise ValueError(f"{tn}.{pin['name']}: pad clock direction {pin['dir']} != {want_dir}")
            data = m.group(1) + ('_pma_rx' if want_dir == 'in' else '_pma_tx')
            dp = pads.get(data)
            if dp is None or dp.get('clock') is True or dp['dir'] != want_dir:
                raise ValueError(f'{tn}.{pin["name"]}: matching data pad {data} ({want_dir}) missing')
            key, row = rows_for(pin)
            row = dict(port=data, **row)
            have = [r for r in pin.get(key, []) if r.get('port') == data]
            if have:
                if have != [row]:
                    raise ValueError(f'{tn}.{pin["name"]}: existing {key} row for {data} differs from {EVENT}')
                continue
            pin.setdefault(key, []).append(row)
            changes.append(dict(type=tn, pad_clock=pin['name'], key=key, row=row))
    return out, changes


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('plan'); ap.add_argument('--out', required=True); ap.add_argument('--receipt', required=True)
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    new, changes = apply(plan)
    json.dump(new, open(a.out, 'w'), indent=1); open(a.out, 'a').write('\n')
    json.dump(dict(event=EVENT, plan_in=a.plan, sha_in=sha(plan), sha_out=sha(new), changes=changes,
                   note='assumption, not a measurement; types without PMA pad_clock pins unchanged'),
              open(a.receipt, 'w'), indent=1)
    print(f'{EVENT}: {len(changes)} rows')
    return 0


if __name__ == '__main__':
    sys.exit(main())
