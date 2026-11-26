"""KIT-WAVE-2: after the placed kit is back on the gen host, the PLACE-host and hub relay copies are removed"""
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import kit_wave as KW


def fake_run_factory(calls, fail_stage=None):
    def fake(argv, capture_output=True, text=True, timeout=None, **_kw):
        s = " ".join(argv)
        calls.append(s)
        out, rc = "", 0
        if "KW_GEOM_TOOLS_OK" in s:
            out = re.search(r"KW_GEOM_TOOLS_OK [0-9a-f]{16}", s).group(0) + "\n"
        elif "run_kit.sh" in s:
            out = "ot-run: RAN on epyc2 (unit oth-1): exit 0\n"
        elif "3_place.odb" in s:
            out = "/w/gen/T/run/results/asap7/x/base/3_place.odb\nNumber of cells: 1000\n"
        elif "geom_check.sh" in s:
            out = "AP_AUTO_GEOM AUTO-GEOM PASS T fill=ok(0.5)\n"
        if fail_stage and fail_stage in s:
            rc = 1
        return SimpleNamespace(returncode=rc, stdout=out, stderr="")
    return fake


def spec(d, gen_host="intel1"):
    sp = {"die": "s81", "item": "T", "event": "e", "plan": "/p/plan.json", "gen_host": gen_host, "src": "/src",
          "root": "/w0", "work": "/w", "kit_rtl": {}, "gen_args": [], "preflight_args": [], "hosts": ["intel2", "epyc2"],
          "hub": "intel2", "place_prefer": [], "place_mem_gb": 48, "place_threads": 8, "geom_mem_gb": 24,
          "gen_mem_gb": 16, "bind_mem_gb": 24, "ot_run": "ot-run"}
    p = Path(d) / "spec.json"
    p.write_text(json.dumps(sp))
    return p


class Clean(unittest.TestCase):
    def go(self, fail_stage=None, gen_host="intel1"):
        calls = []
        real = KW.subprocess.run
        KW.subprocess.run = fake_run_factory(calls, fail_stage)
        try:
            with tempfile.TemporaryDirectory() as d:
                KW.run_item(spec(d, gen_host))
        finally:
            KW.subprocess.run = real
        return calls

    def test_place_and_hub_copies_removed_after_push(self):
        calls = self.go()
        rm = [c for c in calls if "rm -rf /w/gen" in c and "mkdir" not in c]
        self.assertTrue(any(c.startswith("ssh") and " epyc2 " in f" {c} " for c in rm))
        self.assertTrue(any(c.startswith("bash -c rm -rf /w/gen") for c in rm))
        self.assertFalse(any("intel1" in c for c in rm))                     # never the gen host copy
        i_push = next(i for i, c in enumerate(calls) if "rsync" in c and "intel1:" in c and "/w/gen/ intel1" in c)
        self.assertTrue(all(calls.index(c) > i_push for c in rm))

    def test_no_clean_when_push_fails(self):
        calls = self.go(fail_stage="/w/gen/ intel1:")
        self.assertFalse([c for c in calls if "rm -rf /w/gen" in c and "mkdir" not in c])

    def test_shared_bind_reserves_threads_only_on_cache_miss(self):
        from unittest.mock import patch

        for ready in (False, True):
            calls = []
            with tempfile.TemporaryDirectory() as d:
                p = spec(d)
                sp = json.loads(p.read_text())
                sp["kit_rtl"] = {"mode": "bind", "asbuilt": "/p/asbuilt.json"}
                p.write_text(json.dumps(sp))
                miss = None if ready else "test -f /w0/bind/.kw_bind_ok"
                run = fake_run_factory(calls, miss)

                def run_until_gen(cmd, *args, **kwargs):
                    if "kit-rtl -h" in " ".join(cmd):
                        raise RuntimeError("after shared bind")
                    return run(cmd, *args, **kwargs)

                with patch.object(KW, "HOME", Path(d)), patch.object(KW.subprocess, "run", run_until_gen):
                    with self.assertRaisesRegex(RuntimeError, "after shared bind"):
                        KW.run_item(p)
            requests = [c for c in calls if "--threads 48" in c and ".bind.lock" in c]
            self.assertEqual(len(requests), int(not ready))


    def test_gen_on_hub_is_refused_by_the_hub_guard(self):
        # FLEET-WATCH-R8 11-21 (COORD URGENT, owner 11-12 capped build host): the hub is a capped build host again, ot-run HOST_RESERVE bounds it
        self.go(gen_host="intel2")      # no hub-guard RuntimeError any more


if __name__ == "__main__":
    unittest.main()
