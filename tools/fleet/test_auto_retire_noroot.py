import tempfile, os, unittest
import auto_retire as A

class NoRoot(unittest.TestCase):
    def test_missing_root_is_nothing_to_do(self):
        self.assertEqual(A.run(os.path.join(tempfile.mkdtemp(), "kw45"), {"dies": {}}, ["", "", ""], set(), lambda t: None, lambda r: None, 350), [])
