"""Verify actual compilation, exact object retention and archive linkage cheaply."""
import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
S=importlib.util.spec_from_file_location('objects',Path(__file__).resolve().parents[1]/'tools/hbm_generated_json_objects.py')
R=importlib.util.module_from_spec(S);S.loader.exec_module(R)

@unittest.skipUnless(shutil.which('g++') and shutil.which('ar'),'C++ toolchain required')
class Objects(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.d=Path(self.tmp.name);self.compiler=Path(shutil.which('g++'))
        self.s=self.d/'leaf.cpp';self.s.write_text('extern "C" int value() { return 73; }\n')
    def test_real_object_reuse_rejects_changed_source(self):
        o=self.d/'leaf.o';R.build_one(self.compiler,self.s,o,['-std=c++20'],'exact')
        before=o.stat().st_mtime_ns
        self.assertEqual(R.build_one(self.compiler,self.s,o,['-std=c++20'],'exact'),o)
        self.assertEqual(o.stat().st_mtime_ns,before)
        self.s.write_text('extern "C" int value() { return 17; }\n')
        with self.assertRaises(ValueError):R.build_one(self.compiler,self.s,o,['-std=c++20'],'exact')
    def test_real_archive_and_source_owned_harness_link(self):
        include=self.d/'include';include.mkdir();(include/'verilated_dpi.cpp').write_text('// tiny test runtime\n')
        model=dict(job=dict(prefix='Vleaf',cflags=[]),json=str(self.d/'Vleaf.json'),
                   sources=[str(self.s)],runtime=[],include=str(include),options={'use_timing':False},pins={},tool_pins={})
        out=self.d/'build';out.mkdir();harness=self.d/'harness.cpp'
        harness.write_text('extern "C" int value(); int main() { return value()==73 ? 0 : 1; }\n')
        result=R.build([model],out,self.compiler,Path(shutil.which('ar')),1,harness)
        self.assertTrue(result['linked']);self.assertTrue(result['libraries'])
        import subprocess
        self.assertEqual(subprocess.call([result['binary']]),0)
    def test_failed_cpp_preserves_diagnostic(self):
        self.s.write_text('this is an actual compiler error\n');o=self.d/'failed.o'
        with self.assertRaises(RuntimeError):R.build_one(self.compiler,self.s,o,[],'exact')
        self.assertTrue(o.with_suffix('.log').is_file())
        self.assertFalse(o.with_suffix('.receipt.json').exists())
    def test_harness_include_change_rejects_old_object(self):
        include=self.d/'inputs.inc';include.write_text('#define VALUE 73\n')
        self.s.write_text('#include "inputs.inc"\nint main() { return VALUE; }\n')
        o=self.d/'harness.o';envelope=R.digest(R.harness_dependencies(self.s))
        R.build_one(self.compiler,self.s,o,[],envelope)
        include.write_text('#define VALUE 17\n')
        changed=R.digest(R.harness_dependencies(self.s))
        self.assertNotEqual(envelope,changed)
        with self.assertRaises(ValueError):R.build_one(self.compiler,self.s,o,[],changed)

if __name__=='__main__':unittest.main()
