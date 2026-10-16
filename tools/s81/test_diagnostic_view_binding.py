"""A diagnostic routed view never becomes qualified through a loader/cache reuse."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from test_view_binding import S,MST,lef,pins,table
class DiagnosticViews(unittest.TestCase):
 def test_explicit_diagnostic_scope_and_cache_separation(self):
  old=S.VIEW_BINDING
  try:
   with tempfile.TemporaryDirectory() as td:
    S.VIEW_BINDING=table(Path(td)/'view',lef(pins()),verdict='DIAGNOSTIC_CLOSED');S._BOUND.clear()
    with patch.dict(os.environ,{'OT_S81_DIAGNOSTIC_CLOSED_VIEWS':'0'}):
     with self.assertRaisesRegex(SystemExit,'without a QUALIFIED verdict'):S.bound_views()
    with patch.dict(os.environ,{'OT_S81_DIAGNOSTIC_CLOSED_VIEWS':'1'}):
     self.assertEqual(S.bound_views()[MST]['binding_scope'],'DIAGNOSTIC_CLOSED')
    with patch.dict(os.environ,{'OT_S81_DIAGNOSTIC_CLOSED_VIEWS':'0'}):
     with self.assertRaisesRegex(SystemExit,'without a QUALIFIED verdict'):S.bound_views()
  finally:S.VIEW_BINDING=old;S._BOUND.clear()
 def test_diagnostic_mode_keeps_hash_gate(self):
  old=S.VIEW_BINDING
  try:
   with tempfile.TemporaryDirectory() as td:
    S.VIEW_BINDING=table(Path(td)/'view',lef(pins()),verdict='DIAGNOSTIC_CLOSED',edit=True);S._BOUND.clear()
    with patch.dict(os.environ,{'OT_S81_DIAGNOSTIC_CLOSED_VIEWS':'1'}):
     with self.assertRaisesRegex(SystemExit,'sha256 differs'):S.bound_views()
  finally:S.VIEW_BINDING=old;S._BOUND.clear()
