#!/usr/bin/env python3
"""Repair native S81 repeater identity without changing placement or timing policy.

Use on a fresh copy of eco_hs.tcl, never modify a running job's script.
"""
import argparse
from pathlib import Path

OLD_NAME = 'global rk; set nm "slweco_$rk"; incr rk'
NEW_NAME = '''global rk
  # Baselines can contain earlier slweco_* cells. Select an unused exact name
  # before insert_buffer; never infer the result with a prefix wildcard.
  while {1} {
    set nm "ot_nm_repeater_$rk"; incr rk
    if {![llength [get_cells -quiet $nm]] && ![llength [get_nets -quiet ${nm}_n]]} break
  }'''
OLD_LOOKUP = 'set b [lindex [get_cells ${nm}*] 0]; set bn [get_full_name $b]'
NEW_LOOKUP = '''set found [get_cells -quiet $nm]
  if {[llength $found] != 1} {error "ECO repeater exact identity missing: $nm"}
  set b [lindex $found 0]; set bn [get_full_name $b]
  if {$bn ne $nm} {error "ECO repeater renamed unexpectedly: $nm -> $bn"}'''

def patch(text):
    for old in (OLD_NAME, OLD_LOOKUP):
        if text.count(old) != 1:
            raise ValueError(f'Expected one original repeater identity expression: {old}')
    return text.replace(OLD_NAME, NEW_NAME).replace(OLD_LOOKUP, NEW_LOOKUP)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source', type=Path)
    ap.add_argument('destination', type=Path)
    args = ap.parse_args()
    if args.destination.exists():
        ap.error('Destination must be fresh; failed and running scripts remain untouched')
    args.destination.write_text(patch(args.source.read_text()))
