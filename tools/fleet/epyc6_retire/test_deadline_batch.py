import importlib.util
import pathlib
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('batch', pathlib.Path(__file__).with_name('remote_deadline_batch.py'))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


class ExactBatch(unittest.TestCase):
    def records(self):
        return [dict(kind=k,id=i,expected=e) for k,i,e in [('unit','u1',11),('unit','u2',22),
                ('docker','container',('container','started')),('pid',101,1001),('pid',102,1002)]]

    def test_five_exact_targets_one_grace_and_reused_pid_refused(self):
        rows=self.records();ids={x['id']:x['expected'] for x in rows};events=[]
        def sleep(n):
            self.assertEqual(n,5);events.append(('grace',n));ids[102]=9999
        B.run_plan(rows,lambda x:ids.get(x['id']),lambda sig,xs:events.append((sig,[x['id'] for x in xs])),sleep)
        self.assertEqual(events,[('TERM',['u1','u2','container',101,102]),('grace',5),('KILL',['u1','u2','container',101])])

    def test_dry_run_never_sends_or_sleeps(self):
        rows=self.records()
        def forbidden(*a):self.fail('dry-run attempted mutation or sleep')
        out=B.run_plan(rows,lambda x:x['expected'],forbidden,forbidden,True)
        self.assertEqual(len(out['eligible']),5)

    def test_changed_unit_container_and_missing_identity_refused(self):
        rows=self.records();rows[-1]['expected']=None
        out=B.run_plan(rows,lambda x:'different' if x['kind']!='pid' else x['expected'],lambda *a:None,lambda n:None)
        self.assertEqual(out['term'],[rows[3]])
        self.assertEqual(len(out['refused']),4)

    def test_targets_never_expand_inventory_and_deduplicate(self):
        snap={'inventory':{'units':[{'unit':'u','cg_inode':11}], 'stale':[{'unit':'u','cg_inode':11}],
              'docker':[{'name':'c','id':'fullid','started_at':'stamp'}], 'procs':[{'pid':2,'start_ticks':22}]}}
        self.assertEqual(len(B.targets(snap)),3)
        self.assertEqual({x['id'] for x in B.targets(snap)},{'u','fullid',2})

    def test_worker_refuses_before_deadline_before_any_signal(self):
        snap={'deadline':'2026-10-21T14:15:00-07:00','at':'2026-10-21T14:15:01-07:00',
              'inventory':{'hostname':'ot-epyc6'}}
        due=B.datetime.datetime.fromisoformat(snap['deadline']).timestamp()
        with patch.object(B.os,'uname',return_value=SimpleNamespace(nodename='ot-epyc6')), patch.object(B.time,'time',return_value=due-1):
            with self.assertRaisesRegex(AssertionError,'before owner deadline'):B.execute(snap)

    def test_worker_refuses_old_partial_snapshot(self):
        snap={'deadline':'2026-10-21T14:15:00-07:00','at':'2026-10-21T14:14:59-07:00',
              'inventory':{'hostname':'ot-epyc6'}}
        due=B.datetime.datetime.fromisoformat(snap['deadline']).timestamp()
        with patch.object(B.os,'uname',return_value=SimpleNamespace(nodename='ot-epyc6')), patch.object(B.time,'time',return_value=due+1):
            with self.assertRaisesRegex(AssertionError,'old partial snapshot'):B.execute(snap)


if __name__=='__main__':unittest.main()
