import sys,importlib.util
from pathlib import Path
p=Path('/home/ubuntu/wt-claude-closure-daemon-1010/tools/ref_tile/pre_route_gate.py')
s=importlib.util.spec_from_file_location('s81_owned_gate_current',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.ROOT=m.RT.ROOT=Path('/home/ubuntu/wt/s81-gather-leaf-v18')
raise SystemExit(m.main())
