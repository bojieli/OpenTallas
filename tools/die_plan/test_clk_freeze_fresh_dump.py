import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent

class FreshDump(unittest.TestCase):
    def vehicle(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);d=Path(t.name)
        b=d/'run/results/asap7/x/base';b.mkdir(parents=True)
        (b/'6_final.odb').write_text('fixture')
        table='NET\tclkA\tCLOCK\t3\t64\t0:M3 4:100 4:200\nPIN\tclkA\tbuf/Y ff/CLK\nINST\tbuf\tBUFx4\t10\t20\tR0\tLOCKED\n'
        for n in ['clk_freeze_pre.tsv','clk_freeze_post.tsv']:(b/n).write_text(table)
        (d/'fresh.tsv').write_text(table);(d/'clk_geom_diff.json').write_text('{"verdict":"PASS","stale":true}')
        for n in ['clk_freeze.tcl','clk_dump_db.tcl','clk_geom_diff.py']:shutil.copyfile(HERE/n,d/n)
        bindir=d/'bin';bindir.mkdir();mock=bindir/'docker'
        mock.write_text('''#!/usr/bin/env python3
import os,sys,shutil
from pathlib import Path
a=sys.argv[1:]
if a[0]=='ps':sys.exit(0)
if 'chown' in a:sys.exit(0)
if os.environ['MOCK_DUMP']=='fail':sys.exit(17)
if os.environ['MOCK_DUMP']=='empty':sys.exit(0)
d=Path(os.environ['MOCK_KIT']);out=next(v for v in a if v.startswith('OT_OUT=')).split('=',1)[1]
shutil.copyfile(d/'fresh.tsv',d/out.removeprefix('/work/'))
''');mock.chmod(0o755)
        return d,b,dict(os.environ,PATH=str(bindir)+':'+os.environ['PATH'],MOCK_KIT=str(d))

    def test_failed_dump_cannot_reuse_stale_pass(self):
        d,b,env=self.vehicle();env['MOCK_DUMP']='fail'
        p=subprocess.run(['bash',str(HERE/'clk_freeze_check.sh'),str(d)],env=env,capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertIn('fresh dump failed rc=17',p.stdout)
        self.assertFalse((b/'clk_freeze_post.tsv').exists());self.assertFalse((d/'clk_geom_diff.json').exists())
        self.assertEqual(len(list(b.glob('clk_freeze_post.tsv.previous.*'))),1)
        self.assertEqual(len(list(d.glob('clk_geom_diff.json.previous.*'))),1)

    def test_successful_fresh_dump_passes(self):
        d,b,env=self.vehicle();env['MOCK_DUMP']='pass'
        p=subprocess.run(['bash',str(HERE/'clk_freeze_check.sh'),str(d)],env=env,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertIn('CLK_GEOM_DIFF PASS',p.stdout)
        self.assertNotIn('stale',(d/'clk_geom_diff.json').read_text())

    def test_zero_exit_without_fresh_output_fails(self):
        d,b,env=self.vehicle();env['MOCK_DUMP']='empty'
        p=subprocess.run(['bash',str(HERE/'clk_freeze_check.sh'),str(d)],env=env,capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertFalse((d/'clk_geom_diff.json').exists())

if __name__=='__main__':unittest.main()
