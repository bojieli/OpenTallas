import hashlib
from pathlib import Path
import tempfile
import unittest

from dsrom_s81_he_image import extract, literal_operation, write_exclusive


class HeImage(unittest.TestCase):
    def test_actual_literal_L0I1_scope(self):
        op=literal_operation()
        self.assertEqual((op['he_nout'],op['he_k'],op['he_wbase']),(24,2560,0))

    def test_wrong_existing_image_pin_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'hbank.hex';p.write_text('@0\n'+'0'*64+'\n')
            with self.assertRaisesRegex(ValueError,'changed'):
                extract(p,'0'*64)

    def test_missing_and_duplicate_address_refused(self):
        for body in ('@1\n'+'0'*64+'\n','@0\n'+'0'*64+'\n@0\n'+'1'*64+'\n'):
            with self.subTest(body=body[:3]),tempfile.TemporaryDirectory() as d:
                p=Path(d)/'hbank.hex';p.write_text(body)
                with self.assertRaisesRegex(ValueError,'missing/duplicate'):
                    extract(p,hashlib.sha256(p.read_bytes()).hexdigest())

    def test_incomplete_image_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'hbank.hex';p.write_text('@0\n'+'0'*64+'\n')
            with self.assertRaisesRegex(ValueError,'incomplete'):
                extract(p,hashlib.sha256(p.read_bytes()).hexdigest())

    def test_existing_artifact_never_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'hbank.source';write_exclusive(p,b'first')
            with self.assertRaises(FileExistsError):write_exclusive(p,b'second')
            self.assertEqual(p.read_bytes(),b'first')
            self.assertEqual(list(Path(d).iterdir()),[p])


if __name__=='__main__':unittest.main()
