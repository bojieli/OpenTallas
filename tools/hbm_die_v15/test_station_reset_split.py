import contextlib,io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import die_relay_stations as s

class StationGrouping(unittest.TestCase):
 def test_hc_reset_cannot_suppress_same_sink_payload_stations(self):
  pl={'hc_NW':{'master':'ot_hbm_hc_qhub_static'},'hcb_NW6':{'master':'ot_hbm_hc_bankq_static'}}
  nets={};dirs={}
  for port in ['rstb_s','wc_s','xb_d7']:
   src=('hc_NW',port+'[0]',(0.0,0.0));dst=('hcb_NW6',port+'[0]',(13000.0,0.0))
   nets[port]=[src,dst];dirs[src[:2]]='OUTPUT';dirs[dst[:2]]='INPUT'
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);(r/'manifest.json').write_text(json.dumps({'die_um':[20200,31773.52]}));(r/'c.json').write_text('{}')
   args=['stations',td,'--contract',str(r/'c.json'),'--reach','405','--out',str(r/'stations.json')]
   with patch.object(s.RP,'load_case',return_value=(pl,nets,dirs,set())),patch('sys.argv',args),contextlib.redirect_stdout(io.StringIO()):s.main()
   result=json.loads((r/'stations.json').read_text())
   self.assertEqual(len(result['rows']),1)
   row=result['rows'][0];self.assertEqual(row['driver'],'hc_NW.wc_s+xb_d7');self.assertEqual(row['bits'],2)
   self.assertEqual(row['depth'],32);self.assertEqual(len(row['stations']),32)
   skipped=' '.join(x for xs in result['not_relayed'].values() for x in xs)
   self.assertIn('hc_NW.rstb_s',skipped);self.assertNotIn('wc_s',skipped);self.assertNotIn('xb_d7',skipped)

if __name__=='__main__':unittest.main()
