import copy
import unittest
from unittest.mock import patch
import delta_station_controls_1713 as D

class Controls(unittest.TestCase):
    def test_start_physical_aliases_are_counted_once(self):
        T=dict(entry="relay",root=[1,2],start=True,start_in=[3,4])
        rel=[dict(name="u_rrl_a",xy=[5,6],role="gated"),dict(name="u_rrl_a_r",xy=[5,6],role="raw"),dict(name="u_srl_a",xy=[5,6],role="run")]
        with patch.object(D.RT,"start_relays",return_value=rel):s,r=D.census(T)
        self.assertEqual(s,[[1,2,1],[3,4,1],[5,6,3]])
        self.assertEqual(sum(r.values()),5)
        self.assertEqual(r["start_entry"],1)
        with patch.object(D.RT,"start_relays",return_value=rel+[rel[0]]):
            with self.assertRaisesRegex(ValueError,"duplicate"):D.census(T)
    def test_nonconvergence_does_not_mutate_input(self):
        raw=dict(partition_types=dict(t=dict(clock={})));saved=copy.deepcopy(raw)
        with patch.object(D.S,"Plan",return_value=None),patch.object(D.RT,"for_type",return_value={"depth":1}),patch.object(D.RT,"release_clocks",return_value=1),patch.object(D,"census",side_effect=[([[1,1,1]],{}),([[2,2,1]],{})]):
            with self.assertRaisesRegex(ValueError,"did not converge"):D.apply(raw,["t"],rounds=2,require_start=False)
        self.assertEqual(raw,saved)
    def test_absent_start_rejected_for_successor(self):
        raw=dict(partition_types=dict(t=dict(clock={})))
        with patch.object(D.S,"Plan",return_value=None),patch.object(D.RT,"for_type",return_value={}):
            with self.assertRaisesRegex(ValueError,"START broadcast is absent"):D.apply(raw,["t"])
    def test_root_requires_weighted_census(self):
        with self.assertRaisesRegex(ValueError,"root sync"):D.census(dict(entry="sync"))

if __name__=="__main__":unittest.main()
