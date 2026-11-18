import json, os, tempfile, unittest
import kit_peak_disk as K

GB = 2**30


def state(n, host="epyc7"):
    return {"items": {str(i): {"status": "FAIL", "work": "/w/%d" % i, "gen_host": host, "updated": str(1000 + i)} for i in range(n)}}


class Peak(unittest.TestCase):
    def test_pick_newest_finished_with_work_dir_once(self):
        s = state(30); s["items"]["x"] = {"status": "RUNNING", "work": "/w/run", "gen_host": "epyc7", "updated": "9999"}
        p = K.pick(s, 24)
        self.assertEqual(len(p), 24); self.assertEqual(p[0], ("epyc7", "/w/29")); self.assertNotIn(("epyc7", "/w/run"), p)

    def test_p90_of_measured_sizes_and_refresh_cache(self):
        d = tempfile.mkdtemp(); calls = []
        def du(h, ds): calls.append(h); return {x: (int(x.split("/")[-1]) % 10 + 1) * GB for x in ds}
        rec = K.refresh(d, state(20), du, now=5000.0)
        self.assertEqual(rec["n"], 20); self.assertEqual(rec["p90_gb"], 9.0)
        self.assertIsNone(K.refresh(d, state(20), du, now=5000.0 + 3600))       # inside REFRESH_H: no second du
        self.assertEqual(len(calls), 1)
        self.assertEqual(K.load(d, now=5000.0 + 3600), 9.0)
        self.assertIsNone(K.load(d, now=5000.0 + 80 * 3600))                    # stale

    def test_too_few_samples_or_failed_du_give_no_measurement(self):
        d = tempfile.mkdtemp()
        K.refresh(d, state(3), lambda h, ds: {x: GB for x in ds}, now=1.0)
        self.assertIsNone(K.load(d, now=2.0))                                   # n < MIN_N
        self.assertIsNone(K.refresh(d, state(10), lambda h, ds: 1 / 0, now=1.0, force=True))

    def test_floor_from_peak_clamped_and_falls_back(self):
        self.assertEqual(K.floor({"gen_disk_min_gb": 70}), 70)                  # no measurement
        self.assertEqual(K.floor({"gen_disk_min_gb": 70, "_gen_peak_gb": 3}), 60)   # 50 + ceil(3.75) = 54 -> clamp to HARD + 10
        self.assertEqual(K.floor({"gen_disk_min_gb": 70, "_gen_peak_gb": 20}), 75)  # 50 + 25: measured raises it above the flat 70
        self.assertEqual(K.floor({"gen_disk_min_gb": 70, "_gen_peak_gb": 400}), 150)
        self.assertEqual(K.floor({"gen_disk_min_gb": 70, "_gen_peak_gb": 20, "gen_floor_measured": False}), 70)
        self.assertEqual(K.floor({"gen_disk_min_gb": 0, "_gen_peak_gb": 20}), 0)    # 0 still turns the floor off
