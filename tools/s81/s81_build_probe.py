#!/usr/bin/env python3
"""Build-only probe of an S81 recipe (mtp-draftdie 2026-10-09): apply the options, build + finalize_r8, and print
one JSON line: fits / error (with the failing assertion), instance counts of the MTP masters, wall time.  No files
written.  Use it to bisect a recipe that fails in the generator (e.g. a _hop_fix relay that finds no spot).

    python3 tools/s81/s81_build_probe.py <recipe name> [extra generator options ...]
"""
import argparse, json, sys, time, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_dies_recipe as R  # noqa: E402
F = R.F


def main():
    name, extra = sys.argv[1], sys.argv[2:]
    opts = (R._layer1_opts() + ['--die', 'layer1'] if name == 'layer1' else R.recipes()[name]['opts']) + extra
    t0 = time.time()
    out = dict(recipe=name, extra=extra)
    try:
        m = R.build(opts)
        ub = F.unbound_functional_pins(m)
        masters = {}
        for it in m['insts']:
            if it.master in ('dsfd_wfc', 'dsfd_mtp_seq', 'dsfd_p2', 'dsfd_host'):
                masters[it.master] = masters.get(it.master, 0) + 1
        out.update(fits=True, insts=len(m['insts']), masters=masters, unbound=len(ub),
                   legality=F.legality(m), variant={k: m['variant'].get(k) for k in ('wfc_hard', 'mtp_seq', 'mtp_links', 'draft')})
    except Exception as e:  # noqa: BLE001
        out.update(fits=False, error=f'{type(e).__name__}: {str(e)[:600]}', where=traceback.format_exc().splitlines()[-4:-1])
    out['seconds'] = round(time.time() - t0, 1)
    print(json.dumps(out, default=str), flush=True)


if __name__ == '__main__':
    main()
