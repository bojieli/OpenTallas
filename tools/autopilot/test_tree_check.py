import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tree_check as TC

MODULE_DIR = str(Path(TC.__file__).resolve().parent)


class DurableCheck(unittest.TestCase):
    def fixture(self, td):
        checker = Path(td) / "checker.py"
        checker.write_text(
            "from pathlib import Path\nimport sys,time\n"
            f"p=Path({str(Path(td) / 'count')!r})\n"
            "if '--cached-receipts' in sys.argv: raise SystemExit(2)\n"
            "with p.open('a') as f: f.write(sys.argv[sys.argv.index('--hosts')+1]+'\\n')\n"
            "time.sleep(0.1)\n"
            "print('verified')\n"
            "raise SystemExit(3 if 'failed-hash' in sys.argv else 0)\n")
        return checker

    def produce_in_separate_process(self, td, checker, want, links_only=False):
        # This first interpreter exits while its worker is still running. A new
        # interpreter below must consume its result without module globals.
        code = (
            "import sys,subprocess\n"
            f"sys.path.insert(0,{MODULE_DIR!r})\n"
            "import tree_check as T\n"
            f"root={td!r}; checker={str(checker)!r}\n"
            f"ident=T.identity('s81','/published/_d6',{want!r},['epyc7','epyc2'],checker)\n"
            "def detached(argv):\n"
            " i=argv.index(sys.executable)\n"
            " subprocess.Popen(argv[i:],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)\n"
            " return subprocess.CompletedProcess(argv,0,'','')\n"
            f"T.launch(root,ident,checker,'4'*40,links_only={links_only!r},launcher=detached)\n")
        subprocess.run([sys.executable, "-I", "-c", code], check=True)
        ident = TC.identity("s81", "/published/_d6", want, ["epyc7", "epyc2"], str(checker))
        end = time.monotonic() + 10
        result = None
        while time.monotonic() < end:
            result = TC.read(td, ident, active_fn=lambda unit: True)
            if result and not result.get("running"):
                return ident, result
            time.sleep(0.02)
        self.fail("detached checker did not complete")

    def test_completed_receipt_survives_two_processes_without_second_hash(self):
        with tempfile.TemporaryDirectory() as td:
            checker = self.fixture(td)
            ident, result = self.produce_in_separate_process(td, checker, "published-hash")
            self.assertEqual(result["state"], "ok")
            self.assertTrue(result["full_ok"])
            self.assertEqual(sorted((Path(td) / "count").read_text().splitlines()), ["epyc2", "epyc7"])  # one full check per each of two hosts
            consumer = (
                "import sys,json\n"
                f"sys.path.insert(0,{MODULE_DIR!r})\n"
                "import tree_check as T\n"
                f"ident=json.loads({json.dumps(ident)!r})\n"
                f"r=T.read({td!r},ident)\n"
                "assert r['state']=='ok' and r['full_ok']\n"
                "def forbidden(argv): raise AssertionError('completed tuple reverified')\n"
                f"r=T.launch({td!r},ident,{str(checker)!r},'4'*40,launcher=forbidden)\n"
                "assert r['state']=='ok'\n"
                "print(r['main_sha'])\n")
            out = subprocess.check_output([sys.executable, "-I", "-c", consumer], text=True)
            self.assertEqual(out.strip(), "4" * 40)
            self.assertEqual(sorted((Path(td) / "count").read_text().splitlines()), ["epyc2", "epyc7"])
            reordered = TC.identity("s81", "/published/_d6", "published-hash", ["epyc2", "epyc7"], str(checker))
            self.assertEqual(reordered, ident)
            changed = TC.identity("s81", "/published/_d6", "changed-hash", ["epyc7", "epyc2"], str(checker))
            self.assertIsNone(TC.read(td, changed))
            changed_host = TC.identity("s81", "/published/_d6", "published-hash", ["epyc10"], str(checker))
            self.assertIsNone(TC.read(td, changed_host))

    def test_failed_link_check_recovers_via_fresh_receipt_in_new_process(self):
        with tempfile.TemporaryDirectory() as td:
            checker = Path(td) / "checker.py"
            checker.write_text(
                "from pathlib import Path\nimport sys\n"
                f"root=Path({td!r})\n"
                "bad=(root/'bad-link').exists()\n"
                "wrong='failed-hash' in sys.argv\n"
                "host=sys.argv[sys.argv.index('--hosts')+1]\n"
                "receipt=root/('receipt-'+host)\n"
                "if '--links-only' in sys.argv: raise SystemExit(3 if bad else 0)\n"
                "if '--cached-receipts' in sys.argv:\n"
                " print('fresh readonly/unshared inventory')\n"
                " raise SystemExit(0 if receipt.exists() and not bad and not wrong else 2)\n"
                "p=root/'count'\n"
                "with p.open('a') as f: f.write(sys.argv[sys.argv.index('--hosts')+1]+'\\n')\n"
                "if bad or wrong: raise SystemExit(3)\n"
                "receipt.touch()\n")
            ident, first = self.produce_in_separate_process(td, checker, "published-hash")
            self.assertEqual(first["state"], "ok")
            self.assertEqual(sorted((Path(td) / "count").read_text().splitlines()), ["epyc2", "epyc7"])
            (Path(td) / "bad-link").touch()
            _, failed = self.produce_in_separate_process(td, checker, "published-hash", links_only=True)
            self.assertEqual(failed["state"], "bad")
            self.assertTrue(failed["full_ok"])  # old content proof cannot override current failed inventory
            self.assertEqual(sorted((Path(td) / "count").read_text().splitlines()), ["epyc2", "epyc7"])
            (Path(td) / "bad-link").unlink()
            _, repaired = self.produce_in_separate_process(td, checker, "published-hash")
            self.assertEqual(repaired["state"], "ok")
            self.assertTrue(repaired["full_ok"])
            self.assertNotIn("why", repaired)
            self.assertNotEqual(repaired["attempt"], failed["attempt"])
            self.assertEqual({r["basis"] for r in repaired["details"]}, {"published-verification-receipt"})
            self.assertEqual(sorted((Path(td) / "count").read_text().splitlines()), ["epyc2", "epyc7"])  # repaired links did not rehash source payload
            self.assertTrue(TC.read(td, ident)["full_ok"])
            wrong_ident, wrong = self.produce_in_separate_process(td, checker, "failed-hash")
            self.assertNotEqual(wrong_ident, ident)
            self.assertEqual(wrong["state"], "bad")
            self.assertFalse(wrong.get("full_ok", False))
            self.assertEqual(TC.read(td, ident)["attempt"], repaired["attempt"])

    def test_slow_cached_host_does_not_delay_another_hosts_full_check(self):
        with tempfile.TemporaryDirectory() as td:
            checker = self.fixture(td)
            ident = TC.identity("s81", "/tree", "manifest", ["epyc7", "epyc2"], checker)
            TC.launch(td, ident, checker, "main", launcher=lambda argv: subprocess.CompletedProcess(argv, 0))
            folder = TC.location(td, ident)
            attempt = json.loads((folder / "result.json").read_text())["attempt"]
            finished_full = threading.Event()

            def check(argv, **kwargs):
                self.assertEqual(argv[2:5], [str(folder / ("src_manifest-" + ident["checker_sha256"] + ".py")), "hosts", "/tree"])
                self.assertEqual(argv[7:9], ["--expect", "manifest"])
                host = argv[6]
                if host == "epyc2":
                    self.assertEqual(argv[9:], ["--cached-receipts"])
                    self.assertTrue(finished_full.wait(3), "slow host prevented epyc7 from completing")
                elif argv[9:] == ["--cached-receipts"]:
                    return subprocess.CompletedProcess(argv, 2, "missing", "")
                else:
                    self.assertEqual((host, argv[9:]), ("epyc7", []))
                    self.assertTrue(json.loads((folder / "result.json").read_text())["running"])
                    finished_full.set()
                return subprocess.CompletedProcess(argv, 0, host, "")

            with patch.object(TC.subprocess, "run", side_effect=check):
                self.assertEqual(TC.worker(folder / (attempt + ".json")), 0)
            result = TC.read(td, ident)
            self.assertEqual([(r["host"], r["basis"], r["rc"]) for r in result["details"]], [
                ("epyc2", "published-verification-receipt", 0),
                ("epyc7", "cache-miss", 2),
                ("epyc7", "full-verification", 0),
            ])
            self.assertEqual(json.loads((folder / (attempt + ".result.json")).read_text()), result)

    def test_failed_host_preserves_other_host_evidence_and_newer_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            checker = self.fixture(td)
            ident = TC.identity("s81", "/tree", "manifest", ["epyc7", "epyc2"], checker)
            pending = TC.launch(td, ident, checker, "main", launcher=lambda argv: subprocess.CompletedProcess(argv, 0))
            folder = TC.location(td, ident)
            spec = folder / (pending["attempt"] + ".json")
            newer = dict(pending, attempt="newer")
            TC.atomic_json(folder / "result.json", newer)

            def check(argv, **kwargs):
                if argv[6] == "epyc7":
                    raise OSError("checker unavailable")
                return subprocess.CompletedProcess(argv, 0, "verified", "")

            with patch.object(TC.subprocess, "run", side_effect=check):
                self.assertEqual(TC.worker(spec), 1)
            failed = json.loads((folder / (pending["attempt"] + ".result.json")).read_text())
            self.assertEqual(failed["state"], "bad")
            self.assertIn("checker unavailable", failed["why"])
            self.assertEqual([(r["host"], r["basis"], r["rc"]) for r in failed["details"]], [
                ("epyc2", "published-verification-receipt", 0),
                ("epyc7", "cache-miss", 1),
                ("epyc7", "full-verification", 1),
            ])
            self.assertEqual(json.loads((folder / "result.json").read_text()), newer)

    def test_failed_verification_cannot_be_consumed_as_pass(self):
        with tempfile.TemporaryDirectory() as td:
            checker = self.fixture(td)
            ident, result = self.produce_in_separate_process(td, checker, "failed-hash")
            self.assertEqual(result["state"], "bad")
            self.assertFalse(result.get("full_ok", False))
            self.assertTrue(result["why"])
            folder = TC.location(td, ident)
            self.assertEqual(len(list(folder.glob("*.result.json"))), 1)
            self.assertTrue(list(folder.glob("*.json")))  # failed attempt evidence remains


if __name__ == "__main__":
    unittest.main()
