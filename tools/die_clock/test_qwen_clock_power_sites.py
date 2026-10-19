import unittest
from qwen_clock_power_sites import ClockPowerSites
from qwen_exact_corridor import ExactBayGrid


def policy(hard=(),m9=None):
    pins={'BUF':{'R0':{'VDD':(-.018,.261,1.638,.279),'VSS':(-.018,-.009,1.638,.009)},
                 'MX':{'VSS':(-.018,.261,1.638,.279),'VDD':(-.018,-.009,1.638,.009)}}}
    return ClockPowerSites(100,100,hard,pins,{'VDD':(4.08,.48),'VSS':(8.4,.48)},
                           m9 or {'VDD':[(i+1,-1,i+1.48,101) for i in range(0,100,9)],
                                  'VSS':[(i+5.5,-1,i+5.98,101) for i in range(0,100,9)]})


class ClockPowerModel(unittest.TestCase):
    def test_actual_shape_clearance_rejects_phase_and_retains_legal_rows(self):
        p=policy()
        self.assertIsNone(p.requirement(3.24,0))
        self.assertIsNotNone(p.requirement(3.24,1.35))
        self.assertFalse(p.identity()['power_qualified'])

    def test_halo_and_pin_overhang_are_obstacles(self):
        p=policy([('macro',(10,0,20,20))])
        self.assertIsNone(p.requirement(8.1,1.35))
        self.assertIsNone(p.requirement(21.09,1.35)) # .018 M1 overhang enters halo
        self.assertIsNotNone(p.requirement(22.68,1.35))

    def test_both_real_m9_contacts_and_vertical_coverage_required(self):
        p=policy(m9={'VDD':[(1,-1,1.48,101)],'VSS':[(50,-1,50.48,101)]})
        self.assertIsNone(p.requirement(3.24,1.35))
        p=policy(m9={'VDD':[(1,-1,1.48,101)],'VSS':[(5.5,2,5.98,101)]})
        self.assertIsNone(p.requirement(3.24,1.35))

    def test_grid_skips_pg_unsafe_sites_before_reserving(self):
        p=policy();g=ExactBayGrid(100,100,[],site_validator=p)
        xy=g.reserve((0,0))
        self.assertGreater(xy[1],0)
        self.assertTrue(p(*xy))
        blocked=ExactBayGrid(100,100,[],site_validator=lambda x,y:False)
        self.assertFalse(blocked.free((0,0)))
        self.assertIsNone(blocked.point((0,0)))


if __name__=='__main__':unittest.main()
