#!/usr/bin/env python3
"""Geometry regression: full block union and wire conservation in local windows."""
import unittest
from window_audit import segment, union_area, VM

class Geometry(unittest.TestCase):
    def test_union_does_not_double_count_nested_vm_blockage(self):
        self.assertEqual(union_area([VM,VM,(VM[0]+1,VM[1]+1,VM[2]-1,VM[3]-1)],VM),(VM[2]-VM[0])*(VM[3]-VM[1]))
    def test_wire_length_conserved_across_window_boundaries(self):
        for a,b in [((-10,31),(1090,31)),((91,-55),(91,1370))]:
            self.assertAlmostEqual(sum(n for _,_,n in segment(a,b,260)),abs(b[0]-a[0])+abs(b[1]-a[1]))
    def test_local_density_exposes_full_line_dilution(self):
        # 1000 bits confined to a 260um square: at 10 tracks/um,
        # the local demand/capacity is .385; a 26mm cut averages to .00385.
        # Raise demand to 2000: local .769 fails .60 while full-line .00769 passes.
        bits=2000; length=260; density=10
        demand=sum(bits*n for _,_,n in segment((0,130),(260,130),260))
        self.assertGreater(demand/(260*260*density),.60)
        self.assertLess(bits/(26000*density),.60)
if __name__=='__main__': unittest.main()
