#!/bin/bash
cd /srv/opentallas-scratch/claude/s81-l20rd3-1020/src3 && bash results/rtl/s81_l20rd2_1020/native/run.sh && cp native.log textbook.json mapped_attr.v yosys.log /srv/opentallas-scratch/claude/s81-l20rd3-1020/ 2>/dev/null; python3 -c "
import json;t=json.load(open('textbook.json'));r=t.get('refuse',{});print('NATIVE_REFUSE',{k:len(v) for k,v in r.items()})
for k,v in r.items():
  for x in v[:12]: print('  ',x[:220])
print('NATIVE_WARN',{k:len(v) for k,v in t.get('warn',{}).items()} if isinstance(t.get('warn'),dict) else t.get('warn'))"
