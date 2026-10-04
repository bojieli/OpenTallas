import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

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


if __name__=='__main__':unittest.main()
