from pathlib import Path
p=Path('rtl/test/qwen_dv/tt_ctlm_prog_native32_bench.py');s=p.read_text();assert "'--x-assign', '0', '--x-initial', '0'"in s
s=s.replace("'--x-assign', '0', '--x-initial', '0'","'--x-assign', 'unique', '--x-initial', 'unique'")
needle="f'+NCYC={ncyc}']";assert needle in s
s=s.replace(needle,"f'+NCYC={ncyc}', '+verilator+rand+reset+2', '+verilator+seed+'+os.environ.get('HEAD_INIT_SEED','1')]")
Path('rtl/test/qwen_dv/tt_ctlm_prog_native32_rand_bench.py').write_text(s)
