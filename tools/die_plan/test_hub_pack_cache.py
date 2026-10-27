"""Shelf geometry cache must preserve placement, scoring, and caller isolation."""
import copy
import hub_repack as H


def cores():
 return [dict(inst=f'c{i}',w=43.2,h=43.2,ocx=80.0+(i%3)*55,ocy=80.0+(i//3)*60) for i in range(9)]


def test_exact_geometry_reuse_and_caller_isolation():
 H._pack_hub_geometry.cache_clear(); c=cores()
 expected=H._pack_hub_uncached(432,432,c)
 got=H.pack_hub(432,432,c)
 assert got==expected
 got[0]['c0']=(999,999); got[1]['streets']['horizontal_y_um'].append([9,9])
 assert H.pack_hub(432,432,copy.deepcopy(c))==expected
 assert H._pack_hub_geometry.cache_info().hits==1
 c[0]['w']=47.52
 assert H.pack_hub(432,432,c)==H._pack_hub_uncached(432,432,c)
 assert H._pack_hub_geometry.cache_info().misses==2


def test_connected_scoring_not_reused_from_geometry():
 H._pack_hub_geometry.cache_clear();c=cores()
 H.pack_hub(432,432,c)
 conns=[(('c0',0,0),('c8',0,0),0)]
 before=H._pack_hub_geometry.cache_info()
 assert H.pack_hub(432,432,c,conns=conns)==H._pack_hub_uncached(432,432,c,conns=conns)
 assert H._pack_hub_geometry.cache_info()==before
