"""Focused source/ABI checks, not an S81 execution/qualification campaign."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wf_install', ROOT/'tools/dsrom_wavefront_install.py')
W = importlib.util.module_from_spec(spec)
spec.loader.exec_module(W)


def fixture():
    sources = [ROOT/'rtl/dsrom_sys/s81_capture_parent'/n for n in W.ROLES]
    return dict(sources=sources, source_sha256={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                parameters=dict(S81_CAPTURE=1, S81_HOST_WORKSPACE=1, COLL_ACCEPTED_POP=1,
                                C8_CONTEXT=1, C8_PUBLICATION=1), verilator_args=[])


class WiringTests(unittest.TestCase):
    def test_selected_ports_default_off_and_original_fences(self):
        with tempfile.TemporaryDirectory() as d:
            selected = fixture()
            before = [p.read_bytes() for p in selected['sources']]
            r = W.install(selected, d)
            self.assertEqual(r['parameters']['PKG_WAVE'], 0)
            self.assertFalse(r['wavefront_request_to_C8_bound'])
            die, top = [p.read_text() for p in r['sources'][:2]]
            for line in before[0].decode().splitlines():
                if 'assign c8_write_quiet=' in line or 'assign capture_visibility_quiet' in line:
                    self.assertIn(line, die)
            self.assertIn(".host_mode(1'b1)", top)
            self.assertIn('.host_start(C8_CONTEXT ? c8_engine_start : start)', top)
            self.assertIn('.pr_qk(PKG_WAVE && wf_pr_qk)', die)
            self.assertIn('.core_next_token(PKG_WAVE ? wf_stage_next_token : core_next_token)', die)
            self.assertIn('wf_stage_done && wf_result_visible', die)
            self.assertIn('.core_done_accepted(wf_stage_accepted)', die)
            adapter = r['sources'][-1].read_text()
            recovered = adapter.replace('module ot_rom_pkg_ctrl_wf_s81 #(', 'module ot_rom_pkg_ctrl_wf #(').replace('    output wire               core_done_accepted,\n', '').replace('\n    assign core_done_accepted = WAVE && job_done;', '')
            self.assertEqual(recovered, W.CONTROLLER.read_text())
            self.assertNotIn('.core_done(c8_retire_v)', die)
            for link in ('ucie', 'bl'):
                self.assertIn('.'+link+'_rx_valid(PKG_WAVE ? wf_'+link+"_rx_valid : 1'b0)", top)
                self.assertIn('.'+link+'_tx_ready(PKG_WAVE ? wf_'+link+"_tx_ready : 1'b1)", top)
            self.assertEqual(before, [p.read_bytes() for p in selected['sources']])
            again = W.install(selected, d, enable=True)
            self.assertEqual(again['parameters']['PKG_WAVE'], 1)
            self.assertEqual(r['source_sha256'], again['source_sha256'])

    def test_reject_pin_change_and_missing_capture(self):
        selected = fixture()
        with tempfile.TemporaryDirectory() as d:
            selected['source_sha256'][str(selected['sources'][0])] = 'wrong'
            with self.assertRaises(ValueError): W.install(selected, d)
            self.assertEqual(list(Path(d).iterdir()), [])
            selected = fixture()
            selected['parameters']['S81_CAPTURE'] = 0
            with self.assertRaises(ValueError): W.install(selected, d)

    def test_reject_hook_change_before_any_output(self):
        with tempfile.TemporaryDirectory() as d:
            selected = fixture()
            inp = Path(d)/'input'
            inp.mkdir()
            p = inp/W.ROLES[1]
            p.write_text(selected['sources'][1].read_text().replace(".host_mode(1'b1)", ".host_mode(1'b0)"))
            selected['sources'][1] = p
            selected['source_sha256'][str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
            out = Path(d)/'output'
            with self.assertRaises(ValueError): W.install(selected, out)
            self.assertFalse(out.exists())

    def test_immutable_conflict_and_disjoint_output(self):
        with tempfile.TemporaryDirectory() as d:
            selected = fixture()
            r = W.install(selected, d)
            r['sources'][1].write_text('different')
            with self.assertRaises(FileExistsError): W.install(selected, d)
            with self.assertRaises(ValueError): W.install(selected, selected['sources'][0].parent)


if __name__ == '__main__':
    unittest.main(verbosity=2)
