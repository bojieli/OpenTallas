import re,unittest
from pathlib import Path
import kit_wave as KW
class WorkerReceipt(unittest.TestCase):
    def pattern(self):
        # Exercise the production pattern embedded in run_item, not a mirrored parser.
        import inspect,ast
        fn=ast.parse(inspect.getsource(KW.run_item))
        assign=next(n for n in ast.walk(fn) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="ran" for t in n.targets))
        return ast.literal_eval(assign.value.args[0])
    def test_actual_unit_receipt_identifies_pull_host(self):
        txt="ot-run: -> epyc2\not-run: RAN on epyc2 (unit oth-ubuntu-2331435-1793357989): exit 0\n"
        self.assertEqual(re.findall(self.pattern(),txt),["epyc2"])
    def test_legacy_receipt_and_no_receipt(self):
        self.assertEqual(re.findall(self.pattern(),"ot-run: RAN on localhost: exit 0\n"),["localhost"])
        self.assertEqual(re.findall(self.pattern(),"ot-run: -> epyc2\not-run: NOT RUN on epyc2\n"),[])
if __name__=="__main__":unittest.main()
