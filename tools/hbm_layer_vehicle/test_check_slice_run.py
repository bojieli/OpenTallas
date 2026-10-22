import json
from pathlib import Path
import tempfile
import unittest

from hbm_layer_vehicle.check_slice_run import check_run


class CompletenessTest(unittest.TestCase):
    def fixture(self, root, *, checks=1, serial=100, rec_cycle=100):
        (root/'boundary.json').write_text(json.dumps(dict(outputs=[dict(name='su_SW0__fault',width=1,
                                                                       driver='su_SW0.fault')])))
        (root/'tb_slice.sv').write_text("""reg [0:0] po0 = '0; integer f0 = -1, l0 = -1, n0 = 0;
always @(posedge ck0) if (rs0) begin
if (su_SW0__fault != po0) begin if (f0 < 0) f0 = cnt[0]; l0 = cnt[0]; n0 = n0 + 1; po0 = su_SW0__fault; end
if (cnt[0] >= cycles) begin
if (n0 > 0) $display("SLICE_OUT su_SW0__fault first=%0d last=%0d changes=%0d", f0, l0, n0);
end end
""")
        # Stream drive at 5, serial record-0 comparison at 100.
        headers = [(1 << 62) | 5, (2 << 62) | (1 << 60) | (1 << 32) | 100, 3 << 62]
        (root / "hdr.mem").write_text("\n".join(f"{h:016x}" for h in headers))
        (root / "index.json").write_text(json.dumps(dict(events=2, drives=1, checks=1)))
        (root / "run.log").write_text(
            (f"SLICE_REC rec=0 cyc={rec_cycle} COMMIT_OK\n" if checks else "") +
            f"SLICE_SUMMARY drives=1 checks={checks} fails=0 rec_commit_ok={checks} rec_fail=0 stream_edges=150 serial_edges={serial} hbm_edges=200\nSLICE_PASS\n")

    def test_complete(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            self.assertTrue(check_run(p, p / "run.log")["passed"])

    def test_component_pass_cannot_qualify_native_chain(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            result = check_run(p, p / "run.log", scope="native_chain")
            self.assertFalse(result["passed"])
            self.assertFalse(result["qualifies_native_layer"])
            self.assertFalse(result["qualifies_native_chain"])

    def test_old_tb_false_pass_before_serial_check(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p, checks=0, serial=90)
            result = check_run(p, p / "run.log")
            self.assertFalse(result["passed"])
            self.assertTrue(any("last scheduled event" in e for e in result["errors"]))

    def test_wrong_commit_edge(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p, rec_cycle=99)
            self.assertFalse(check_run(p, p / "run.log")["passed"])

    def test_silent_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            with (p / "hdr.mem").open("a") as f:
                f.write(f"\n{(2 << 62) | (1 << 60) | (1 << 32) | 110:016x}\n")
            self.assertFalse(check_run(p, p / "run.log")["passed"])

    def test_missing_vm_preload(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            (p / "index.json").write_text(json.dumps(dict(events=2, drives=1, checks=1, vm_preload_words=1)))
            self.assertFalse(check_run(p, p / "run.log")["passed"])

    def test_numeric_pass_with_actual_fault_activity_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            with (p/'run.log').open('a') as f:
                f.write('SLICE_OUT su_SW0__fault first=31 last=31 changes=1\n')
            result = check_run(p,p/'run.log')
            self.assertFalse(result['passed'])
            self.assertEqual(result['fault_observation']['observed_activity'][0]['port'],'su_SW0__fault')

    def test_nondeclared_control_activity_is_not_a_fault_output(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            with (p/'run.log').open('a') as f:
                f.write('SLICE_OUT some_fault_mask_control first=31 last=31 changes=1\n')
            self.assertTrue(check_run(p,p/'run.log')['passed'])

    def test_unverified_fault_observer_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); self.fixture(p)
            q=p/'tb_slice.sv';q.write_text(q.read_text().replace("po0 = '0", "po0 = '1"))
            self.assertFalse(check_run(p,p/'run.log')['passed'])


if __name__ == "__main__":
    unittest.main()
