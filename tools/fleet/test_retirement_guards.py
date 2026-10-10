"""Retirement safety checks with no host scans or process signaling."""
import ast
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

SOURCE=Path(__file__).with_name('host_review_48h.py')
namespace=dict(os=os,Path=Path,cutoff=time.time()-48*3600)
functions=[n for n in ast.parse(SOURCE.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('overlap','process_guard')]
exec(compile(ast.Module(body=functions,type_ignores=[]),str(SOURCE),'exec'),namespace)
guard=namespace['process_guard']

class RetirementGuards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name);self.row=dict(pid=123,start='900',cwd=str(self.base))
        self.approvals=[dict(pid=123,start='900')]

    def test_age_alone_and_reused_pid_are_not_approved(self):
        self.assertIn('review required',guard(self.row,[],set()))
        self.assertIn('review required',guard(self.row,[dict(pid=123,start='899')],set()))

    def test_keep_in_ancestor_or_descendant_protects(self):
        (self.base/'.keep').touch()
        self.assertEqual(guard(self.row,self.approvals,set()),'.keep')
        (self.base/'.keep').unlink();(self.base/'sub').mkdir();(self.base/'sub/.keep').touch()
        self.assertEqual(guard(self.row,self.approvals,set()),'.keep')

    def test_active_pinned_source_and_fd_dependency_protect(self):
        self.assertIn('pinned',guard(self.row,self.approvals,{str(self.base)}))
        self.assertIn('dependency',guard(self.row,self.approvals,{'/source/job'},['/source/job/model.v']))

    def test_source_evidence_and_progress_outputs_protect(self):
        for filename in ('model.sv','SOURCE_COMMIT','failure.json','recent.log'):
            p=self.base/filename;p.touch()
            self.assertIsNotNone(guard(self.row,self.approvals,set()),filename)
            p.unlink()

    def test_explicit_old_empty_unit_is_eligible(self):
        self.assertIsNone(guard(self.row,self.approvals,set()))

    def test_help_exits_before_review_and_unknown_option_fails(self):
        script=SOURCE.with_name('hourly_review_48h.py')
        r=subprocess.run(['python3',str(script),'--help'],capture_output=True,text=True)
        self.assertEqual(r.returncode,0);self.assertNotIn('AUDIT ',r.stdout)
        r=subprocess.run(['python3',str(script),'--bogus'],capture_output=True,text=True)
        self.assertEqual(r.returncode,2);self.assertNotIn('AUDIT ',r.stdout)

if __name__=='__main__':unittest.main()
