import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pinstack_odb import def_patches, near_pin  # noqa: E402


def test_uses_only_the_requested_signal_nets_and_routing_layers():
    text = r"""
SPECIALNETS 1 ;
    - bus\[0\]
      NEW M4 ( 40 50 ) RECT ( -2 -1 2 1 ) ;
END SPECIALNETS
NETS 2 ;
    - bus\[0\] ( PIN bus[0] ) + USE SIGNAL
      NEW M4 ( 190 300 ) RECT ( -53 -12 -20 12 )
      NEW M3 ( 190 300 ) RECT ( -1 -1 1 1 ) ;
    - unrelated ( PIN other ) + USE SIGNAL
      NEW M4 ( 190 300 ) RECT ( -1 -1 1 1 ) ;
END NETS
""".splitlines()
    assert dict(def_patches(text, {"bus[0]"})) == {"bus[0]": [("M4", 137, 288, 170, 312)]}


def test_window_limits_pin_stack_scope_without_changing_conductor_geometry():
    pins = [("M4", 0, 90, 24, 114)]
    assert near_pin(("M5", 100, 100, 950, 132), pins, 300)
    assert not near_pin(("M4", 400, 90, 950, 114), pins, 300)
