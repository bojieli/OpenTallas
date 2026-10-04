import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_combined_head_readback as m


class FullTokenReadbackTests(unittest.TestCase):
    def test_full_token_and_last_rank_head_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); oracle=root/'oracle'; pos=oracle/'P255'; run=root/'run'
            (pos/'kv_at_P').mkdir(parents=True);run.mkdir()
            words='00000000\n'*4096
            (pos/'x_preload.hex').write_text(words)
            frame=dict(token=6280,x_preload_sha256=m.sha(pos/'x_preload.hex'),
                       layer_x_sha256={},kv_at_P_sha256={},head=dict(next_token=98951,next_logit_bits='42098785'))
            for rank in range(4):
                (run/f'E_die{rank}_x.hex').write_text(words)
                key=f'head_die{rank}'
                (pos/(key+'_xnorm.hex')).write_text(words)
                (run/(key+'_xnorm.hex')).write_text(words)
                (run/(key+'_result.hex')).write_text('00018287 42098785\n')
                frame['head'][key]=dict(xnorm_sha256=m.sha(pos/(key+'_xnorm.hex')))
                for layer in range(36):
                    key=f'L{layer}_die{rank}'
                    expected=pos/f'L{layer:02d}_die{rank}_x.hex';expected.write_text(words)
                    (run/(key+'_x.hex')).write_text(words)
                    frame['layer_x_sha256'][key]=m.sha(expected)
                    expected=pos/'kv_at_P'/(key+'.json')
                    expected.write_text(json.dumps(dict(k_bits=['00000000']*256,v_bits=['00000000']*256)))
                    frame['kv_at_P_sha256'][key]=m.sha(expected)
                    (run/(key+'_kvP.hex')).write_text(''.join(f'{k} {h} {d} 00\n'
                        for k in ('K','V') for h in range(2) for d in range(128)))
            oracle_file=oracle/'oracle.json'
            oracle_file.write_text(json.dumps(dict(status='ISA_golden_only',tp=4,groups=6144,kv_format='fp8',
                layers=36,head=True,per_position={'255':frame})))
            terminal=root/'terminal.json';terminal.write_text(json.dumps(dict(status='runtime_exit_zero',returncode=0,
                layers=list(range(36)),position=255,token=6280,command=['bin','--stages','stages',str(run)])))
            log=root/'log';log.write_text(''.join(f'HEAD_RANK head die{r} next_token=98951 next_val=42098785\n'
                for r in range(4))+'QWEN_ROM_COMBINED PASS stages=38 cycles=1\n')
            def check():return m.check(terminal,oracle,m.sha(oracle_file),run,log)
            verdict=check();self.assertEqual(verdict['status'],'pass')
            self.assertEqual(len(verdict['layer_x_checks']),148)
            self.assertEqual(len(verdict['token_kv_writeback_checks']),144)
            (run/'head_die3_result.hex').write_text('00018287 42098784\n')
            self.assertEqual(check()['status'],'fail')
            (run/'head_die3_result.hex').write_text('00018287 42098785\n')
            log.write_text('QWEN_ROM_COMBINED PASS stages=4\n')
            with self.assertRaises(ValueError):check()


if __name__=='__main__':unittest.main()
