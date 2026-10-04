import gzip,json,tempfile,unittest
from pathlib import Path
from h4_c0_ds_composite_captured_output_reference import records

class StreamingMetadataTests(unittest.TestCase):
    def test_record_strings_and_chunk_boundaries_preserved(self):
        values=[{'PC':115,'nested':{'text':'} , ] " '+'x'*70000}}, {'PC':443}, {'PC':776}]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bindings.json.gz';p.write_bytes(gzip.compress(json.dumps(values).encode()))
            self.assertEqual(list(records(p)),values)
    def test_incomplete_or_nonarray_metadata_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bindings.json.gz'
            for raw in [b'{"PC":115}',b'[{"PC":115}']:
                p.write_bytes(gzip.compress(raw))
                with self.assertRaises(ValueError):list(records(p))

if __name__=='__main__':unittest.main()
