import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import qwen_rom_combined_runtime_emit as original
import qwen_rom_combined_head_runtime_emit as head
import qwen_rom_combined_head_launch as launch


class HeadHostTests(unittest.TestCase):
    def test_original_pinned_host_and_emitter_remain_unchanged(self):
        self.assertEqual(hashlib.sha256((ROOT/original.BASE).read_bytes()).hexdigest(),original.BASE_SHA)
        before=original.emit()
        successor=head.emit()
        self.assertEqual(original.emit(),before)
        self.assertNotIn('HEAD_HOST_ABI',before)
        self.assertIn('HEAD_HOST_ABI combined-head-host-v1',successor)

    def test_actual_hardware_results_no_kv_head_and_norm_readback(self):
        source=head.emit()
        self.assertIn('else if (st.name == "head") st.layer = -1;',source)
        self.assertIn('const bool embed_stage = stages[0].name == "E";',source)
        self.assertIn('if (!kv_ideal && stages[cur].layer >= 0)',source)
        self.assertIn('die[d]->rm_layer = uint8_t(stages[cur].layer);',source)
        self.assertIn('layer_fences[d].begin(unsigned(uint8_t(stages[cur].layer)),POS,TOKEN);',source)
        self.assertIn('die[d]->seq_ntok!=die[0]->seq_ntok || die[d]->seq_nval!=die[0]->seq_nval',source)
        self.assertIn('rm_vm(die[d]->rootp)[8192+i]',source)
        self.assertIn('head_die',source)
        self.assertNotIn('rm_layer = 36',source)

    def test_fulltoken_stage_contract_rejects_alias_reorder_and_kv_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            dirs=[root/f'd{d}' for d in range(4)]
            for d in dirs:d.mkdir()
            paths=' '.join(map(str,dirs))
            names=['E']+[f'L{l}' for l in range(36)]+['head']
            text='\n'.join(f'{n} {paths} {0 if n in ("E","head") else 1}' for n in names)+'\n'
            stage=root/'stages.txt'
            stage.write_text(text)
            self.assertEqual(launch.layers_from_stages(stage),list(range(36)))
            for bad in (text.replace('head ','L36 '),text.replace('head ','H '),
                        text.replace('L35 ','L34 '),text.replace(f'head {paths} 0',f'head {paths} 1'),
                        '\n'.join(text.splitlines()[:-1]),text+f'head {paths} 0\n'):
                stage.write_text(bad)
                with self.subTest(text=bad[-100:]),self.assertRaises(ValueError):
                    launch.layers_from_stages(stage)

    def test_existing_rtl_rank_order_strict_tie_contract_and_no_kv_sentinel(self):
        sequence=(ROOT/'rtl/rom/ot_qwen_tp_seq_w12.sv').read_text()
        self.assertIn('if (r_rank != rx_k[RB-1:0]) fault <= 1\'b1;',sequence)
        self.assertIn('okey(g_val) > okey(best_v)',sequence)
        self.assertIn('core_next_token + row0',sequence)
        fence=(ROOT/'tools/runtime/qwen_combined/combined_driver.hpp').read_text()
        self.assertIn('if(layer_==255)return kv_starts_==0 && service_starts_==0;',fence)

    def test_cache_adapter_failed_baselines_do_not_replace_source_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            oracle=root/'oracle.json'
            preload=root/'preload.hex';preload.write_text('@0\n00000000\n')
            oracle.write_text(json.dumps(dict(status='ISA_golden_only',layers=36,head=True,tp=4,
                groups=6144,kv_format='fp8',per_position={'255':dict(token=6280,
                x_preload_sha256=launch.predecessor.sha(preload))})))
            compiled=root/'compiled.json';compiled.write_text('{}')
            link=root/'link.json';link.write_text(json.dumps(dict(compiled_params_sha256=launch.predecessor.sha(compiled))))
            book=root/'book.json';book.write_text(json.dumps(dict(head_link_record=str(link))))
            embedding=root/'embedding.bin';embedding.write_bytes((6280).to_bytes(4,'little')+bytes(4098))
            inputs=dict(schema='opentallas.qwen-rom-full36-inputs.v1',position=255,token=6280,
                oracle=dict(root=str(root),sha256=launch.predecessor.sha(oracle)),
                stages=[dict(name=n) for n in ['E']+[f'L{l}' for l in range(36)]+['head']],
                compiled_extent=dict(hbm_layers=36,memory_words_per_stack=4718592,
                    path=str(compiled),sha256=launch.predecessor.sha(compiled)),
                preload=dict(path=str(preload),sha256=launch.predecessor.sha(preload)),
                embedding=dict(raw=str(embedding),sha256=launch.predecessor.sha(embedding)),
                history={},baseline_pending=['L3'],baselines={'L3':{'status':'fail'}})
            receipt=root/'inputs.json';receipt.write_text(json.dumps(inputs))
            output=root/'output'
            with patch.object(launch,'validate_head_runtime',return_value=root/'not-executed'):
                # A failed prior stage is retained, not fabricated into PASS.
                # It cannot replace missing cached history: coverage still refuses.
                with self.assertRaisesRegex(ValueError,'all144'):
                    launch.prepare_from_inputs(book,receipt,output)
                inputs['stages'][-1]['name']='L36'
                receipt.write_text(json.dumps(inputs))
                with self.assertRaisesRegex(ValueError,'stage order'):
                    launch.prepare_from_inputs(book,receipt,output)
                inputs['stages'][-1]['name']='head'
                link.write_text(json.dumps(dict(compiled_params_sha256='wrong')))
                receipt.write_text(json.dumps(inputs))
                with self.assertRaisesRegex(ValueError,'compiled extent differs'):
                    launch.prepare_from_inputs(book,receipt,output)
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
