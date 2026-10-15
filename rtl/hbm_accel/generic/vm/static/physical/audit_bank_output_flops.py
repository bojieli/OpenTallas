#!/usr/bin/env python3
"""Check physical bank response payloads retain distinct boundary state after synthesis."""
import argparse
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('netlist', type=Path)
parser.add_argument('--read-groups', required=True, type=int)
args = parser.parse_args()
text = args.netlist.read_text()
cells = re.findall(r'^\s*(DFF\S+)\s+([^\n]+)\(\s*$', text, re.M)
rr = sum('bank.rr_d' in name for _, name in cells)
eg = sum('bank.eg_d' in name for _, name in cells)
# The mirror bit in eg is always one when valid and may optimize to a constant.
result = {'mapped_DFF_clock_sinks': len(cells), 'macro_clock_sinks': 3,
          'rr_payload_DFFs': rr, 'required_rr_payload_DFFs': args.read_groups * 256,
          'eg_payload_DFFs': eg, 'required_eg_payload_DFFs': 274,
          'pass': rr >= args.read_groups * 256 and eg >= 274}
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['pass'] else 1)
