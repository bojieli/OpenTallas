import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cached_readback', ROOT/'tools/qwen_rom_combined_readback.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CachedReadbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.oracle = self.root/'oracle'
        self.position = self.oracle/'P255'
        (self.position/'kv_at_P').mkdir(parents=True)
        self.run = self.root/'run'
        self.run.mkdir()
        self.baseline = self.root/'baseline.json'
        self.terminal = self.root/'terminal.json'
        self.log = self.root/'runtime.log'
        frame = dict(token=6280,layer_x_sha256={},kv_at_P_sha256={})
        preload = self.position/'x_preload.hex'
        words = '00000000\n'*4096
        preload.write_text('@0000\n'+words)
        frame['x_preload_sha256'] = m.sha(preload)
        for stage in ['E','L0','L1','L2']:
            for rank in range(4):
                key = f'{stage}_die{rank}'
                (self.run/(key+'_x.hex')).write_text(words)
                if stage == 'E':continue
                x = self.position/f'L{int(stage[1:]):02d}_die{rank}_x.hex'
                x.write_text(words)
                frame['layer_x_sha256'][key] = m.sha(x)
                kv = self.position/'kv_at_P'/(key+'.json')
                kv.write_text(json.dumps({'k_bits':['80000000']*256,'v_bits':['3f800000']*256}))
                frame['kv_at_P_sha256'][key] = m.sha(kv)
                (self.run/(key+'_kvP.hex')).write_text(''.join(
                    f'{kind} {h} {d} {code}\n' for kind,code in [('K','80'),('V','38')]
                    for h in range(2) for d in range(128)))
        (self.oracle/'oracle.json').write_text(json.dumps(dict(status='ISA_golden_only',tp=4,groups=6144,
            kv_format='fp8',layers=3,per_position={'255':frame})))
        self.baseline.write_text(json.dumps(dict(status='pass',source_stable=True,configuration='REAL_MEM',
            position=255,token=6280,stages_run=['E','L0','L1','L2'],oracle_json_sha256=m.sha(self.oracle/'oracle.json'))))
        self.receipt = dict(returncode=0,status='runtime_exit_zero',position=255,token=6280,layers=[0,1,2],
            command=['binary','--stages','stages',str(self.run)],input_sha256={str(self.baseline):m.sha(self.baseline)})
        self.terminal.write_text(json.dumps(self.receipt))
        self.log.write_text('QWEN_ROM_COMBINED PASS stages=4 cycles=1\n')

    def check(self):
        return m.check(self.terminal,self.baseline,self.oracle,self.run,self.log)

    def test_complete_selected_three_layers_all_four_ranks(self):
        r = self.check()
        self.assertEqual(r['status'],'pass')
        self.assertEqual(len(r['layer_x_checks']),16)
        self.assertEqual(len(r['token_kv_writeback_checks']),12)

    def test_each_rank_last_layer_x_and_kv_mutants_fail(self):
        for rank in range(4):
            x = self.run/f'L2_die{rank}_x.hex'
            original = x.read_text()
            x.write_text(original[:-9]+'80000000\n')
            self.assertEqual(self.check()['status'],'fail')
            x.write_text(original)
            kv = self.run/f'L2_die{rank}_kvP.hex'
            original = kv.read_text()
            kv.write_text(original.replace('V 1 127 38','V 1 127 00'))
            self.assertEqual(self.check()['status'],'fail')
            kv.write_text(original)

    def test_missing_and_truncated_outputs_refuse_or_fail(self):
        p = self.run/'E_die3_x.hex'
        p.write_text('00000000\n')
        self.assertEqual(self.check()['status'],'fail')
        p.unlink()
        with self.assertRaises(OSError):self.check()

    def test_duplicate_kv_coordinate_and_unknown_kind_refuse(self):
        p = self.run/'L1_die2_kvP.hex'
        original = p.read_text()
        for change in (original.replace('K 0 1 80','K 0 0 80'),original.replace('K 0 1 80','Z 0 1 80')):
            p.write_text(change)
            with self.assertRaises(ValueError):self.check()

    def test_changed_golden_oracle_and_baseline_refuse(self):
        for p in (self.position/'L02_die3_x.hex',self.oracle/'oracle.json',self.baseline):
            original=p.read_bytes()
            p.write_bytes(original+b'\n')
            with self.assertRaises(ValueError):self.check()
            p.write_bytes(original)

    def test_terminal_count_exit_and_output_binding_refuse(self):
        for key,value in [('returncode',1),('layers',[0,1,2,3]),('token',0),
                          ('command',['binary','--stages','stages','wrong'])]:
            receipt=dict(self.receipt);receipt[key]=value
            self.terminal.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):self.check()
        self.terminal.write_text(json.dumps(self.receipt))
        self.log.write_text('QWEN_ROM_COMBINED PASS stages=3\n')
        with self.assertRaises(ValueError):self.check()

    def test_existing_e4m3_signed_zero_and_unsupported_bits(self):
        convert=m.existing_e4m3()
        self.assertEqual([convert(v) for v in (0,0x80000000,0x3f800000)],[0,128,56])
        with self.assertRaises(ValueError):convert(0x3f800001)


if __name__ == '__main__':unittest.main()
