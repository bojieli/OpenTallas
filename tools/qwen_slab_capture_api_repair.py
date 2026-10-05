#!/usr/bin/env python3
"""Bounded physical API adapter: OpenDB EXCLUSIVE serializes to DEF FENCE.

The original r1 hooks and failures remain frozen. No RTL/geometry/cell/clock change.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HEIGHTS=(456,570,685)


def adapt(original):
    if original.count('$region setRegionType FENCE')!=1 or original.count('$group setRegion $region')!=1:
        raise ValueError('expected exactly the frozen region-type and attachment calls')
    return original.replace('$region setRegionType FENCE',
        '# Pinned OpenDB EXCLUSIVE writes DEF TYPE FENCE; hard inside/exclusion semantics.\n  $region setRegionType EXCLUSIVE').replace('$group setRegion $region','$region addGroup $group')


def validation_checks():
    return r"""
set repair_total 0
for {set c 0} {$c < 4} {incr c} {
  set r [$cap_block findRegion "capture_col_$c"]
  set g [$cap_block findGroup "capture_col_$c"]
  if {[$r getRegionType] != "EXCLUSIVE"} {error "capture region is not hard EXCLUSIVE"}
  if {[llength [$r getGroups]] != 1} {error "capture region does not have one group"}
  if {[[$g getRegion] getName] != [$r getName]} {error "capture group region mismatch"}
  if {[llength [$g getInsts]] != 128} {error "capture group membership !=128"}
  if {[llength [$r getBoundaries]] != 1} {error "capture region rectangle count changed"}
  incr repair_total [llength [$g getInsts]]
  puts "CAPTURE_API_GROUP $c TYPE [$r getRegionType] FF [llength [$g getInsts]]"
}
if {$repair_total !=512 || [dict size $cap_seen] !=512} {error "capture unique membership !=512"}
puts "CAPTURE_API_MEMBERSHIP_PASS 4 EXCLUSIVE_GROUPS 512 UNIQUE_FF"
"""


def generate():
    out={}
    for n in HEIGHTS:
        old=ROOT/f'physical/qwen_slab_fanout/capture_{n}.tcl'
        new=ROOT/f'physical/qwen_slab_fanout/capture_api_r2_{n}.tcl'
        new.write_text(adapt(old.read_text())+validation_checks())
        out[n]=dict(original=str(old.relative_to(ROOT)),original_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),
            corrected=str(new.relative_to(ROOT)),corrected_sha256=hashlib.sha256(new.read_bytes()).hexdigest(),
            region_semantics='OpenDB EXCLUSIVE / emitted DEF FENCE',regions=4,FF_each=128,unique_FF=512,
            changed_geometry=False,changed_RTL=False,new_area_or_cycles=0)
    return out


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(generate(),indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
