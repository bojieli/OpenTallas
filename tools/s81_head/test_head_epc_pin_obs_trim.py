"""The exact measured EPC abstract transform preserves pin and blanket geometry."""
from head_epc_pin_obs_trim import process, q


def test_touching_signal_obs_is_cut_but_pin_and_unrelated_metal_are_unchanged():
    source='''MACRO epc
  PIN out
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER M7 ;
      RECT 1 0 1.032 0.192 ;
    END
  END out
  OBS
    LAYER M7 ;
    RECT 1 0.192 1.032 0.8 ;
    RECT 4 4 5 5 ;
  END
END epc
'''
    result,stats=process(source.splitlines(keepends=True),q(.261))
    out=''.join(result)
    assert out.split('  OBS')[0]==source.split('  OBS')[0]
    assert 'RECT 1 0.453 1.032 0.8 ;' in out
    assert 'RECT 4 4 5 5 ;' in out
    assert stats[('epc','M7')]==[{'out'},1,1]


def test_blanket_obs_and_unselected_layers_stay_byte_identical():
    source='''MACRO epc
  PIN out
    PORT
      LAYER M7 ;
      RECT 1 0 1.032 0.192 ;
    END
  END out
  OBS
    LAYER M7 ;
    RECT 0 -1 4 4 ;
  END
END epc
'''
    result,stats=process(source.splitlines(keepends=True),q(.261))
    assert ''.join(result)==source and not stats
    source=source.replace('RECT 0 -1 4 4 ;','RECT 1 0.192 1.032 0.8 ;')
    result,stats=process(source.splitlines(keepends=True),q(.261),{'M6'})
    assert ''.join(result)==source and not stats
