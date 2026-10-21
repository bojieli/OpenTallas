import copy
import os
import unittest
from unittest.mock import patch
from qwen_split.clock_follow_port import apply


class ClockFollowPort(unittest.TestCase):
    def scene(self):
        return ({'ck_follow':{('flt_tt','ck'):'tt_ctlm'},
                 'ck_follow_port':{('flt_tt','ck'):('tt_ctlm','ck_hr')}},
                {1:[('tt_ctlm','ck_core'),('flt_tt','ck')],
                 2:[('tt_ctlm','ck_hr')],3:[('native59','ck')]})

    def test_default_without_map_is_exact_identity(self):
        model,per=self.scene();model.pop('ck_follow_port');old=copy.deepcopy(per);record={}
        with patch.dict(os.environ,{'OT_SPLIT_CK_FOLLOW_PORT':'0'}):self.assertEqual(apply(model,per,record),0)
        self.assertEqual(per,old);self.assertEqual(record,{})

    def test_default_rejects_requested_map(self):
        model,per=self.scene()
        with patch.dict(os.environ,{'OT_SPLIT_CK_FOLLOW_PORT':'0'}):
            with self.assertRaisesRegex(ValueError,'disabled'):apply(model,per,{})

    def test_multiclock_follower_uses_exact_hr_port(self):
        model,per=self.scene();record={}
        with patch.dict(os.environ,{'OT_SPLIT_CK_FOLLOW_PORT':'1'}):self.assertEqual(apply(model,per,record),1)
        self.assertNotIn(('flt_tt','ck'),per[1]);self.assertIn(('flt_tt','ck'),per[2])
        self.assertEqual(per[1],[('tt_ctlm','ck_core')]);self.assertEqual(record['follow_port'][0]['owner'],['tt_ctlm','ck_hr'])

    def rejected(self,edit,message):
        model,per=self.scene();edit(model,per);before=copy.deepcopy(per)
        with patch.dict(os.environ,{'OT_SPLIT_CK_FOLLOW_PORT':'1'}):
            with self.assertRaisesRegex(ValueError,message):apply(model,per,{})
        self.assertEqual(per,before)

    def test_wrong_instance_owner_rejected(self):
        self.rejected(lambda m,p:m['ck_follow_port'].update({('flt_tt','ck'):('native59','ck')}),'instance owner')

    def test_missing_owner_port_rejected(self):
        self.rejected(lambda m,p:m['ck_follow_port'].update({('flt_tt','ck'):('tt_ctlm','missing')}),'one actual region')

    def test_missing_follower_rejected(self):
        self.rejected(lambda m,p:p[1].remove(('flt_tt','ck')),'one actual region')

    def test_duplicate_clock_assignment_rejected(self):
        self.rejected(lambda m,p:p[3].append(('tt_ctlm','ck_hr')),'one actual region')

    def test_owner_follower_rejected(self):
        self.rejected(lambda m,p:m['ck_follow'].update({('tt_ctlm','ck_hr'):'native59'}),'real terminal')

    def production_generator(self,explicit):
        # Run the actual committed generator function, without importing the
        # rest of its design-construction dependencies or starting a build.
        import ast
        from pathlib import Path
        from types import SimpleNamespace
        source=Path(__file__).resolve().parents[1]/'qwen_rom_fulldie_b3r2.py'
        node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='_gen16_clock_refile')
        env={'os':os,'REP_SEG_MM':1.0}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),env)
        model,per=self.scene();model['b3r2']={}
        if not explicit:model.pop('ck_follow_port')
        by={i:SimpleNamespace(master='real_'+i) for endpoints in per.values() for i,p in endpoints}
        flags={'OT_SPLIT_CK_FOLLOW_PORT':'1' if explicit else '0',
               'OT_SPLIT_CK_COROOT':'','OT_SPLIT_REGION_ONE_HARD':'0','OT_SPLIT_RST_REGION_LAND':'0'}
        with patch.dict(os.environ,flags):env['_gen16_clock_refile'](model,[],by,per)
        return model,per

    def test_actual_generator_default_preserves_legacy_instance_root(self):
        model,per=self.production_generator(False)
        self.assertIn(('flt_tt','ck'),per[1]);self.assertNotIn(('flt_tt','ck'),per[2])
        self.assertNotIn('follow_port',model['b3r2']['gen16_clock_refile'])

    def test_actual_generator_port_override_runs_after_legacy_follow(self):
        model,per=self.production_generator(True)
        self.assertNotIn(('flt_tt','ck'),per[1]);self.assertIn(('flt_tt','ck'),per[2])
        self.assertEqual(model['ck_follow'],{('flt_tt','ck'):'tt_ctlm'})


if __name__=='__main__':unittest.main()
