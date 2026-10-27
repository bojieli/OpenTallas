#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path
from current_native_top import compose


def fixture():
    lines = ['module original (clk,rst);', 'input clk;', 'input rst;']
    roles = dict(SW='hfd_hgi_vms_glue_sw_t',SE='hfd_hgi_vms_static_SE_glue',NW='hfd_hgi_vms_glue_nw_t',NE='hfd_hgi_vms_static_NE_glue')
    for q in roles:
        lines += [f'wire [305:0] hb_idx__s_{q}__score;', f'wire hb_idx__s_{q}__fault;']
    for q, master in roles.items():
        lines += [f'  {master} hb_vms_{q} (', '    .clk(clk),', '    .rst_n(rst)', '  );']
        ports = {p: 'clk' for p in ('clk_ctl','clk_engine','clk_meta','clk_tail','clk_chunk','clk_hslice')}
        ports.update(rst_n='rst', half="1'd0", score=f'hb_idx__s_{q}__score',fault=f'hb_idx__s_{q}__fault')
        lines += [f'  ot_hbm_idx_score_quarter_static hb_idx__s_{q} (', ',\n'.join(f'    .{p}({x})' for p,x in ports.items()), '  );']
    return '\n'.join(lines + ['endmodule'])


class CompositionTest(unittest.TestCase):
    def run_compose(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'original.v').write_text(text)
            (root/'base.v').write_text('module base (clk);\ninput clk;\nendmodule\n')
            report = compose(root/'original.v', root/'base.v', {'transport':[]}, root/'out')
            return report, (root/'out/hbm_current_native_top.sv').read_text(), json.loads((root/'out/native_instance_manifest.json').read_text())

    def test_real_roles_and_explicit_controls(self):
        report, rtl, instances = self.run_compose(fixture())
        self.assertEqual(report['status'], 'FAIL_CLOSED_NATIVE_PROVIDERS_MISSING')
        self.assertEqual(len(report['obligations']), 48)
        self.assertEqual(len([x for x in instances if x.startswith('hb_vms_')]),4)
        self.assertEqual(len([x for x in instances if x.startswith('hb_idx__s_')]),4)
        for obligation in report['obligations']:
            self.assertIn('input wire [' + str(obligation['width']-1) + ':0] ' + obligation['net'] + ';',rtl)
        self.assertEqual(instances['u_mu_fused_root']['ports']['up_nw']['segments'],[['n','u_mu_fused_n4_nw__uo',0,270]])
        self.assertEqual(instances['u_mu_fused_n4_ne']['ports']['dn']['segments'],[['n','u_mu_fused_root__down_ne',0,172]])

    def test_wrong_vms_role_mutant_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'VMS role/master'):
            self.run_compose(fixture().replace('hfd_hgi_vms_glue_sw_t','hfd_hgi_vms_glue_nw_t'))

    def test_distinct_quarter_clock_mutant_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'clocks do not resolve'):
            self.run_compose(fixture().replace('.clk_tail(clk)', '.clk_tail(rst)',1))


if __name__ == '__main__': unittest.main()
