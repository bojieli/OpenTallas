import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from lec_completed_transfer import transfer, identity


class CompletedTransferTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.k=Path(self.temp.name)/'donor'; self.k.mkdir(); (self.k/'rtl').mkdir(); (self.k/'lec').mkdir()
        rows={'config.mk':'export VERILOG_FILES = /work/rtl/top.v\nexport VERILOG_DEFINES = EXACT=1\n',
              'freeze.json':'{"schema":"frozen.v1"}', 'core.json':'{"ports":[]}',
              'lec.py':'# original proof driver\n','rtl/top.v':'module top;endmodule\n',
              'net.v':'module top;endmodule\n', 'reset_contract.json':'{"reset_cycles":64}',
              'lec_async.ready':'1\npython3 /work/lec.py --netlist /work/net.v\n'}
        for n,v in rows.items(): (self.k/n).write_text(v)
        (self.k/'lec_async.source_identity').write_text(identity(self.k,'source')+'\n')
        (self.k/'lec_async.identity').write_text(identity(self.k)+'\n')
        (self.k/'lec/lec.json').write_text(json.dumps({'verdict':'EQUIVALENT','netlist':'/work/net.v','counts':{'proved':17}}))
        (self.k/'lec_async.rc').write_text('0\n'); (self.k/'lec_async.done').touch()
        (self.k/'image.txt').write_text('OOMKilled=true\nend 2026-11-06 rc 2\n')
        (self.k/'lec_async.pid').write_text('999999999')
        self.c=Path(self.temp.name)/'copy'; shutil.copytree(self.k,self.c)
        for n in ('lec_async.pid','lec_async.done','lec_async.ready','lec_async.rc','lec/lec.json'):
            (self.c/n).unlink()

    def test_completed_eq_from_oom_preserves_donor_and_imports_immutable_receipt(self):
        before={str(p.relative_to(self.k)):p.read_bytes() for p in self.k.rglob('*') if p.is_file()}
        r=transfer(self.k,self.c)
        self.assertTrue(r['historical_identity_available']); self.assertFalse(r['source_qualified'])
        self.assertEqual((self.c/'lec/lec.json').read_bytes(),(self.k/'lec/lec.json').read_bytes())
        self.assertFalse((self.c/'lec_async.pid').exists())
        self.assertEqual(before,{str(p.relative_to(self.k)):p.read_bytes() for p in self.k.rglob('*') if p.is_file()})
        self.assertEqual(r,transfer(self.k,self.c))

    def test_shell_import_marks_done_without_pid(self):
        subprocess.run(['bash',str(Path(__file__).with_name('lec_async.sh')),'import-completed',str(self.k),str(self.c)],check=True,capture_output=True)
        self.assertTrue((self.c/'lec_async.done').exists())
        self.assertFalse((self.c/'lec_async.pid').exists())
        self.assertEqual(identity(self.c),identity(self.k))

    def test_changed_input_reset_define_and_netlist_rejected(self):
        for name in ('rtl/top.v','reset_contract.json','config.mk','net.v'):
            old=(self.c/name).read_bytes(); (self.c/name).write_bytes(old+b' mutant')
            with self.assertRaisesRegex(ValueError,'differs'): transfer(self.k,self.c)
            (self.c/name).write_bytes(old)

    def test_incomplete_failed_or_unproven_rejected(self):
        (self.k/'lec_async.done').unlink()
        with self.assertRaisesRegex(ValueError,'not completed'): transfer(self.k,self.c)
        (self.k/'lec_async.done').touch(); (self.k/'lec_async.rc').write_text('1')
        with self.assertRaisesRegex(ValueError,'not completed'): transfer(self.k,self.c)
        (self.k/'lec_async.rc').write_text('0'); (self.k/'lec/lec.json').write_text('{"verdict":"UNDECIDED"}')
        with self.assertRaisesRegex(ValueError,'not completed'): transfer(self.k,self.c)

    def test_modified_donor_and_unknown_capture_rejected(self):
        old=(self.k/'rtl/top.v').read_bytes(); (self.k/'rtl/top.v').write_bytes(old+b' changed')
        (self.c/'rtl/top.v').write_bytes(old+b' changed')
        with self.assertRaisesRegex(ValueError,'differs'): transfer(self.k,self.c)

    def test_missing_capture_rejected(self):
        (self.k/'lec_async.identity').unlink()
        with self.assertRaisesRegex(ValueError,'identity absent'): transfer(self.k,self.c)

    def test_changed_omitted_legacy_metadata_rejected(self):
        (self.c/'core.json').write_text('{"ports":["reset"]}')
        with self.assertRaisesRegex(ValueError,'input differs'): transfer(self.k,self.c)


if __name__=='__main__': unittest.main()
