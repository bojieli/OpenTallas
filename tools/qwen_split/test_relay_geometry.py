import json
from pathlib import Path
from types import SimpleNamespace as S
import unittest
from qwen_split.relay_geometry import rebuild

class ActualRepackGeometry(unittest.TestCase):
    def model(self):
        p=Path(__file__).resolve().parents[2]/'results/arch/qwen_split_compute_1014/repack_2210/fpq_r2f-homes.json'
        h=json.loads(p.read_text())
        insts=[S(name=n,master=q['m'],x=q['x'],y=q['y'],w=q['w'],h=q['h'],orient=q['o']) for n,q in h['homes'].items()]
        m=dict(insts=insts,geo=dict(row_y=[999],y0=999,y_io=999),die=h['die'],
               col_x=lambda c:999,corridor_lanes=[(999,1)],
               regions=[dict(kind='tile_field',rect=[0,0,1,1]),dict(kind='tile_field',rect=[2,0,3,1])])
        return S(),m
    def test_all_768_actual_homes_replace_stale_search_grid(self):
        v,m=self.model();r=rebuild(v,m)
        self.assertEqual((v.COLS,v.ROWS,r['actual_tiles']),(48,16,768))
        self.assertAlmostEqual(v.CORR,64.8)
        self.assertAlmostEqual(v.TILE_SLOT[1],820.8)
        self.assertAlmostEqual(m['col_x'](0),21.6)
        self.assertAlmostEqual(m['corridor_lanes'][0][0],479.52)
        self.assertEqual(len(m['geo']['row_y']),16)
        self.assertEqual(m['geo']['y_io'],m['die']['h'])
    def test_bad_station_and_staggered_grid_fail_closed(self):
        v,m=self.model();next(i for i in m['insts'] if i.name=='s_0_0').x+=1
        with self.assertRaisesRegex(ValueError,'station'):rebuild(v,m)
        v,m=self.model();next(i for i in m['insts'] if i.name=='t_0_1').x+=1
        with self.assertRaisesRegex(ValueError,'staggered'):rebuild(v,m)

if __name__=='__main__':unittest.main()
