import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import qwen_rom_combined_head_runtime_emit as head
import qwen_rom_combined_runtime_emit_initialized as common
import qwen_rom_combined_head_runtime_emit_initialized as composed
import qwen_rom_combined_head_launch_initialized as launch


class InitializedHeadTests(unittest.TestCase):
    def test_composition_initializes_all_models_before_every_initial_payload_write(self):
        old=head.emit()
        source=composed.emit()
        self.assertEqual(source,common.initialize_source(old))
        self.assertEqual(source.count('// INITIALIZATION_ABI '),1)
        self.assertEqual(source.count('// HEAD_HOST_ABI '),1)
        first_load=source.index('for (int d = 0; d < D; d++) load_images(mem[d], stages[0].dir[d]);')
        for eval in ('die[d]->eval();','coll.eval();','hbm[d]->eval();','fab[d]->eval();'):
            self.assertLess(source.index(eval),first_load)
        self.assertLess(first_load,source.index('// ---- preloads:'))
        self.assertIn('coll.clk=0; coll.rst_n=0;',source)
        self.assertIn('HEAD_RANK head die%d',source)
        self.assertIn('rm_vm(die[d]->rootp)[8192+i]',source)
        self.assertEqual(head.emit(),old)

    def test_expected_composed_source_pins_refuse_uninitialized_host_or_wrong_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            record=Path(directory)/'link.json'
            good=dict(returncode=0,archives_stable=True,
                generated_runtime_sha256=hashlib.sha256(composed.emit().encode()).hexdigest(),
                executable_sha256='unit-control-binary')
            book=dict(head_host_abi=composed.HEAD_ABI,initialization_abi=composed.INITIALIZATION_ABI,
                source_sha256={p:launch.predecessor.predecessor.sha(ROOT/p) for p in launch.SOURCES},
                head_link_record=str(record),executable_sha256='unit-control-binary')
            def set_record(value):
                record.write_text(json.dumps(value))
                book['head_link_record_sha256']=launch.predecessor.predecessor.sha(record)
            set_record(good)
            with patch.object(launch.predecessor,'BASE_VALIDATE',return_value=Path('not-executed')):
                self.assertEqual(launch.validate_selection(book),Path('not-executed'))
                for change in (dict(generated_runtime_sha256=hashlib.sha256(head.emit().encode()).hexdigest()),
                               dict(executable_sha256='wrong'),dict(returncode=1),dict(archives_stable=False)):
                    set_record(dict(good,**change))
                    with self.assertRaisesRegex(ValueError,'runtime source/binary'):
                        launch.validate_selection(book)

    def test_initializer_and_composer_source_pins_are_mandatory(self):
        book=dict(head_host_abi=composed.HEAD_ABI,initialization_abi=composed.INITIALIZATION_ABI,
                  source_sha256={p:launch.predecessor.predecessor.sha(ROOT/p) for p in launch.SOURCES})
        with patch.object(launch.predecessor,'BASE_VALIDATE',return_value=Path('not-executed')):
            for path in launch.SOURCES:
                changed=dict(book,source_sha256=dict(book['source_sha256'],**{path:'0'*64}))
                with self.assertRaisesRegex(ValueError,'source pin'):
                    launch.validate_selection(changed)
            changed=dict(book,initialization_abi='uninitialized')
            with self.assertRaisesRegex(ValueError,'initial-eval'):
                launch.validate_selection(changed)

    def test_cache_adapter_selects_initialized_validation_then_restores_predecessor(self):
        old=launch.predecessor.validate_head_runtime
        def observe(*args):
            self.assertIs(launch.predecessor.validate_head_runtime,launch.validate_selection)
            raise ValueError('control refusal, no launch')
        with patch.object(launch.predecessor,'prepare_from_inputs',side_effect=observe):
            with self.assertRaisesRegex(ValueError,'control refusal'):
                launch.prepare_from_inputs('book','cache','output')
        self.assertIs(launch.predecessor.validate_head_runtime,old)


if __name__=='__main__':unittest.main()
