import csv
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "s81_ftok"))
from static_vm_trace import convert


class StaticTrace(unittest.TestCase):
    def trace(self, rows):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        p=Path(tmp.name)/"trace.csv"
        with p.open("w") as f:
            w=csv.writer(f); w.writerow(["time_ns","stream_cycle","job","client","event","slot","row","mask","tag"]); w.writerows(rows)
        return p

    def test_observed_deadlines_never_become_native_reservations(self):
        p=self.trace([
            ["8.333",10,0,"su","read",0,9216,"ffff",2],
            ["8.333",10,0,"hc","read",0,1280,"ffff",1],
            ["16.667",20,0,"su","response",0,9216,"ffff",2],
            ["16.667",20,0,"hc","response",0,1280,"ffff",1],
            ["20.833",25,0,"su","write",0,9408,"001f",2],
            ["25.000",30,0,"su","done",0,-1,"0000",2],
            ["25.000",30,0,"hc","done",0,-1,"0000",1]])
        r=convert(p)
        self.assertEqual(len(r["events"]),3)
        self.assertEqual(r["events"][0]["deadline_cycle"],20)
        self.assertEqual(r["events"][2]["deadline_cycle"],30)
        self.assertEqual(r["events"][2]["mask"],31)
        self.assertFalse(r["qualified"])
        self.assertFalse(r["complete_actual_trace"])
        self.assertTrue(all(not e["native_service_reserved"] for e in r["events"]))
        self.assertNotIn("service_cycle",r["events"][0])
        self.assertEqual(r["events"][0]["observed_producer"]["client"],"BOOT_OR_GOLDEN")

    def test_legacy_core_done_is_not_an_engine_deadline(self):
        p=self.trace([
            ["8",10,0,"su","read",0,9216,"ffff",2],
            ["8",10,0,"hc","read",0,1280,"ffff",1],
            ["16",20,0,"su","response",0,9216,"ffff",2],
            ["16",20,0,"hc","response",0,1280,"ffff",1],
            ["21",25,0,"su","write",0,9408,"001f",2],
            ["24",30,0,"su","done",0,-1,"0000",2]])
        r=convert(p,done_boundary="legacy_internal_core")
        w=r["events"][-1]
        self.assertNotIn("deadline_cycle",w)
        self.assertEqual(w["observed_core_done_cycle"],30)
        self.assertTrue(w["native_done_deadline_missing"])
        self.assertTrue(all("done_cycle" not in j for j in r["jobs"]))

    def test_partial_or_unpaired_capture_fails(self):
        p=self.trace([["8",10,0,"su","read",0,9216,"ffff",2]])
        with self.assertRaisesRegex(ValueError,"lack model responses"):
            convert(p)
        p=self.trace([["8",10,0,"su","response",0,9216,"ffff",2]])
        with self.assertRaisesRegex(ValueError,"unsolicited"):
            convert(p)


if __name__=="__main__": unittest.main()
