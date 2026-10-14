import unittest
from types import SimpleNamespace
from unittest.mock import patch
import kvsys_window as W

class SignalWindows(unittest.TestCase):
    def scan(self, a, b):
        instances = [SimpleNamespace(name=n,master="qkd_rly_test",x=x,y=y,w=1,h=1)
                     for n,(x,y) in zip(["a","b"],[a,b])]
        model = dict(die=dict(w=1000,h=1000),insts=instances,
                     buses=[("far_head","stack_local",1000,[("a","p"),("b","p")])])
        with patch.object(W.K,"pin_xy",side_effect=lambda i,m,p:(i.x,i.y)):
            return W.scan(model,{"qkd_rly_test":object()},260)
    def test_abut_class_with_real_length_counts(self):
        r=self.scan((20,20),(700,700))
        self.assertGreater(r["max_util_h"],0)
        self.assertGreater(r["max_util_v"],0)
        self.assertTrue(any("far_head" in dict(w["top"]) for w in r["hot"]))
    def test_actual_touch_has_no_routing_demand(self):
        r=self.scan((20,20),(20,20))
        self.assertEqual((r["max_util_h"],r["max_util_v"]),(0,0))
    def test_horizontal_segment_has_no_vertical_demand(self):
        r=self.scan((20,20),(700,20))
        self.assertGreater(r["max_util_h"],0)
        self.assertEqual(r["max_util_v"],0)
    def test_face_bits_route_from_their_own_pins(self):
        # two 1,000-bit faces facing each other across a 10-um gap: per-bit routes are short horizontal wires (no V)
        M=SimpleNamespace(ports={"p":("face",1000,"E","M4",500.0,20)},w=10,h=1000)
        N=SimpleNamespace(ports={"p":("face",1000,"W","M4",500.0,20)},w=10,h=1000)
        ins=[SimpleNamespace(name="a",master="A",x=0,y=0,w=10,h=1000,orient="R0"),
             SimpleNamespace(name="b",master="B",x=20,y=0,w=10,h=1000,orient="R0")]
        model=dict(die=dict(w=1000,h=1000),insts=ins,buses=[("dfi","phy_dfi",1000,[("a","p"),("b","p")])])
        r=W.scan(model,{"A":M,"B":N},260)
        self.assertEqual(r["max_util_v"],0)
        r0=W.scan(model,{"A":M,"B":N},260,per_bit=False)
        self.assertEqual(r0["max_util_v"],0)

if __name__ == "__main__":unittest.main()
