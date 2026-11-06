import subprocess
import unittest
from kit_epoch_observability import inspect
from kit_istations import EXACT_BANK_TCL

class EpochObservability(unittest.TestCase):
    def test_epoch_chain_and_observed_mutant(self):
        text='''module m(input wire clk, input wire rst_n, output wire result);
wire e0; wire e1;
ot_dp_st #(.W(2)) first (.ea(input_epoch), .eq(e0));
ot_dp_st #(.W(2)) second (.ea(e0), .eq(e1));
endmodule'''
        self.assertTrue(inspect(text,'first')['unobserved'])
        self.assertFalse(inspect(text.replace('endmodule','assign result = e1; endmodule'),'first')['unobserved'])
        self.assertFalse(inspect(text.replace('endmodule','payload u(.d(e1)); endmodule'),'first')['unobserved'])

    def test_runtime_requires_every_payload_and_observed_epoch(self):
        body=EXACT_BANK_TCL[EXACT_BANK_TCL.rfind('  for {set bit 0}'):].strip()
        body=body[:-1]  # close of is_exact_bank, not part of the validator
        script='proc check {seen epoch_unobserved} {set W 2;set inst demo;\n'+body+'\n}\n'
        for seen,allow,expected in [('{0 1 1 1}',1,0),('{0 1 1 1}',0,1),('{0 1 2 1}',1,1),('{0 1 1 1 2 1}',0,0)]:
            run=subprocess.run(['tclsh'],input=script+f'puts "RESULT:[catch {{check {seen} {allow}}} msg]"\n',text=True,capture_output=True,check=True)
            self.assertIn('RESULT:'+str(expected),run.stdout,run.stdout+run.stderr)

if __name__=='__main__':unittest.main()
