import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class HierarchyLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = sys.path[:]
        try:
            sys.path.insert(0, str(ROOT/'tools'))
            spec = importlib.util.spec_from_file_location('hierarchy_link', ROOT/'tools/qwen_rom_combined_link_hierarchy.py')
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)
        finally:
            sys.path[:] = previous

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.makefile = self.root/'Vdie_hier.mk'
        self.makefile.write_text('VM_HIER_LIBS := \\\n  '+' \\\n  '.join(self.module.EXPECTED)+' \\\n\n')
        self.archives = [self.root/'Vdie__ALL.a', *(self.root/n for n in self.module.EXPECTED)]
        for archive in self.archives:
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_bytes(b'!<arch>\n')

    def test_top_plus_all_three_generated_libraries_required(self):
        self.assertEqual(self.module.require_hierarchy_archives(self.root), self.archives)
        for archive in self.archives:
            with self.subTest(missing=archive.name):
                archive.unlink()
                with self.assertRaises(ValueError):
                    self.module.require_hierarchy_archives(self.root)
                archive.write_bytes(b'!<arch>\n')

    def test_empty_library_and_changed_or_duplicate_source_manifest_refused(self):
        self.archives[1].write_bytes(b'')
        with self.assertRaises(ValueError):
            self.module.require_hierarchy_archives(self.root)
        self.archives[1].write_bytes(b'!<arch>\n')
        original = self.makefile.read_text()
        for manifest in (original.replace(self.module.EXPECTED[0], '../foreign.a'),
                         original+'VM_HIER_LIBS := other.a\n',
                         original.replace(self.module.EXPECTED[1], self.module.EXPECTED[0])):
            self.makefile.write_text(manifest)
            with self.assertRaises(ValueError):
                self.module.require_hierarchy_archives(self.root)

if __name__ == '__main__':
    unittest.main()
