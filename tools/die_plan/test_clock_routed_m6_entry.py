"""A real M6 jog must connect the fixed pin stack to a different M7 column."""
import pytest
import clock_routed as C

@pytest.mark.parametrize('backbone',[9.92,10.0,10.08])
def test_m6_entry_keeps_actual_pin_and_continuous_layer_path(backbone):
    s=dict(cell='inv0',pin='A',xy=[backbone,20.135],riser_from=[backbone,21.0],
           m6_entry_xy=[10.,20.135])
    pts=C.stack_down(s)
    assert pts[0]==('M8',backbone,21.)
    assert pts[-1]==('M1',10.,20.135)
    # No sideways M7 conductor crosses another fixed clock-bar column.
    assert all(not(a[0]==b[0]=='M7' and a[1]!=b[1]) for a,b in zip(pts,pts[1:]))
    for a,b in zip(pts,pts[1:]):
        if a[0]!=b[0]:
            assert a[1:]==b[1:]
            assert abs(int(a[0][1:])-int(b[0][1:]))==1
        else:
            assert a[1]==b[1] or a[2]==b[2]
    pads=C.stack_pad_layers(s)
    assert pads[(10.,20.135)] >= {'M2','M3','M4','M5','M6'}
    assert 'M6' in pads[(backbone,20.135)]
    if backbone!=10.:
        assert not({'M2','M3','M4','M5'} & pads[(backbone,20.135)])
        shapes=C.stack_shapes(dict(name='clk',stacks=[s]))
        assert any(layer=='M6' and x0<=min(backbone,10.)-.016+1e-8 and
                   x1>=max(backbone,10.)+.016-1e-8 for _,layer,x0,_,x1,_ in shapes)
    lines=[]
    C._emit_stack(lines,pts,pads,split_down=True)
    assert any('VIA67' in line for line in lines)
    assert any('VIA56' in line for line in lines)


def test_m6_entry_refuses_unmodeled_vertical_detour():
    s=dict(xy=[10.08,20.135],riser_from=[10.08,21.],m6_entry_xy=[10.,20.27])
    with pytest.raises(ValueError,match='actual pin row'):
        C.stack_down(s)
