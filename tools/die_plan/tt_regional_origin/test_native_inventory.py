"""Clock-path facts must come from actual Liberty function polarity, not master-name heuristics."""
import unittest
from native_inventory import primitive_clock,path_function


class ActualLibClockFacts(unittest.TestCase):
    def test_ff_clock_edges(self):
        self.assertEqual(primitive_clock('CLK'),('CLK',1))
        self.assertEqual(primitive_clock('!CLK'),('CLK',-1))
        with self.assertRaises(ValueError):primitive_clock('CLK & OTHER_CLOCK')

    def cell(self,function):
        return dict(name='LIB_ACTUAL',pins={'A':dict(direction='input'), 'Y':dict(direction='output',function=function)})

    def test_buffer_and_inverter_functions(self):
        self.assertEqual(path_function(self.cell('A'),'Y',set())[1:3],(1,'buffer'))
        self.assertEqual(path_function(self.cell('!A'),'Y',set())[1:3],(-1,'inverter'))

    def gate(self,function):
        return dict(name='LIB_GATE',pins={'CLK':dict(direction='input',clock=True),'EN':dict(direction='input'),'Y':dict(direction='output',function=function)})

    def test_typed_clock_gate_polarity(self):
        self.assertEqual(path_function(self.gate('CLK & EN'),'Y',set())[1:3],(1,'clock_gate'))
        self.assertEqual(path_function(self.gate('!(CLK & EN)'),'Y',set())[1:3],(-1,'clock_gate'))

    def test_phase_selecting_clock_logic_is_rejected(self):
        with self.assertRaises(ValueError):path_function(self.gate('CLK ^ EN'),'Y',set())


if __name__=='__main__':unittest.main()
