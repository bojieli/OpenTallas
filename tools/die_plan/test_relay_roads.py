import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import relay_roads as R

HERE = Path(__file__).parent


def graph():
    return {'cells': {'b': {'master': 'BUFx2', 'pins': {'A': {'net': 'n0', 'direction': 'INPUT'}, 'Y': {'net': 'n1', 'direction': 'OUTPUT'}}}},
            'nets': {'n0': {'sig_type': 'SIGNAL', 'pins': [{'pin': 'src/Q', 'direction': 'OUTPUT', 'sig_type': 'SIGNAL'}, {'pin': 'b/A', 'direction': 'INPUT', 'sig_type': 'SIGNAL'}]},
                     'n1': {'sig_type': 'SIGNAL', 'pins': [{'pin': 'b/Y', 'direction': 'OUTPUT', 'sig_type': 'SIGNAL'}, {'pin': 'dst/D', 'direction': 'INPUT', 'sig_type': 'SIGNAL'}]}}}


ROAD = {'source_pin': 'src/Q', 'sink_pin': 'dst/D', 'polyline_um': [[0, 0], [0, 10], [10, 10]]}


class Roads(unittest.TestCase):
    def test_exact_buffers_and_missing_site(self):
        g = graph()
        self.assertEqual(R.trace_roads(g, [ROAD])[0]['buffers'], ['b'])
        with self.assertRaisesRegex(R.RoadError, 'lack explicit'):
            R.compile_sites(g, [ROAD], {'dst': {'origin_um': [1, 1], 'orient': 'R0'}})
        text, _ = R.compile_sites(g, [ROAD], {'b': {'origin_um': [1, 1], 'orient': 'R0'}})
        self.assertIn('PIN\tb\tA\tn0', text)

    def test_clock_and_disconnected_fail(self):
        g = graph(); g['nets']['n0']['sig_type'] = 'CLOCK'
        with self.assertRaisesRegex(R.RoadError, 'non-data'):
            R.trace_roads(g, [ROAD])
        with self.assertRaisesRegex(R.RoadError, 'non-buffer'):
            R.trace_roads(graph(), [{**ROAD, 'source_pin': 'wrong/Q'}])

    def test_data_sites_and_shared_corridor(self):
        g = graph()
        rows = {'row0': {'site_w': .054, 'site_h': .27, 'nsites': 400},
                'rows': [(0, k*.27, 'R0' if k%2 == 0 else 'MX', 400) for k in range(20)],
                'masters': {'BUFx2': (.216, .27)}, 'fixed': [(4, 0, 6, 2)],
                'pg': {'M5': [(0, 0, 20, 20)]}}
        trace = {**ROAD, 'polyline_um': [[0, 1.35], [10, 1.35]], 'buffers': ['b']}
        placed = R.allocate_buffer_sites(g, [trace], rows, {}, .3)['b']
        self.assertTrue(placed['origin_um'][0]+.216 <= 4 or placed['origin_um'][0] >= 6)
        # A single physical buffer cannot be separately averaged onto two roads.
        other = {**trace, 'polyline_um': [[0, 4.35], [10, 4.35]]}
        with self.assertRaisesRegex(R.RoadError, 'no common branch'):
            R.allocate_buffer_sites(g, [trace, other], rows, {}, .3)

    def test_fragment_rows_share_occupancy(self):
        g = graph(); g['cells']['c'] = g['cells']['b'].copy()
        rows = {'row0': {'site_w': .054, 'site_h': .27, 'nsites': 400},
                'rows': [(0, 0, 'R0', 40), (8.1, 0, 'R0', 40)],
                'masters': {'BUFx2': (.216, .27)}, 'fixed': [], 'pg': {'M5': []}}
        trace = {**ROAD, 'polyline_um': [[0, .135], [10, .135]], 'buffers': ['b','c']}
        placed = R.allocate_buffer_sites(g, [trace], rows, {}, .2)
        self.assertNotEqual(placed['b']['origin_um'],placed['c']['origin_um'])
        for cell in placed.values():
            x,y = cell['origin_um']
            self.assertTrue(x+.216 <= 2.16+1e-6 or x >= 8.1-1e-6)

    def test_actual_buffer_pin_price(self):
        g=graph();g['cells']['b'].update(origin_um=[0,0],orient='R0',height_um=.27)
        g['cells']['b']['pins']['A']['xy_um']=[.1,.135]
        g['cells']['b']['pins']['Y']['xy_um']=[.2,.135]
        trace={**ROAD,'polyline_um':[[0,.135],[10,.135]],'buffers':['b']}
        sites={'b':{'origin_um':[4,0],'orient':'R0'}}
        self.assertAlmostEqual(R.price_buffer_paths(g,[trace],sites,10)[0]['wire_length_um'],9.9)
        sites['b']['origin_um']=[4,4]
        self.assertFalse(R.price_buffer_paths(g,[trace],sites,10)[0]['pass'])

    def test_tcl_transaction(self):
        # Execute the real runtime helper with a tiny OpenDB command fixture.
        # Mutants stop BEFORE setLocation; default helper sourcing is inert.
        mock = '''
namespace eval ord { proc get_db_block {} {return block}; proc get_db_tech {} {return tech} }
proc tech {m args} {return 1000}
proc block {m args} {switch $m {findInst {if {[lindex $args 0] eq "b"} {return cell};return NULL} getRows {return row} getInsts {return cell}}}
proc row {m args} {switch $m {getOrigin {return {0 0}} getSite {return site} getSiteCount {return 1000} getOrient {return R0}}}
proc site {m args} {switch $m {getWidth {return 10} getHeight {return 270}}}
proc cell {m args} {switch $m {getMaster {return master} getName {return b} getITerms {return {pinA pinY}} setLocation {set ::moved 1} setOrient {} getPlacementStatus {return $::status} setPlacementStatus {set ::status [lindex $args 0]}}}
proc master {m args} {switch $m {getName {return BUFx2} isBlock {return 0} getWidth {return 20} getHeight {return 270}}}
proc pinA {m args} {switch $m {getSigType {return SIGNAL} getNet {return n0} getMTerm {return mtA}}}
proc pinY {m args} {switch $m {getSigType {return SIGNAL} getNet {return n1} getMTerm {return mtY}}}
proc mtA {m args} {return A};proc mtY {m args} {return Y}
proc n0 {m args} {return n0};proc n1 {m args} {return n1}
set moved 0
set status PLACED
'''
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            for mutant in ('good', 'badnet', 'badsite', 'badmaster'):
                text = 'DBU\t1000\nCELL\tb\tBUFx2\t100\t0\tR0\t8640\nPIN\tb\tA\tn0\nPIN\tb\tY\tn1\n'
                if mutant == 'badnet': text = text.replace('PIN\tb\tA\tn0', 'PIN\tb\tA\twrong')
                if mutant == 'badsite': text = text.replace('\t100\t0', '\t101\t0')
                if mutant == 'badmaster': text = text.replace('BUFx2', 'BUFx4')
                (p / 'sites.tsv').write_text(text)
                code = mock + f'\nset ::env(RESULTS_DIR) {{{p}}}\nsource {{{HERE / "relay_roads.tcl"}}}\n'
                code += f'set failed [catch {{ot_relay_roads {{{p / "sites.tsv"}}}}} why]\nputs "RESULT $failed $moved"\n'
                if mutant == 'good':
                    (p / 'ot_face_flops.txt').write_text('')
                    (p / 'ot_relay_mid.txt').write_text('b\n')
                    code += f'set ::env(OT_RELAY_ROAD_FILE) {{{p / "sites.tsv"}}}\nsource {{{HERE / "face_flops_release.tcl"}}}\nputs "KEPT $status"\n'
                result = subprocess.run(['tclsh'], input=code, text=True, capture_output=True, check=True)
                if mutant == 'good':
                    self.assertIn('KEPT FIRM', result.stdout)
                self.assertIn('RESULT 0 1' if mutant == 'good' else 'RESULT 1 0', result.stdout, result.stderr + result.stdout)


if __name__ == '__main__':
    unittest.main()
