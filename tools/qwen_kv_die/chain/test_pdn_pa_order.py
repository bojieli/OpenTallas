#!/usr/bin/env python3
"""KV run_pdn.tcl: the temporary PDN bbox master swap must precede pin access (kvs8-codex-1338 'map::at')."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kv_die as K  # noqa: E402

VEHICLE = """read_db /work/floorplan.odb
mem read
set_routing_layers -signal M2-M9
""" + K.PDN_PA_BLOCK + """set t0 [clock seconds]
if {[catch {source /work/pdn.tcl; pdngen; source /work/die_constant_pg_check.tcl} err]} { error $err }
mem pdn
foreach net {VDD VSS} { puts "OT_PGCHECK $net PASS" }
write_db /work/floorplan_pdn.odb
"""


class PaOrder(unittest.TestCase):
    def test_pa_after_pdn_and_pg(self):
        out = K.pdn_pin_access_after_pdn(VEHICLE)
        self.assertEqual(out.count('pin_access'), 1)
        self.assertLess(out.index('pdngen'), out.index('pin_access'))
        self.assertLess(out.index('OT_PGCHECK'), out.index('pin_access'))
        self.assertLess(out.index('pin_access'), out.index('write_db'))

    def test_changed_vehicle_fails_closed(self):
        with self.assertRaises(ValueError):
            K.pdn_pin_access_after_pdn(VEHICLE.replace('pin_access -verbose 1', 'pin_access'))
        with self.assertRaises(ValueError):
            K.pdn_pin_access_after_pdn(VEHICLE.replace('write_db', 'write_def'))


if __name__ == '__main__':
    unittest.main()
