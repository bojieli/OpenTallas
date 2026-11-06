"""Regression for ORFS procedure-scoped hook invocation."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class LoadBankScopeTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("tclsh"), "requires Tcl")
    def test_nested_hook_uses_global_block_and_propagates_errors(self):
        helper = Path(__file__).with_name("load_bank.tcl")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hook = root / "caller bank script.tcl"
            hook.write_text("set ::seen $ff_blk\n")
            bad = root / "bad bank script.tcl"
            bad.write_text("error EXPECTED_BANK_FAILURE\n")
            runner = root / "orfs.tcl"
            runner.write_text('''source [lindex $argv 0]
proc orfs_hook {path} {
    set ff_blk LOCAL_SHADOW
    return [lb_apply $path]
}
set ff_blk GLOBAL_BLOCK
set got [orfs_hook [lindex $argv 1]]
if {$got ne "GLOBAL_BLOCK" || $::seen ne "GLOBAL_BLOCK"} {
    error "bank script did not use the face_flops global block"
}
if {![catch {orfs_hook [lindex $argv 2]} message] ||
    $message ne "EXPECTED_BANK_FAILURE"} {
    error "bank script failure was swallowed"
}
puts PASS
''')
            result = subprocess.run(
                ["tclsh", str(runner), str(helper), str(hook), str(bad)],
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(result.stdout.strip(), "PASS")


if __name__ == "__main__":
    unittest.main()
