#!/usr/bin/env python3
"""Fixed-profile causal negative: sticky core fault cannot reset after poison."""
import hashlib,re,sys
from pathlib import Path
p=Path('rtl/hdc/nearhbm/qkd_ahub_static_dw_safe_native.v');s=p.read_text()
assert hashlib.sha256(s.encode()).hexdigest()=='e215df81353e6ba546c0865945e53e60b772f891a76a1ca833f2c2744e83b7b8'
lines=s.splitlines();changed=0
for i,line in enumerate(lines):
 if ' safe_c7351 ' in line:
  assert 'DFFASRHQNx1_ASAP7_75t_R' in line
  lines[i],changed=re.subn(r'\.\\RESETN \([^)]*\)',lambda m:".\\RESETN (1'b1)",line)
assert changed==1
Path(sys.argv[1]).write_text('\n'.join(lines)+'\n')
