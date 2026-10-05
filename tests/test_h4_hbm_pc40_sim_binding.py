import re
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import h4_hbm_pc40_sim_binding as B


def port_names(source):
    header=source.split(')(\n',1)[1].split(');',1)[0]
    names=[]
    for m in re.finditer(r'\b(?:input|output)\s+wire\s*(?:\[[^]]+\])?\s*([^\n]*?)(?=\binput|\boutput|\n|$)',header):
        names.extend(x.strip() for x in m.group(1).rstrip(',').split(',') if x.strip())
    return names


class SimBinding(unittest.TestCase):
    def test_all_actual_connector_ports_connected(self):
        original=(ROOT/B.FILES[9]).read_text()
        top=(ROOT/B.FILES[11]).read_text()
        instance=top.split(' connector(',1)[1].split(');',1)[0]
        connections=dict(re.findall(r'\.(\w+)\(([^()]*)\)',instance))
        self.assertEqual(set(connections),set(port_names(original)))
        self.assertTrue(all(name==value for name,value in connections.items()))

    def test_actual_provider_not_bare_ACK_or_fixture(self):
        top=(ROOT/B.FILES[11]).read_text()
        self.assertIn('ot_gpu_rf_service #(.ACK_ID(1)) rf(',top)
        for port in ('ack_owner','ack_slot','ack_identity_fault','wr_owner'):
            self.assertIn('.'+port+'('+port+')',top)
        self.assertNotIn('seed',top)
        self.assertNotIn('always #',top)
        self.assertNotIn('initial',top)

    def test_exact_existing_SRAM_body_without_testbench(self):
        original=(ROOT/'rtl/test/hbm_c0_connected_20261003/r3/tb.sv').read_text()
        module='module ot_sram_1r1w_128x256_m1_r2c2'
        body=(ROOT/B.FILES[10]).read_text()
        self.assertEqual(body[body.index(module):],original[original.index(module):])
        self.assertNotIn('module tb',body)

    def test_observers_sample_actual_handshakes(self):
        top=(ROOT/B.FILES[11]).read_text()
        for name,value in {'rf_read_accepted':'rd_valid&&rd_ready',
                           'rf_response_accepted':'rsp_valid&&rsp_ready',
                           'rf_write_accepted':'wr_valid&&wr_ready',
                           'rf_ACK_accepted':'ack_valid&&ack_ready'}.items():
            self.assertIn('assign '+name+'='+value+';',top)

    def test_minimal_sources_no_W2_or_fixture(self):
        report=B.binding()
        self.assertEqual(len(report['sources']),12)
        self.assertFalse(report['W2_dependency'])
        self.assertFalse(report['fixture_dependency'])
        self.assertFalse(report['compile_or_run'])
        self.assertEqual(report['storage']['existing_RF_bytes'],524288)
        self.assertTrue(all('/test/' not in r['path'] for r in report['sources']))

    def test_fusion_cannot_mislabel_FMIN_as_FMAX(self):
        report=B.binding()
        self.assertFalse(report['fusion']['per_primitive_drop_in'])
        self.assertIn('actual FMAX bytes',report['fusion']['FMAX_reply'])
        self.assertIn('matching fragment owner',report['fusion']['FMIN_reply'])


if __name__=='__main__':unittest.main()
