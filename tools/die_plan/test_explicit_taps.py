from types import SimpleNamespace
import unittest
from unittest.mock import patch
import schema as S
import taps as T
import gen_phys as G

def plan():
    return SimpleNamespace(types={'t':dict(outline_um=[400,400],clock=dict(tap_mode='explicit',tap_radius_um=80,tap_max_sinks=10,
        taps=[dict(name='clk',xy=[100,100],kind='leaf'),dict(name='clk_t1',xy=[300,300],kind='leaf')]))})

class ExplicitTaps(unittest.TestCase):
    def test_fixed_ports_and_native_density_recipe(self):
        p=plan()
        with patch.object(T,'sink_sites',return_value=[(110.,100.,3.),(300.,290.,4.)]):
            self.assertEqual(S.tap_grid(p,'t'),[('clk',100.,100.),('clk_t1',300.,300.)])
            self.assertEqual(T.sink_taps(p,'t'),[('clk',100.,100.,3.,10.),('clk_t1',300.,300.,4.,10.)])
        self.assertTrue(S.sink_tap_mode(p.types['t']))
        self.assertTrue(G._density(p.types['t']))
        self.assertEqual(G._tap_cap(p.types['t']),10)

    def test_control_demand_changes_load_without_moving_ports(self):
        p=plan();before=p.types['t']['clock']['taps'].copy()
        with patch.object(T,'sink_sites',return_value=[(100.,100.,3.),(300.,300.,4.),(110.,100.,2.)]):
            self.assertEqual(T.explicit_taps(p,'t')[0],('clk',100.,100.,5.,10.))
        self.assertEqual(p.types['t']['clock']['taps'],before)

    def test_capacity_distance_and_empty_fail_closed(self):
        for sinks in ([(100.,100.,11.),(300.,300.,1.)],[(1.,1.,1.),(300.,300.,1.)],[(100.,100.,1.)]):
            with self.subTest(sinks=sinks),patch.object(T,'sink_sites',return_value=sinks):
                with self.assertRaisesRegex(ValueError,'load='):
                    T.explicit_taps(plan(),'t')

    def test_halo_and_port_order_are_not_repaired(self):
        p=plan();p.types['t']['clock']['keepouts_um']=[[95,95,105,105]]
        with self.assertRaisesRegex(ValueError,'halo'):
            T.explicit_taps(p,'t')
        p=plan();p.types['t']['clock']['taps'].reverse()
        with self.assertRaisesRegex(ValueError,'names/order'):
            T.explicit_taps(p,'t')

    def test_rounded_density_spacing_boundary(self):
        p=plan();p.types["t"]["outline_um"]=[1500,1300]
        xy=[[712.6712,367.2908],[721.3112,375.9308]]
        p.types["t"]["clock"]["taps"]=[dict(name=n,xy=v,kind="leaf") for n,v in zip(("clk","clk_t1"),xy)]
        with patch.object(T,"sink_sites",return_value=[(*v,1.) for v in xy]):
            self.assertEqual(len(T.explicit_taps(p,"t")),2)
            p.types["t"]["clock"]["taps"][1]["xy"]=[721.3111,375.9307]
            with self.assertRaisesRegex(ValueError,"spacing"):
                T.explicit_taps(p,"t")

if __name__=='__main__':unittest.main()
