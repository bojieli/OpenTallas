import json, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import pdn_regroup  # noqa: E402

PDN = '''# r5
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name core -voltage_domains CORE -pins {M9} -starts_with GROUND
add_pdn_stripe -grid core -layer M8 -width .48 -pitch 9.091 -offset 0
add_pdn_stripe -grid core -layer M9 -width .48 -pitch 9.091 -offset 0
add_pdn_connect -grid core -layers {M8 M9}
add_pdn_stripe -grid core -layer M1 -width .018 -followpins
add_pdn_stripe -grid core -layer M2 -width .018 -followpins
add_pdn_stripe -grid core -layer M3 -width 0.09 -pitch 4.32 -spacing 2.07 -offset 1.08 -extend_to_boundary
add_pdn_stripe -grid core -layer M4 -width 0.12 -pitch 4.32 -spacing 2.04 -offset 1.08 -extend_to_boundary
add_pdn_stripe -grid core -layer M5 -width 0.12 -pitch 8.64 -spacing 4.2 -offset 2.16 -extend_to_boundary
add_pdn_stripe -grid core -layer M6 -width 0.16 -pitch 8.64 -spacing 4.16 -offset 2.16 -extend_to_boundary
add_pdn_stripe -grid core -layer M7 -width 0.16 -pitch 8.64 -spacing 4.16 -offset 2.16 -extend_to_boundary
''' + ''.join(f'add_pdn_connect -grid core -layers {{M{i} M{i+1}}}\n' for i in range(1, 8)) + '''define_pdn_grid -macro -instances {^a$} -voltage_domains CORE -name pg_0 -starts_with GROUND -grid_over_boundary
add_pdn_stripe -grid pg_0 -layer M8 -width .48 -pitch 9.091 -offset 1.0
add_pdn_connect -grid pg_0 -layers {M7 M8}
add_pdn_connect -grid pg_0 -layers {M8 M9}
'''
RUN = '''read_db /work/floorplan.odb
mem read
set t0 [clock seconds]
if {[catch {source /work/pdn.tcl; pdngen; source /work/die_constant_pg_check.tcl} err]} { error $err }
'''


class TieLocal(unittest.TestCase):
    def case(self, run=RUN):
        d = Path(tempfile.mkdtemp())
        (d / 'pdn.tcl').write_text(PDN)
        (d / 'run_pdn.tcl').write_text(run)
        (d / 'pos.json').write_text(json.dumps({'insts': [{'n': 'a', 'x': 0.0, 'y': 2.16}]}))
        return d

    def test_r8_strips_ladder_and_stacks_to_m9(self):
        d = self.case()
        r = pdn_regroup.regroup(d, 8.64, 'pdn.tcl', pos_json=d / 'pos.json', tie_local_pg=True)
        out = (d / 'pdn.tcl').read_text()
        for layer in 'M3 M4 M5 M6 M7'.split():
            self.assertNotIn(f'-grid core -layer {layer} ', out)
        for i in range(2, 8):
            self.assertNotIn(f'-grid core -layers {{M{i} M{i+1}}}', out)
        self.assertIn('add_pdn_connect -grid core -layers {M1 M2}\nadd_pdn_connect -grid core -layers {M2 M9}', out)
        self.assertIn('-layer M2 -width .018 -followpins', out)
        self.assertIn('add_pdn_connect -grid pg_m8_0 -layers {M7 M8}', out)       # macro grids keep their M7->M8 vias
        self.assertEqual(r['r8_tie_local']['dropped_ladder_lines'], 11)
        run = (d / 'run_pdn.tcl').read_text()
        self.assertLess(run.index('ot_tie_rows 8.640 0.48 9.091 0.480'), run.index('source /work/pdn.tcl'))
        self.assertIn('pdngen; ot_tie_rows_verify 8.640 0.48;', run)
        self.assertTrue((d / 'die_tie_rows.tcl').is_file())
        # idempotent run_pdn patch
        (d / 'pdn.tcl').write_text(PDN)
        pdn_regroup.regroup(d, 8.64, 'pdn.tcl', pos_json=d / 'pos.json', tie_local_pg=True)
        self.assertEqual((d / 'run_pdn.tcl').read_text().count('ot_tie_rows_verify'), 1)

    def test_default_keeps_ladder(self):
        d = self.case()
        pdn_regroup.regroup(d, 8.64, 'pdn.tcl', pos_json=d / 'pos.json')
        self.assertIn('-grid core -layer M3 ', (d / 'pdn.tcl').read_text())
        self.assertNotIn('ot_tie_rows', (d / 'run_pdn.tcl').read_text())

    def test_mutant_missing_hook_refuses(self):
        d = self.case(run=RUN.replace('mem read\n', ''))
        with self.assertRaises(SystemExit):
            pdn_regroup.regroup(d, 8.64, 'pdn.tcl', pos_json=d / 'pos.json', tie_local_pg=True)


if __name__ == '__main__':
    unittest.main()
