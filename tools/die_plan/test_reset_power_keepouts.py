import reset_tree as RT


def test_reset_relay_sites_follow_type_clock_power_keepout():
    t={'outline_um':[1000,1000], 'clock':{'keepouts_um':[[0,0,600,600]]}}
    boxes=RT.blockages(t)
    assert boxes==[(-8.64,-8.64,608.64,608.64)]
    tree=RT.build([('tap',100,100),('other',850,850)],(850,100),boxes=boxes,
                  box_out=(4.32,4.32,995.68,995.68))
    assert tree['max_hop_um']<=405
    for relay in tree['relays']:
        x,y=relay['xy']
        assert not any(a<x<c and b<y<d for a,b,c,d in boxes)
    assert tree['tap_offset_um']>0


def test_unmodified_types_keep_their_macro_only_blockages():
    t={'outline_um':[1000,1000], 'hard_cores':[{'origin_um':[100,100],'outline_um':[200,300]}]}
    assert RT.blockages(t)==[(95.68,95.68,304.32,404.32)]
