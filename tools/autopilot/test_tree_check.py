import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

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
            "p.write_text(str(int(p.read_text())+1 if p.exists() else 1))\n"
            "time.sleep(0.1)\n"
            "print('verified')\n"
            "raise SystemExit(3 if 'failed-hash' in sys.argv else 0)\n")
        return checker

    def produce_in_separate_process(self, td, checker, want):
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
            "T.launch(root,ident,checker,'4'*40,launcher=detached)\n")
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
            self.assertEqual((Path(td) / "count").read_text(), "2")  # one full check per each of two hosts
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
            self.assertEqual((Path(td) / "count").read_text(), "2")
            reordered = TC.identity("s81", "/published/_d6", "published-hash", ["epyc2", "epyc7"], str(checker))
            self.assertEqual(reordered, ident)
            changed = TC.identity("s81", "/published/_d6", "changed-hash", ["epyc7", "epyc2"], str(checker))
            self.assertIsNone(TC.read(td, changed))
            changed_host = TC.identity("s81", "/published/_d6", "published-hash", ["epyc10"], str(checker))
            self.assertIsNone(TC.read(td, changed_host))

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
