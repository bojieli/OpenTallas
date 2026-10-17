import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from v16_fetch import REMOTE_PY, check_direct_master, check_sources, check_etm_signature, check_contract_entry


class FetchAdmission(unittest.TestCase):
    def test_current_contract_membership_and_parameter_binding(self):
        entry = dict(representative='a', instances=['a', 'b'], master='M', params={'N': 2})
        instance = dict(master='M', params={'N': 2},
                        ports={'i': {'direction': 'input', 'bits': 2}})
        contract = {'instances': {'a': copy.deepcopy(instance), 'b': copy.deepcopy(instance)}}
        self.assertEqual(check_contract_entry(entry, contract), instance)
        for member in ('a', 'b'):
            for key, value in [('master', 'OTHER'), ('params', {'N': 4}),
                               ('ports', {'i': {'direction': 'output', 'bits': 2}}),
                               ('ports', {'i': {'direction': 'input', 'bits': 3}})]:
                with self.subTest(member=member, field=key, value=value):
                    changed = copy.deepcopy(contract)
                    changed['instances'][member][key] = value
                    with self.assertRaises(ValueError):
                        check_contract_entry(entry, changed)
        for missing in ('a', 'b'):
            changed = copy.deepcopy(contract)
            del changed['instances'][missing]
            with self.subTest(missing=missing), self.assertRaises(KeyError):
                check_contract_entry(entry, changed)
        with self.assertRaises(ValueError):
            check_contract_entry(dict(entry, params={'N': 4}), contract)

    def test_actual_liberty_cell_and_ports_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'model.lib'
            p.write_text('library(model) {\n cell("wrapper") {\n pin(clk) { direction : input; }\n }}\n')
            check_etm_signature(p, 'wrapper', {'clk': ('input', 1)})
            with self.assertRaisesRegex(ValueError, 'Wrong actual ETM cell'):
                check_etm_signature(p, 'default', {'clk': ('input', 1)})
            with self.assertRaisesRegex(ValueError, 'ports differ'):
                check_etm_signature(p, 'wrapper', {'clk': ('input', 1), 'missing': ('output', 8)})

    def test_ignored_wrapper_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); d = root / 'syn' / 'cell'; d.mkdir(parents=True)
            (d / 'cell.ys').write_text('hierarchy -check -top default_master\n')
            r = subprocess.run([sys.executable, '-c', REMOTE_PY, tmp, tmp, 'cell', 'parameter_wrapper'],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('Wrong synthesized top', r.stderr)

    def test_actual_source_and_wrapper_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); d = root / 'syn' / 'cell'; d.mkdir(parents=True)
            src = root / 'src'; (src / 'v16w').mkdir(parents=True)
            wrapper = b'`include "coeff.svh"\nmodule parameter_wrapper; endmodule\n'
            (src / 'v16w' / 'wrapper.sv').write_bytes(wrapper)
            (src / 'v16w' / 'coeff.svh').write_bytes(b'// exact consumed include\n')
            (d / 'cell.ys').write_text('read_verilog -sv v16w/wrapper.sv\nhierarchy -check -top parameter_wrapper\n')
            (d / 'cell.stat').write_text("Chip area for top module 'parameter_wrapper': 12.5\n")
            (d / 'cell.files.json').write_text(json.dumps({'macros': []}))
            r = subprocess.run([sys.executable, '-c', REMOTE_PY, tmp, str(src), 'cell', 'parameter_wrapper'],
                               capture_output=True, text=True, check=True)
            m = json.loads(r.stdout)
            self.assertEqual(m['actual_top'], 'parameter_wrapper')
            self.assertEqual(m['source_file_sha256']['v16w/wrapper.sv'], hashlib.sha256(wrapper).hexdigest())
            self.assertEqual(m['source_file_sha256']['v16w/coeff.svh'],
                             hashlib.sha256(b'// exact consumed include\n').hexdigest())
            (root / 'views' / 'wrap').mkdir(parents=True)
            (root / 'views' / 'wrap' / 'wrapper.sv').write_bytes(wrapper)
            (root / 'views' / 'wrap' / 'coeff.svh').write_bytes(b'// exact consumed include\n')
            check_sources(m, 'HEAD', root / 'views')
            (root / 'views' / 'wrap' / 'coeff.svh').write_bytes(b'// changed include\n')
            with self.assertRaisesRegex(ValueError, 'Parameter wrapper mismatch'):
                check_sources(m, 'HEAD', root / 'views')
            (root / 'views' / 'wrap' / 'coeff.svh').write_bytes(b'// exact consumed include\n')
            (root / 'views' / 'wrap' / 'wrapper.sv').write_bytes(wrapper + b'// different parameters\n')
            with self.assertRaisesRegex(ValueError, 'Parameter wrapper mismatch'):
                check_sources(m, 'HEAD', root / 'views')
            (src / 'coeff.svh').write_bytes(b'// ambiguous current-directory include\n')
            r = subprocess.run([sys.executable, '-c', REMOTE_PY, tmp, str(src), 'cell', 'parameter_wrapper'],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('Missing/ambiguous include', r.stderr)

    def test_modified_snapshot_source_is_rejected(self):
        path = 'tools/hbm_die_v15/synth_master.sh'
        with self.assertRaisesRegex(ValueError, 'Source differs'):
            check_sources({'source_file_sha256': {path: '0' * 64}}, 'HEAD', '.')

    def test_direct_master_requires_empty_params_exact_recipe_and_ports(self):
        entry = dict(params={}, master='cell', cell='cell', wrapper='v16w_cell', env='', blackbox='-')
        resolution = dict(top='cell', files=['rtl/cell.sv'], macros=[], blackboxes=[], unresolved=[], ambiguous={})
        script = '\n'.join(['read_verilog -sv -DSYNTHESIS v16w/v16w_cell.sv',
                            'read_verilog -sv -DSYNTHESIS rtl/cell.sv', 'hierarchy -check -top cell',
                            'tee -o /out/cell.hier.stat stat', 'synth -top cell',
                            'dfflibmap -liberty /tmp/lib/seq.lib', 'abc -liberty /tmp/lib/all.lib', 'opt_clean',
                            'tee -o /out/cell.stat stat -liberty /tmp/lib/all.lib',
                            'write_verilog -noattr /out/cell.netlist.v']) + '\n'
        meta = dict(actual_top='cell', expected_resolution=resolution, actual_elaboration_script=script)
        ports = {'clk': ('input', 1), 'o': ('output', 8)}
        check_direct_master(entry, meta, ports, ports)
        with self.assertRaisesRegex(ValueError, 'params'):
            check_direct_master(dict(entry, params={'FEATURE': 1}), meta, ports, ports)
        with self.assertRaisesRegex(ValueError, 'port'):
            check_direct_master(entry, meta, ports, dict(ports, o=('output', 7)))
        with self.assertRaisesRegex(ValueError, 'recipe'):
            check_direct_master(entry, dict(meta, actual_elaboration_script=script.replace('-DSYNTHESIS', '-DSYNTHESIS -DOTHER')), ports, ports)
        with self.assertRaisesRegex(ValueError, 'recipe'):
            check_direct_master(entry, dict(meta, actual_elaboration_script=script.replace('synth -top', 'chparam -set FEATURE 1 cell\nsynth -top')), ports, ports)


if __name__ == '__main__':
    unittest.main()
