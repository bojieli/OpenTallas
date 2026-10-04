import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import qwen_rom_combined_nearbaseline_runtime_emit as runtime
import qwen_rom_combined_nearbaseline_access as access
import qwen_rom_combined_nearbaseline_link as link
import qwen_rom_combined_nearbaseline_selection as selection


class NearRuntimeTests(unittest.TestCase):
    def test_first_eval_precedes_all_payload_writes_and_real_ports_remain(self):
        original = runtime.initialized.predecessor.BASE_SHA
        text = runtime.emit(ROOT)
        self.assertEqual(runtime.initialized.predecessor.BASE_SHA, original)
        first = text.index('for(int d=0;d<D;++d)fab[d]->eval();')
        for write in ('load_images(mem[d], stages[0].dir[d])', 'rm_vm(r)[i] =',
                      'rm_embed_codes(r)[', 'preload_die_roms(*die[d]',
                      'preload_tile_roms(*fab[d]', 'preload_hbm(*die[d]'):
            self.assertLess(first, text.index(write))
        self.assertIn('stages.size()!=1 || stages[0].layer<0', text)
        self.assertIn('POS<0 || POS>=8192 || kv_dir.empty()', text)
        self.assertIn('(m.desc[0]&3)!=3', text)
        self.assertIn('layer_fences[d].can_retire(sample(d))', text)
        self.assertIn('die[d]->nhb_active_o', text)
        self.assertIn('hbm[d]->wire()', text)

    def test_changed_current_fixed_host_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = root/runtime.initialized.predecessor.BASE
            p.parent.mkdir(parents=True)
            p.write_text('different host')
            with self.assertRaisesRegex(ValueError, '157 preload host changed'):
                runtime.emit(root)

    def test_actual_root_resolver_restores_real_member_names(self):
        with tempfile.TemporaryDirectory() as temp:
            t = Path(temp);header = t/'die.h'
            names = [access.TOP+'__DOT__'+x for x in ('vm','prog_mem','desc_mem','crom_mem','crom_words')]
            names += [access.TOP+'__DOT__g_sc__BRA__0__KET____DOT__u_bank__DOT__g_m__BRA__0__KET____DOT__u_rom__DOT__arr']
            header.write_text('\n'.join(n+';' for n in names))
            tile = t/'tile.h'
            tile.write_text('\n'.join('tile__DOT__g_col__BRA__'+str(p)+'__KET____DOT__g_bank__BRA__0__KET____DOT__u_rom__DOT__arr;' for p in range(2))+'\n'+
                            '\n'.join('tile__DOT__g_kv__BRA__'+str(p)+'__KET____DOT__u_kv__DOT__arr;' for p in range(2)))
            hbm = t/'hbm.h';hbm.write_text('hbm__DOT__mem;')
            access.emit(header,tile,hbm,t/'out',nport=1,scale_banks=1,code_banks=1,crom_words=64,hbm_layers=36,embed_rom=0)
            result=(t/'out/combined_access.hpp').read_text()
            self.assertIn(access.TOP+'__DOT__vm',result)
            self.assertNotIn(access.BASE_TOP+'__DOT__',result)
            header.write_text(header.read_text().replace(access.TOP,access.BASE_TOP))
            with self.assertRaisesRegex(ValueError,'nearbaseline generated root'):
                access.emit(header,tile,hbm,t/'wrong',nport=1)

    def test_protected_selection_rejects_old_near0_model(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp);p=t/'models.json'
            p.write_text(json.dumps(dict(top='ot_qwen_rom_combined_die',parameters=dict(NEAR_HBM=0))))
            with self.assertRaisesRegex(ValueError,'mandatory NEAR1 top'):
                selection.create(ROOT,ROOT,p,t,{},t/'selection.json')

    def test_all_actual_generated_hierarchy_libs_required(self):
        with tempfile.TemporaryDirectory() as temp:
            t=Path(temp)
            (t/'Vdie__verFiles.dat').write_text(runtime.TOP)
            (t/'Vdie_hier.mk').write_text('VM_HIER_LIBS := extra/libextra.a\n')
            (t/'Vdie__ALL.a').write_bytes(b'!<arch>\n')
            build=dict(die=['-GNEAR_HBM=1'])
            with self.assertRaises(FileNotFoundError):link.require_selected_models(build,t)
            (t/'extra').mkdir();(t/'extra/libextra.a').write_bytes(b'!<arch>\n')
            self.assertEqual(link.require_selected_models(build,t)['NEAR_HBM'],1)
            with self.assertRaisesRegex(ValueError,'NEAR_HBM=1'):
                link.require_selected_models(dict(die=['-GNEAR_HBM=0']),t)

    def test_failed_link_restores_canonical_modules(self):
        emitter,accessor=link.predecessor.emitter,link.predecessor.access
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'params.json';p.write_text('{}')
            with patch.object(sys,'argv',['link','--die-build',temp,'--compiled-params',str(p),'--out',temp]), \
                 patch.object(link,'require_selected_models',return_value={}), \
                 patch.object(link.predecessor,'main',side_effect=RuntimeError('compiler failed')):
                with self.assertRaisesRegex(RuntimeError,'compiler failed'):link.main()
        self.assertIs(link.predecessor.emitter,emitter)
        self.assertIs(link.predecessor.access,accessor)


if __name__ == '__main__':unittest.main()
