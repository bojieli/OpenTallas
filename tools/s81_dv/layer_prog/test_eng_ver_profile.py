import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import lower_vs as V

class EngVerProfileTest(unittest.TestCase):
    def compile(self, params):
        die=types.SimpleNamespace(slices=lambda:{'s_0N':dict(params=params)})
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            rowmap=root/'results/arch/s81_dv_1016/eng/kv_rowmap.json'
            rowmap.parent.mkdir(parents=True)
            rowmap.write_text(json.dumps(dict(layers=dict(L14=dict(A0=128)))))
            with patch.object(V,'ROOT',root):
                return V.lower_eng(die,dict(op='eng.add',start=100),dict(layer='L14'),'s_0N',0)
    def test_selected_l1_response_moves_hload_and_preserves_add(self):
        old=self.compile(".LF_CS_VER_D(20'h00000)")
        new=self.compile(".LF_CS_VER_D(20'h00010)")
        self.assertEqual(new['rows'][0],old['rows'][0])
        self.assertEqual(new['templates'],old['templates'])
        self.assertEqual(new['rows'][1]['issue'],old['rows'][1]['issue']+1)
        self.assertEqual(new['source_profile']['response_edges'],[0,1,0,0,0])
        self.assertFalse(new['source_profile']['transport_included'])
        self.assertEqual(old['rows'][1]['issue']-100,V.ENG_ADD_DUR+V.GUARD)
    def test_legacy_and_non_eng_durations(self):
        self.assertEqual(self.compile('')['rows'],self.compile(".LF_CS_VER_D(20'h00000)")['rows'])
        self.assertEqual(V.VS_DUR['QB'](8),19)
        self.assertEqual(V.VS_DUR['RA'](6),147)
    def test_unresolved_depth_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'explicit'):
            self.compile('.LF_CS_VER_D(UNRESOLVED)')
        with self.assertRaisesRegex(ValueError,'exceeds'):
            self.compile(".LF_CS_VER_D(20'h100000)")

if __name__=='__main__':unittest.main()
