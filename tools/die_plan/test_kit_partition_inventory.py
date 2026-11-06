import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from kit_topology import stage_inventory

class PartitionInventory(unittest.TestCase):
    def test_partition_freeze_uses_explicit_selected_module(self):
        with tempfile.TemporaryDirectory() as td:
            rtl=Path(td)/'rtl';kit=Path(td)/'kit';rtl.mkdir();kit.mkdir()
            source=rtl/'bound.sv';source.write_text('module selected; endmodule\n')
            census=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),problems=[],required_instances=[dict(inst='u_ist_A_0',master='ot_dp_st')])
            (rtl/'kit_topology.json').write_text(json.dumps(census))
            (kit/'freeze.json').write_text(json.dumps(dict(schema='opentallas.partition_freeze.v1',type='part')))
            with self.assertRaisesRegex(ValueError,'explicit selected parent module'):
                stage_inventory(rtl,kit)
            stage_inventory(rtl,kit,top='selected')
            actual=json.loads((kit/'kit_assembly.json').read_text())
            self.assertEqual(actual['parent_profile']['top'],'selected')
            self.assertEqual(actual['required_instances'],census['required_instances'])

if __name__=='__main__':unittest.main()
