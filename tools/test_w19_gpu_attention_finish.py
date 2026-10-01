import ast
from pathlib import Path
import unittest
from w19_gpu_attention_finish import build,calendar,ins,exp_program,profile,inverse_rope


class AttentionFinish(unittest.TestCase):
    def test_actual_forty_bindings_and_no_complete_claim(self):
        b=build();self.assertEqual(len(b['source_graph_binding']),40)
        self.assertFalse(b['physical_qualified']);self.assertIsNone(b['full_token_cycles'])
        for p in b['profiles']:self.assertIsNone(p['full_attention_cycles'])

    def test_producer_rounding_supported_by_source(self):
        src=Path(__file__).resolve().parent/'hdc_golden_v41.py'
        f={n.name:n for n in ast.parse(src.read_text()).body if isinstance(n,ast.FunctionDef)}
        for fn in ['linear_q','qdq_fp8','qdq_fp4_e4m3']:
            returns=[n for n in ast.walk(f[fn]) if isinstance(n,ast.Return)]
            self.assertEqual(returns[-1].value.func.id,'to_bf16')
        dots=f['dots'];calls=[n.func.id for n in ast.walk(dots) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertNotIn('to_bf16',calls)

    def test_exp_exact_primitive_count_and_scale(self):
        p=exp_program()
        self.assertEqual(sum(i['op']=='FMUL' for i in p),9)
        self.assertEqual(sum(i['op']=='FADD' for i in p),10)
        self.assertEqual([i['op'] for i in p[-3:]],['F2I','SHL','IADD'])
        self.assertEqual(p[-1]['src'],['p','delta'])
        self.assertFalse(any(i['op'] in ['FMA','EXP'] for i in p))

    def test_division_lane_serialization_is_real_cost(self):
        p=[ins('LOAD','a'),ins('LOAD','b'),ins('DIV','x',['a','b'])]
        one=calendar(p,1);sixteen=calendar(p,16)
        self.assertEqual(sixteen['cycles']-one['cycles'],15)
        with self.assertRaises(ValueError):calendar(p,33)
        with self.assertRaisesRegex(ValueError,'arity'):calendar([ins('FADD','x',['@ZERO'])],1)
        with self.assertRaisesRegex(ValueError,'unknown'):calendar([ins('FADD','x',['@ZERO','@UNKNOWN'])],1)

    def test_denominator_retains_unrounded_exp_and_sink(self):
        for n in [128,640]:
            p=profile(n);r=p['recipes']
            self.assertEqual(sum(i['op']=='FADD' for i in r['den_local']),8 if n==128 else 35)
            self.assertEqual(r['den_local'][1]['src'][0],'@ZERO')
            add=r['sink_den'][-2];self.assertEqual(add['src'],['den','e'])
            self.assertEqual(r['output_div_bf16'][2]['src'],['pv','den'])
            phases={e['phase']:e['wait'] for e in p['events']}
            self.assertIn('actual positioncos/sin available',phases['inverse_rope'])
            self.assertIn('allconsumercompletion/fences acknowledged',phases['WOA_activation_publish'])

    def test_rope_conjugate_and_two_rounding_points(self):
        p=inverse_rope();adds=[i['src'] for i in p if i['op']=='FADD']
        self.assertEqual(adds,[['ac','bs'],['bc','negas']])
        self.assertEqual([i['src'] for i in p if i['op']=='XOR'],[['as','@SIGN']])
        self.assertEqual([i['attributes']['source_bits'] for i in p if i['op']=='STORE16'],['31:16','31:16'])

    def test_rf_ports_fullshape_limits(self):
        for p in build()['profiles']:
            for c in p['calendars'].values():
                self.assertLessEqual(c['peak_live_value_registers']+c['address_loop_registers'],32)
                self.assertEqual(c['RF_read_ports'],2);self.assertEqual(c['RF_write_ports'],1)
                self.assertGreaterEqual(c['cycles'],c['shared_issue_cycles'])


if __name__=='__main__':unittest.main()
