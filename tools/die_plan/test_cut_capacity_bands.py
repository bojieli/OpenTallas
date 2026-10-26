"""Cut lower bounds must count declared OBS and reserved FT tracks together."""
import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check import cut_interval_tracks

class CutCapacity(unittest.TestCase):
 def test_band_through_union_of_cores(self):
  # [0,20] and[70,100] at1/4, [60,70] at1; [20,60] blocked.
  self.assertAlmostEqual(cut_interval_tracks(0,100,1,.25,[(20,40),(35,60)],[(30,70,1)]),22.5)
 def test_overlapping_bands_not_summed_and_lower_share_is_respected(self):
  self.assertAlmostEqual(cut_interval_tracks(0,100,1,.25,[],[(20,60,.5),(40,80,1)]),60)
  self.assertAlmostEqual(cut_interval_tracks(0,100,1,.5,[],[(20,80,.25)]),35)
 def test_empty_and_clipped_intervals(self):
  self.assertAlmostEqual(cut_interval_tracks(0,100,2,.25,[(-10,20),(80,120)],[]),7.5)
  self.assertEqual(cut_interval_tracks(0,100,1,.25,[(0,100)],[(0,100,1)]),0)
 def test_mirrored_macro_ceiling_and_band_use_route_rectangles(self):
  from die_trial import die_core_rects,ft_band_rects
  p=SimpleNamespace(parts={'p':dict(type='t',origin_um=[100,200],orient='MY')},
     types={'t':dict(outline_um=[100,80],hard_cores=[dict(origin_um=[10,10],outline_um=[20,30],obs_max='M5')],
                    die_ft_bands=[dict(dir='NS',span_um=[10,30],layers=['M7'],die_share=1)])},
     layer_budget={'partition_signal_max':'M7'})
  self.assertEqual(die_core_rects(p,'M4'),[(170,210,190,240)])
  self.assertEqual(die_core_rects(p,'M6'),[])
  self.assertEqual(ft_band_rects(p),[('M7',170,200,190,280,1.0)])
  m4=cut_interval_tracks(100,200,1,.25,[(170,190)],[])
  m7=cut_interval_tracks(100,200,1,.25,[],[(170,190,1)])
  self.assertEqual(m4+m7,60)
if __name__=='__main__':unittest.main()
