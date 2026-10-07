#!/usr/bin/env python3
"""Synthetic gate tests only: fixtures are not physical closure evidence."""
import json
import tempfile
import unittest
from pathlib import Path
from qwen_embedding_parent_binding import sha,alias_bytes,qualify,verify_binding


class BindingGate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.view=self.root/'qfd_embed_ingress_code';self.view.mkdir()
        self.receipt=self.root/'receipt';self.receipt.mkdir();self.pin='1'*40
        self.name=self.view.name;top='ot_qwen_embedding_ingress_island'
        raw=self.view/'export_original';raw.mkdir()
        originals={};files={}
        for suffix in ('.lef','_ss.lib','_ff.lib'):
            text=(f'MACRO {top}\n  SIZE 15.12 BY 15.12 ;\nEND {top}\n' if suffix=='.lef'
                  else f'library (fixture) {{ cell ("{top}") {{ area : 1; }} }}\n')
            path=self.view/(self.name+suffix);(raw/path.name).write_text(text)
            originals[path.name]=sha(raw/path.name)
            path.write_bytes(alias_bytes(text.encode(),suffix,top,self.name));files[path.name]=sha(path)
        (self.view/'interface.sdc').write_text('# SYNTHETIC TEST FIXTURE ONLY\n')
        physical={k:'2'*64 for k in ('odb_sha256','spef_sha256','sdc_sha256')}
        self.abstract=dict(ok=True,source_commit=self.pin,source_artifacts=physical,files=files,
            interface_sdc=dict(sha256=sha(self.view/'interface.sdc')),
            identifier_alias=dict(source_top=top,target_top=self.name,original_sha256=originals))
        self.corner={k:dict(worst_slack_ps=20,errors=[],**physical) for k in ('setup_ss','hold_ff')}
        self.write(self.view/'abstract.json',self.abstract)
        self.write(self.receipt/'corner_sta.json',self.corner)
        self.write(self.receipt/'metadata_storage.json',dict(verdict='PASS',width=12,
            counts=dict(address_q=12,address_n=12,valid_q=1,valid_n=1,credit_q=1,credit_n=1)))
        self.evidence=dict(source_commit=self.pin,drc=0,exactness_pass=True)
        self.refresh_evidence()
        for c in ('ss','ff'):
            (self.receipt/f'w18_sta_{c}.log').write_text('QDM reference pin valid_q/CLK clock arrival max 37 min 34 skew 90 hold 50\n')
        self.bind()

    def tearDown(self):self.tmp.cleanup()
    def write(self,p,value):p.write_text(json.dumps(value,indent=2)+'\n')
    def refresh_evidence(self):
        for file in ('corner_sta','metadata_storage'):
            self.evidence[file+'_sha256']=sha(self.receipt/(file+'.json'))
        self.write(self.receipt/'qualification.json',self.evidence)
    def bind(self):
        self.write(self.root/'binding.json',qualify('code',self.view,self.receipt,self.pin))
        (self.root/'clock_reference.tcl').write_text('set embedding_ref_internal_setup_ps 37.000000000\nset embedding_ref_internal_hold_ps 34.000000000\n')
    def verify(self):return verify_binding('code',self.view,self.receipt,self.pin)
    def test_complete_fixture(self):self.assertFalse(self.verify()['parent_physical_closed'])
    def test_missing_view(self):
        (self.view/(self.name+'_ff.lib')).unlink()
        with self.assertRaisesRegex(ValueError,'absent'):self.verify()
    def test_stale_clock(self):
        (self.root/'clock_reference.tcl').write_text('set embedding_ref_internal_setup_ps 0\nset embedding_ref_internal_hold_ps 0\n')
        with self.assertRaisesRegex(ValueError,'stale parent clock'):self.verify()
    def test_failed_corner(self):
        self.corner['hold_ff']['worst_slack_ps']=-23.65
        self.write(self.receipt/'corner_sta.json',self.corner);self.refresh_evidence()
        with self.assertRaisesRegex(ValueError,'not qualified'):self.verify()
    def test_nan_corner(self):
        self.corner['hold_ff']['worst_slack_ps']=float('nan')
        self.write(self.receipt/'corner_sta.json',self.corner);self.refresh_evidence()
        with self.assertRaisesRegex(ValueError,'not qualified'):self.verify()
    def test_non_identifier_edit_even_with_updated_hash(self):
        p=self.view/(self.name+'_ss.lib');p.write_text(p.read_text().replace('area : 1','area : 2'))
        self.abstract['files'][p.name]=sha(p);self.write(self.view/'abstract.json',self.abstract)
        with self.assertRaisesRegex(ValueError,'beyond top identifier'):self.verify()
    def test_missing_raw_export(self):
        (self.view/'export_original'/(self.name+'.lef')).unlink()
        with self.assertRaisesRegex(ValueError,'original export missing'):self.verify()
    def test_changed_physical_hash(self):
        self.corner['hold_ff']['odb_sha256']='3'*64
        self.write(self.receipt/'corner_sta.json',self.corner);self.refresh_evidence()
        with self.assertRaisesRegex(ValueError,'physical source mismatch'):self.verify()
    def test_relocation(self):
        import shutil
        new=self.root/'moved';new.mkdir()
        for name in (self.name,'receipt','binding.json','clock_reference.tcl'):shutil.move(str(self.root/name),str(new/name))
        self.assertFalse(verify_binding('code',new/self.name,new/'receipt')['parent_physical_closed'])
    def test_approved_padded_alias(self):
        source='ot_qwen_embedding_ingress_padded'
        self.assertEqual(alias_bytes(f'cell ("{source}") {{}}'.encode(),'_ss.lib',source,self.name),f'cell ("{self.name}") {{}}'.encode())
    def make_padded(self):
        old='ot_qwen_embedding_ingress_island';new='ot_qwen_embedding_ingress_padded'
        self.abstract['identifier_alias']['source_top']=new
        for suffix in ('.lef','_ss.lib','_ff.lib'):
            p=self.view/'export_original'/(self.name+suffix)
            p.write_text(p.read_text().replace(old,new))
            self.abstract['identifier_alias']['original_sha256'][p.name]=sha(p)
        self.write(self.view/'abstract.json',self.abstract)
        meta=json.loads((self.receipt/'metadata_storage.json').read_text())
        meta.update(input_padding=dict(stages_per_input=6,input_bits=15,fixed_buffer_cells=90,
            cell_type='BUFx2_ASAP7_75t_R',connectivity_verified=True),netlist_sha256='4'*64)
        self.write(self.receipt/'metadata_storage.json',meta)
        self.write(self.receipt/'metadata_storage_synthesis.json',meta)
        self.evidence.update(routed_netlist_sha256='4'*64,synthesis_netlist_sha256='4'*64,
            metadata_storage_synthesis_sha256=sha(self.receipt/'metadata_storage_synthesis.json'))
        self.refresh_evidence();self.bind()
    def test_padded_topology_fixture(self):
        self.make_padded();self.assertEqual(self.verify()['input_padding']['fixed_buffer_cells'],90)
    def test_missing_synthesis_padding_receipt(self):
        self.make_padded();(self.receipt/'metadata_storage_synthesis.json').unlink()
        with self.assertRaisesRegex(ValueError,'synthesis pad topology receipt'):self.verify()
    def test_stale_routed_netlist(self):
        self.make_padded();self.evidence['routed_netlist_sha256']='5'*64;self.refresh_evidence()
        with self.assertRaisesRegex(ValueError,'not bound to the final netlist'):self.verify()
    def test_unknown_top(self):
        with self.assertRaisesRegex(ValueError,'unapproved'):alias_bytes(b'cell (proxy) {}','_ss.lib','proxy',self.name)

if __name__=='__main__':unittest.main()
