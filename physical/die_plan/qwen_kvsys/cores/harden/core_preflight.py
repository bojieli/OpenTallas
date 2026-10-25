#!/usr/bin/env python3
"""Check a KV core's synthesized boundary using the same typed roles as signoff.py.

Exit nonzero on FAIL, missing inputs, or an incomplete check. Run on both the
raw Yosys netlist and the netlist exported from 1_synth.odb before floorplan.
"""
import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('kit', type=Path)
    ap.add_argument('netlist', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args(argv)
    sys.path.insert(0, str(a.kit.resolve()))
    import signoff
    result = signoff.run_face_guard(dict(kit=str(a.kit), synth=str(a.netlist),
                                        pins=str(a.kit / 'pins.json')))
    a.out.write_text(json.dumps(result, indent=1) + '\n')
    print('CORE_PREFLIGHT', result['verdict'], a.netlist,
          result.get('fail_counts', {}), result.get('reason', ''))
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
