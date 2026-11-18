"""Selected current token path and layer floor must reach the pair compiler."""
from pathlib import Path
from tempfile import TemporaryDirectory
import gzip,json,os,subprocess,unittest
SCRIPT=Path(__file__).with_name('d2d_cal_image_production.sh')
class TestSourceInputs(unittest.TestCase):
    def run_case(self,selected=None,floor=None):
        with TemporaryDirectory() as tmp:
            t=Path(tmp);tools=t/'bin';tools.mkdir()
            py=tools/'python3';py.write_text('''#!/usr/bin/python3
import sys,json,pathlib
if sys.argv[1].endswith('d2d_link_calendar.py'):
 p=pathlib.Path(sys.argv[sys.argv.index('--out')+1]);p.mkdir(parents=True,exist_ok=True)
 (p/'args.json').write_text(json.dumps(sys.argv[2:]))
else:pathlib.Path(sys.argv[3]).write_text('selected image')
''');py.chmod(0o755)
            legacy=t/'results/rtl/qwen_layer_tput_1018/compiled_L1/d2d/token_path_compiled.json.gz';legacy.parent.mkdir(parents=True)
            legacy.write_bytes(gzip.compress(b'{"legacy":true}'))
            env={k:v for k,v in os.environ.items() if not k.startswith('D2D_')}
            env.update(PATH=str(tools)+':'+os.environ['PATH'],D2D_KV_CODEC='2')
            for k in ('D2D_TOKEN_PATH','D2D_LAYER_PERIOD_MIN'):env.pop(k,None)
            expected=b'{"legacy":true}'
            if selected is not None:
                p=t/('selected.json.gz' if selected=='gz' else 'selected.json');expected=b'{"current_mif":1}'
                if selected!='missing':p.write_bytes(gzip.compress(expected) if selected=='gz' else expected)
                env['D2D_TOKEN_PATH']=str(p)
            if floor is not None:env['D2D_LAYER_PERIOD_MIN']=str(floor)
            out=t/'out';r=subprocess.run(['bash',str(SCRIPT),str(out)],cwd=t,env=env,capture_output=True,text=True)
            if selected=='missing':
                self.assertNotEqual(r.returncode,0);self.assertIn('selected token path missing',r.stderr);return
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual((out/'token_path_compiled.json').read_bytes(),expected)
            args=json.loads((out/'program/args.json').read_text())
            self.assertEqual(args[args.index('--token-path')+1],str(out/'token_path_compiled.json'))
            if floor is None:self.assertNotIn('--layer-period-min',args)
            else:self.assertEqual(args[args.index('--layer-period-min')+1],str(floor))
    def test_default_retains_legacy_path_and_no_floor(self):self.run_case()
    def test_selected_plain_and_gzip_feed_current_calendar(self):
        for mode in ('json','gz'):
            with self.subTest(mode=mode):self.run_case(mode,8020)
    def test_missing_selected_path_fails(self):self.run_case('missing')
if __name__=='__main__':unittest.main()
