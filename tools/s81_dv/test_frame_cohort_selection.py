import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=[str(Path(__file__).parent),str(Path(__file__).parent/'layer_prog')]
import lower_xs as X


class Cohorts(unittest.TestCase):
 def test_optin_instance_selection_and_mismatch(self):
  master='col_h10_l4_lp_asb_x'
  with tempfile.TemporaryDirectory() as root:
   d=Path(root);mp=d/'cohorts.json'
   mp.write_text(json.dumps(dict(schema='opentallas.s81.frame_cohort_map.v1',frames={'u_f_p1':'colrelay_p1'})))
   for suffix,meta in [('',{}),('__colrelay_p1',dict(frame_cohort='colrelay_p1',internal_visibility_profile={}))]:
    sp=d/(master+suffix+'_schedule.json');sp.write_text(json.dumps(meta))
    (d/(master+suffix+'_check.json')).write_text(json.dumps(dict(verdict='PASS',fails=[],schedule_sha256=hashlib.sha256(sp.read_bytes()).hexdigest())))
   with patch.dict(os.environ,{'OT_XS_ASB_SCHEDULE_DIR':root,'OT_XS_FRAME_COHORT_MAP':str(mp)}),patch.object(X,'qualify_frame_source',return_value=None),patch.object(X,'frame_manifest',return_value=(None,None)):
    self.assertEqual(X.source_frame_schedule(master,'u_f_p1').name,master+'__colrelay_p1_schedule.json')
    self.assertEqual(X.source_frame_schedule(master,'u_f_other').name,master+'_schedule.json')
    self.assertEqual(X.source_frame_schedule(master).name,master+'_schedule.json')
    sp=d/(master+'__colrelay_p1_schedule.json');sp.write_text(json.dumps(dict(frame_cohort='wrong',internal_visibility_profile={})))
    (d/(master+'__colrelay_p1_check.json')).write_text(json.dumps(dict(verdict='PASS',schedule_sha256=hashlib.sha256(sp.read_bytes()).hexdigest())))
    with self.assertRaisesRegex(ValueError,'cohort differs'):X.source_frame_schedule(master,'u_f_p1')


if __name__=='__main__':unittest.main()
