import unittest
from unittest.mock import patch
from test_autopilot import Base

class FlowChangesCache(Base):
    def test_exact_repeat_reuses_diff_but_moving_tag_and_config_do_not(self):
        diffs=[]; tag=['a'*40]
        def sh(cmd, **kw):
            if 'rev-parse' in cmd:return 0,tag[0],' '
            diffs.append(cmd)
            return 0,'tools/die_plan/signoff.py\nphysical/die_plan/s81/a.tcl\nphysical/die_plan/hbm/b.tcl\n',''
        with patch.object(self.ap,'sh',sh):
            args=('flow-tag','f'*40,['tools/*','physical/*'],[],['s81'])
            expected=(0,['tools/die_plan/signoff.py','physical/die_plan/s81/a.tcl'])
            self.assertEqual(self.ap.flow_changes(*args),expected)
            self.assertEqual(self.ap.flow_changes(*args),expected)
            self.assertEqual(len(diffs),1)
            tag[0]='b'*40
            self.assertEqual(self.ap.flow_changes(*args),expected)
            self.assertEqual(len(diffs),2)
            self.assertEqual(self.ap.flow_changes('flow-tag','f'*40,['tools/*'],[],['s81']), (0,['tools/die_plan/signoff.py']))
            self.assertEqual(len(diffs),3)
    def test_git_failure_is_not_cached(self):
        calls=[]
        def sh(cmd,**kw):
            if 'rev-parse' in cmd:return 0,'a'*40,''
            calls.append(cmd)
            return (1,'','error') if len(calls)==1 else (0,'tools/a.py','')
        with patch.object(self.ap,'sh',sh):
            self.assertEqual(self.ap.flow_changes('tag','f'*40,['tools/*'],[],None),(1,[]))
            self.assertEqual(self.ap.flow_changes('tag','f'*40,['tools/*'],[],None),(0,['tools/a.py']))
            self.assertEqual(len(calls),2)
if __name__=='__main__':unittest.main()
