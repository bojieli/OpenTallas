"""C-CLK-LAND-OBS 11-27 (QC-R3-COLLS): a core tap at its own clock pin is the real entry for every core orientation.

QC live 77f2: 36 core taps on 17 cb* types sit on the MY NK tile's ck pin (plan clock_entry_access M5-M7); the old R0-only
own-pin test reported them as buried and clk_land_clear would have moved them off the pin."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_clk_land_obs as A  # noqa: E402
import clk_land_clear as C  # noqa: E402

W, H, OX, OY = 457.92, 1157.76, 86.4, 69.12
PIN_LEF = (100.0, 578.808, 100.072, 579.024)          # ck in the LEF macro frame (off-centre: MY moves it ~258 um)


def plan(tap, orient="MY", cea=True, lef="views_none/nk.lef"):
    hc = dict(inst="u_t02", module="nk", origin_um=[OX, OY], outline_um=[W, H], orient=orient, obs_max="M7", halo_um=2.16,
              lef=lef, track_offset_um=[0.0, 0.0])
    if cea:
        hc["clock_entry_access"] = {"pin": "ck", "footprints_um": {"M7": [[315.28, 647.628, 315.312, 648.396]],
                                                                    "M5": [[315.324, 647.877, 315.348, 648.036]]}}
    t = dict(outline_um=[1235.52, 2540.16], hard_cores=[hc],
             clock=dict(taps=[dict(name="u_t02.ck", kind="core", xy=list(tap))]), relay_sites={})
    return dict(die=dict(name="d", outline_um=[2000, 3000], layer_budget={"partition_signal_max": "M7"}),
                partition_types={"t": t}, partitions=[], ports=[], lanes=[])


class T(unittest.TestCase):
    def test_mirrored_core_tap_on_entry_access_is_not_a_hit(self):
        raw = plan((315.296, 648.012))
        self.assertEqual(A.counts(raw), {})
        types = copy.deepcopy(raw["partition_types"])
        led = C.apply(types, dict(raw, clk_land_clear={"enable": 1}))
        self.assertEqual(types["t"]["clock"]["taps"][0]["xy"], [315.296, 648.012])   # real entry not moved
        self.assertEqual(led, [])

    def test_buried_tap_in_mirrored_core_still_a_hit(self):
        raw = plan((200.0, 400.0))
        self.assertEqual(A.counts(raw)["t"]["by_cls"]["tap"]["body"], 1)

    def test_entry_access_of_other_pin_does_not_exempt(self):
        raw = plan((315.296, 648.012))
        raw["partition_types"]["t"]["hard_cores"][0]["clock_entry_access"]["pin"] = "ck2"
        self.assertEqual(A.counts(raw)["t"]["by_cls"]["tap"]["body"], 1)

    def test_lef_pin_placed_by_orientation(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "nk.lef").write_text("MACRO nk\n  PIN ck\n    PORT\n      LAYER M7 ;\n        RECT %s %s %s %s ;\n    END\n  END ck\nEND nk\n"
                                           % PIN_LEF)
            A._PIN.clear(), A._LEF_TOP.clear()
            mx = OX + (W - PIN_LEF[0]) - 0.036          # MY: x' = W - x
            raw = plan((mx, OY + 578.9), cea=False, lef="nk.lef")
            self.assertEqual(A.counts(raw, root=d), {})
            raw = plan((OX + PIN_LEF[0], OY + 578.9), cea=False, lef="nk.lef")   # the unmirrored spot is buried
            self.assertEqual(A.counts(raw, root=d)["t"]["n"], 1)
            raw = plan((OX + PIN_LEF[0], OY + 578.9), orient="R0", cea=False, lef="nk.lef")
            self.assertEqual(A.counts(raw, root=d), {})
            raw = plan((OX + PIN_LEF[0], OY + (H - 578.9)), orient="MX", cea=False, lef="nk.lef")
            self.assertEqual(A.counts(raw, root=d), {})
            A._PIN.clear(), A._LEF_TOP.clear()


if __name__ == "__main__":
    unittest.main()
