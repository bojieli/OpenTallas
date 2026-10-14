#!/usr/bin/env python3
from pathlib import Path
import json
import rtl_w11_idx_array as A
A.IW=20
x=A.prepare_small(Path('debugvectors'),2,4,22)
print(json.dumps(x))
