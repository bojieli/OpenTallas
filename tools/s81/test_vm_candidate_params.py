import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import dsrom_s81_fulldie as G


class VMCandidate(unittest.TestCase):
    def test_default_has_no_override(self):
        with patch.object(G, 'VM_NATIVE_CANDIDATE', False):
            self.assertNotIn('dsfd_sp_vm', G.die_master_params(dict(insts=[SimpleNamespace(master='dsfd_sp_vm')])))

    def test_older_actual_wrapper_refuses_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv'
            p.parent.mkdir(parents=True)
            p.write_text('module dsfd_sp_vm #(parameter READ_PIPE=0, CAP_PIPE=0) (input ck); endmodule')
            with patch.object(G,'ROOT',root), self.assertRaisesRegex(ValueError,'actual READ_PIPE'):
                G.vm_native_candidate_params()

    def test_explicit_candidate_emits_all_three_params_only_when_present(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); p=root/'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv'
            p.parent.mkdir(parents=True)
            p.write_text('module dsfd_sp_vm #(parameter READ_PIPE=0, CAP_PIPE=0, WSCATTER_PIPE=0) (input ck); endmodule')
            with patch.object(G,'ROOT',root), patch.object(G,'VM_NATIVE_CANDIDATE',True):
                params=G.die_master_params(dict(insts=[SimpleNamespace(master='dsfd_sp_vm')]))['dsfd_sp_vm']
                self.assertEqual({k:v for k,v in params.items() if k!='_source'},dict(READ_PIPE=4,CAP_PIPE=2,WSCATTER_PIPE=1))
                with self.assertRaisesRegex(ValueError,'actual dsfd_sp_vm instance'):
                    G.die_master_params(dict(insts=[]))


if __name__=='__main__': unittest.main()
