import sys,copy
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[2])]
import ref_tile as RT

def leaf():
 return RT.track_macro('physical/ref_tile/qfd_tile_lsl_fp1/views/ot_qwen_tile_lsl_fp1')

def test_real_closed_lsl_best_pin_shape_rechecked():
 b={'view':'physical/ref_tile/qfd_tile_lsl_fp1/views/ot_qwen_tile_lsl_fp1','orient':'MY','_tm':leaf()}
 x,y,off=RT.on_track(b,103.68,330.48)
 actual=RT.cmta.check_placement(b['_tm'],'MY',round(x*1000),round(y*1000))
 assert off==sum(v['offtrack']for v in actual['layers'].values())==0
 assert actual['layers']['M4']['pins']==241 and actual['layers']['M6']['pins']==224

def test_conflicting_pin_without_any_access_shape_still_rejected():
 tm=copy.deepcopy(leaf())
 # A new pin one nanometre away from an existing M4 pin has no common legal
 # origin with it. This must remain a rejection rather than a blanket waiver.
 p=next(p for p in tm['pins']if p['use']=='SIGNAL' and any(l=='M4'for l,_ in p['rects']))
 bad=copy.deepcopy(p);bad['name']='actual_negative_guard'
 bad['rects']=[(l,(a,b+1,c,d+1))for l,(a,b,c,d)in p['rects']if l=='M4']
 tm['pins'].append(bad)
 b={'view':'unused','orient':'MY','_tm':tm}
 x,y,off=RT.on_track(b,103.68,330.48)
 assert off>0
