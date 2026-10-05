"""Source-only narrow-provider contract checks; no native runtime fixture."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tools/runtime/dsrom/s81_source_selection_restore.hpp'

class SelectionRestoreContract(unittest.TestCase):
    def test_actual_scope_and_inactive_no_copy(self):
        s=SOURCE.read_text()
        start=s.index('if(action.layer==20)')
        end=s.index('require(action.layer==19',start)
        branch=s[start:end]
        self.assertIn('!retained_source && !actual_copy',branch)
        self.assertIn('return;',branch)
        self.assertNotIn('transfer.reset',branch)
        self.assertIn('action.required && action.source_layer==14',s)
        self.assertIn('action.before_instruction==7',s)
        self.assertIn('bool opt_in=false',s)
    def test_full512_rank_homes_not_aliases(self):
        s=SOURCE.read_text()
        self.assertIn('selection_words = 512',s)
        self.assertIn('selection_address = 447360',s)
        for rank in range(4):
            self.assertEqual((112+rank)//4,28)
            self.assertEqual((152+rank)//4,38)
            self.assertNotEqual(112+rank,152+rank)
        for check in ('destination.die_id==int(152+rank)',
                      'source.offer.die_id==int(112+rank)',
                      's.producer_identity==source.offer.identity',
                      's.words==selection_words'):
            self.assertIn(check,s)
    def test_missing_source_refuses_and_catalogue_not_native_pc(self):
        s=SOURCE.read_text()
        self.assertIn('require(retained_source && actual_copy',s)
        self.assertIn('source.source_node=="L14.I63"',s)
        self.assertIn('d0ca14372349ed80e998c5140108eaf4796bb1ed121c3b5529e9729abd4e6c79',s)
        self.assertIn('source.publication_retained(source.offer,source.native_writer)',s)
        self.assertNotIn('native_writer=1792',s)
        self.assertNotIn('source.offer.identity=destination.identity',s)
    def test_native_owner_and_both_visibility_fences_preserved(self):
        s=SOURCE.read_text()
        self.assertIn('b.native_copy_visible && !b.transfer_accepted',s)
        self.assertIn('source_lease(id,address,n)',s)
        self.assertIn('new DsromS81SourceIoTransferHooks',s)
        self.assertIn('std::move(all_copies_drained)',s)
        self.assertIn('transfer->restore(accepted)',s)
        self.assertIn('transfer->drain(accepted)',s)
        self.assertNotIn('read_word(',s)  # native copy already owns prefetch
        self.assertNotIn('native_scalar(',s)  # no duplicate payload capture
        self.assertNotIn('enroll_literal(',s)
        self.assertNotIn('.begin(',s)
    def test_no_parent_ready_fabrication(self):
        s=SOURCE.read_text()
        self.assertIn('Inactive, Waiting, Published',s)
        self.assertIn('if(!transfer)return SelectionRestoreResult::Inactive;',s)
        self.assertIn('o.entry==destination.entry',s)
        self.assertIn('o.epoch==destination.epoch',s)
        self.assertIn('catch(...){stopped=true;throw;}',s)
        self.assertNotIn('vm_word',s)

if __name__=='__main__': unittest.main()
