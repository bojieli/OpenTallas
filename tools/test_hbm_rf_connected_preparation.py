#!/usr/bin/env python3
"""Short static preparation/synthetic parser tests only; no RTL execution."""
import json,subprocess,unittest
from pathlib import Path
import check_hbm_rf_connected_trace as T
import prepare_hbm_rf_connected_gate as P
R=P.ROOT

def synthetic(q=0):
    lines=['RESET_RF_FENCE_PASS qwen=%d actualmatrixproducer=1 staleepoch_rejected=1'%q]
    for c,(rows,scratch) in enumerate([(16,0),(16,1),(4096,0),(4096,0)],1):
        n=rows*(16 if q else 8)//128;hold=240 if c==4 else 0
        def stamp(name,t):lines.append(f'STAMP case={c} qwen={q} name={name} cycle={t}')
        stamp('producer_first_rv',1);stamp('producer_last_rv',2)
        for i in range(n):
            for k,t in [('RF_VECTOR_WRITE',3+i*3),('RF_VECTOR_ACK_VISIBLE',4+i*3),('RF_VECTOR_ACK_RETIRE',5+i*3)]:
                lines.append(f'{k} case={c} index={i} epoch={c} cycle={t+(hold if k=="RF_VECTOR_ACK_RETIRE" and i==n-1 else 0)}')
        t=6+3*n+hold;stamp('RF_fence_valid',t)
        for pas in range(2):
            for i in range(n):
                t+=20;lines.append(f'SIMD_ALIAS_ACCEPT case={c} pass={pas} index={i} a={i} b={i} dst={i} cycle={t}')
            t+=15;stamp('SIMD_last_done',t)
        t+=1;stamp('RF_operand_read_visible',t)
        if scratch:
            t+=20;stamp('scratch_write_done',t);t+=20;stamp('scratch_read_done',t)
        t+=10;stamp('consumer_x_last_write',t);t+=1;stamp('consumer_start',t);t+=5;stamp('consumer_first_valid_issue',t)
        lines.append(f'CASE id={c} qwen={q} rows={rows} vectors={n} scratch={scratch} hold_cycles={hold}')
    lines.append(f'CONNECTED_RF_FENCE_PASS qwen={q} cases=4 plus_reset=1 dependent_alias_ops=2_per_vector no_blackboxes=1')
    return '\n'.join(lines)

class Prepared(unittest.TestCase):
    def test_original_pins_and_manifest_regeneration(self):
        self.assertEqual(P.prepare(),json.loads((P.OUT/P.PROPOSAL).read_text()))
    def test_native_matrix_connections_unchanged(self):
        parent=P.blob('e6cac61a773b81075e924d911c9e354b08ab4c7a','rtl/test/hbm_connected_service/tb_connected_matrix_service.sv').decode()
        new=(R/'rtl/test/hbm_rf_visibility/tb_connected_rf_visibility.sv').read_text()
        def matrix(s):return s[s.index(' generate if(QWEN)'):s.index(' // Test HBM')]
        self.assertEqual(matrix(parent),matrix(new))
        self.assertIn('ot_gpu_matrix_capture_audit #(.ENABLE(1),.NC(NC))',new)
    def test_model_control_geometry_default_off(self):
        m=json.loads((P.OUT/'model_capture_adapter_before_RTL.json').read_text())
        self.assertEqual(m['total_state_bits'],51);self.assertEqual(m['payload_buffer_bits'],0)
        self.assertEqual(m['SIMD_lanes'],128);self.assertEqual(m['RF_read_copies'],2)
        s=(R/'rtl/gpu/ot_gpu_rf_visibility_fence.sv').read_text()
        self.assertIn('parameter integer ENABLE=0',s);self.assertIn('cap_addr==issued[8:0]',s)
    def test_synthetic_DS_Qwen_trace_accept(self):
        for q in (0,1):self.assertEqual(len(T.check(synthetic(q))['cases']),4)
    def test_synthetic_alias_rejected(self):
        with self.assertRaises(ValueError):T.check(synthetic().replace('a=0 b=0 dst=0','a=1 b=0 dst=0',1))
    def test_synthetic_premature_fence_rejected(self):
        s=synthetic().replace('name=RF_fence_valid cycle=9','name=RF_fence_valid cycle=1',1)
        with self.assertRaises(ValueError):T.check(s)
    def test_synthetic_missing_reset_rejected(self):
        with self.assertRaises(ValueError):T.check(synthetic().replace('RESET_RF_FENCE_PASS','UNTESTED_RESET'))
    def test_synthetic_host_overwrite_rejected(self):
        s=synthetic().replace('RF_VECTOR_WRITE case=1 index=0 epoch=1 cycle=3','RF_VECTOR_WRITE case=1 index=0 epoch=1 cycle=30')
        with self.assertRaises(ValueError):T.check(s)
    def test_synthetic_early_second_pass_rejected(self):
        s=synthetic().replace('SIMD_ALIAS_ACCEPT case=1 pass=1 index=0 a=0 b=0 dst=0 cycle=64','SIMD_ALIAS_ACCEPT case=1 pass=1 index=0 a=0 b=0 dst=0 cycle=30')
        with self.assertRaises(ValueError):T.check(s)
if __name__=='__main__':unittest.main(verbosity=2)
