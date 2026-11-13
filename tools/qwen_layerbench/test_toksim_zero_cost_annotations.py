"""The priced ledger may describe overlapping work outside the serial layer model."""
import unittest
import toksim_compose as T

class ZeroCostAnnotations(unittest.TestCase):
    def test_supported_rows_and_overlapped_metadata(self):
        known={'label':'landing','cycles':3,'at':['pre_qkv']}
        annotations=[{'label':'ARF','cycles':0,'at':['o_ar','down_ar','lm_arx']},
                     {'label':'RoPE','cycles':0,'cycles_per_token':24,'at':['token_start']}]
        ledger={'edges':[known]+annotations}
        self.assertEqual(T.die_edge_map(ledger),T.die_edge_map({'edges':[known]}))
        self.assertEqual(ledger['edges'][2]['cycles_per_token'],24)

    def test_unrepresented_charged_boundary_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'charged edge at unknown boundary'):
            T.die_edge_map({'edges':[{'label':'bad','cycles':1,'at':['token_start']}]})

    def test_selected_variant_cost_cannot_be_discarded(self):
        row={'label':'variant','cycles':0,'cycles_plan':1,'at':['token_start']}
        self.assertEqual(T.die_edge_map({'edges':[row]}),{})
        with self.assertRaisesRegex(ValueError,'charged edge at unknown boundary'):
            T.die_edge_map({'edges':[row]},'plan')

if __name__=='__main__':unittest.main()
