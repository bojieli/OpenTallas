"""Small retained ECO admission and launch use the same honest resource request."""
import copy
import unittest
from unittest.mock import Mock, patch

import closure_loop as cl


class HoldEcoResources(unittest.TestCase):
    def job(self, ram=4):
        return dict(name="metadata", host="test", run="/retained", spec=dict(
            name="metadata", block="metadata", peak_ram_gb=ram, threads=8,
            stages=dict(route=dict(cmd="route", peak_ram_gb=ram)), verdict={}))

    def test_completed_small_route_gets_eight_gb_minimum(self):
        with patch.object(cl, "measured_peak_gb", return_value=0):
            self.assertEqual(cl.hold_eco_resources(self.job()), (8, 8))

    def test_large_unknown_and_measured_classes_keep_large_policy(self):
        for requested, measured, expected in ((12,0,32), (32,0,32), (64,0,64),
                                               (4,40,50), (96,3,8), (4,4.1,32)):
            with self.subTest(requested=requested, measured=measured), patch.object(cl, "measured_peak_gb", return_value=measured):
                self.assertEqual(cl.hold_eco_resources(self.job(requested)), (8, expected))
        j=self.job(96);j["spec"]["measured_ram"]=False
        with patch.object(cl, "measured_peak_gb", return_value=3):
            self.assertEqual(cl.hold_eco_resources(j), (8,96))
        j=self.job();j["spec"].pop("peak_ram_gb");j["spec"]["stages"]={}
        with patch.object(cl, "measured_peak_gb", return_value=0):
            self.assertEqual(cl.hold_eco_resources(j), (8,32))

    def fleet(self, disk=81, mem=64):
        fleet=cl.Fleet()
        info=dict(mem_gb=mem, disk_gb=disk, roots_gb={"/":disk}, admission_measured_at=1e10)
        fleet.probe=Mock(return_value=info)
        cfg=dict(label="test", max_job_threads=16, max_job_ram_gb=128,
                 min_free_disk_gb=200, min_free_ram_gb=16)
        return fleet,cfg

    def test_actual_81gb_host_admits_small_but_not_large_and_keeps_floors(self):
        for disk, mem, ram, expected in ((81,64,8,True), (81,64,32,False),
                                        (29,64,8,False), (81,23,8,False)):
            with self.subTest(disk=disk, mem=mem, ram=ram):
                fleet,cfg=self.fleet(disk,mem)
                with patch.object(cl,"host_cfg",return_value=cfg), patch.object(cl,"disk_roots",return_value={"/":200}):
                    self.assertEqual(fleet.fits("test",8,ram)[0], expected)

    def test_capacity_reservation_and_launch_use_same_sizing(self):
        j=self.job(); fleet=Mock();fleet.fits.return_value=(True,"ok")
        metrics=dict(ss_ps=356.68,ff_ps=-6.28,setup_corner="tt")
        with patch.object(cl,"measured_peak_gb",return_value=0), patch.object(cl,"eco_paths",return_value=("/rb","/ob")), \
             patch.object(cl,"eco_post_sdcs",return_value=[]), patch.object(cl,"verdict_macros",return_value=[]), \
             patch.object(cl,"ship_helpers"), patch.object(cl,"launch_stage") as launch, \
             patch.object(cl,"event"), patch.object(cl,"experiment"):
            self.assertTrue(cl.start_hold_eco(j,fleet,metrics))
        fleet.fits.assert_called_once_with("test",8,8)
        fleet.reserve_launch.assert_called_once_with("test",8,8)
        st=launch.call_args.args[1]
        self.assertEqual((st["threads"],st["ram"]),(8,8))
        self.assertIn("THREADS=8",launch.call_args.args[2])
        self.assertEqual(j["eco"]["resources"],dict(threads=8,ram=8))
        self.assertEqual(j["status"],"ECO")

    def test_blocked_small_eco_does_not_ship_or_launch(self):
        j=self.job(); original=copy.deepcopy(j);fleet=Mock();fleet.fits.return_value=(False,"memory low")
        with patch.object(cl,"measured_peak_gb",return_value=0), patch.object(cl,"eco_paths",return_value=("/rb","/ob")), \
             patch.object(cl,"ship_helpers") as ship, patch.object(cl,"launch_stage") as launch, patch.object(cl,"event"):
            self.assertTrue(cl.start_hold_eco(j,fleet,{}))
        ship.assert_not_called();launch.assert_not_called();fleet.reserve_launch.assert_not_called()
        self.assertEqual(j,original)


if __name__=="__main__":
    unittest.main()
