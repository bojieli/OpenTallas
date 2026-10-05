import unittest
from tools.w10_liberty_event_energy import events,parse_when,truth

class EventEnergyTest(unittest.TestCase):
    def test_mutually_exclusive_states_not_summed(self):
        s='''cell (c) { pin (A) { direction : input;
        internal_power () { related_pg_pin : VDD; when : "B";
        rise_power (s) { values ("3"); } fall_power (s) { values ("2"); } }
        internal_power () { related_pg_pin : VDD; when : "!B";
        rise_power (s) { values ("4"); } fall_power (s) { values ("1"); } } } }'''
        x=events(s,'c')
        self.assertEqual(x['event_cycle_fJ']['A'],'6')
        self.assertEqual(x['compatible_arc_proof'][0]['maximum_compatible_arcs'],1)
    def test_overlapping_conditions_are_summed(self):
        s='''cell (c) { pin (A) { direction : input;
        internal_power () { when : "B"; rise_power (s) { values ("3"); } fall_power (s) { values ("2"); } }
        internal_power () { when : "B + C"; rise_power (s) { values ("4"); } fall_power (s) { values ("1"); } } } }'''
        self.assertEqual(events(s,'c')['event_cycle_fJ']['A'],'10')
    def test_disabled_gate_keeps_input_cost(self):
        s='''cell (c) { pin (CLK) { direction : input;
        internal_power () { when : "!ENA"; rise_power (s) { values ("1"); } fall_power (s) { values ("2"); } } }
        pin (GCLK) { direction : output;
        internal_power () { related_pin : "CLK"; when : "ENA";
        rise_power (s) { values ("8"); } fall_power (s) { values ("9"); } } } }'''
        self.assertEqual(events(s,'c',{'ENA':False})['event_cycle_fJ']['CLK'],'3')
    def test_unsupported_condition_fails_closed(self):
        with self.assertRaises(ValueError):parse_when('f(A)')
    def test_boolean_protocol(self):
        self.assertTrue(truth(parse_when('(ENA) + (!ENA * SE)'),{'ENA':False,'SE':True}))
        self.assertFalse(truth(parse_when('(ENA) + (!ENA * SE)'),{'ENA':False,'SE':False}))
if __name__=='__main__':unittest.main()
