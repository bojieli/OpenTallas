#!/usr/bin/env python3
import hashlib,json,re,shutil
from pathlib import Path
root=Path('/srv/opentallas-scratch2/claude/codex-s81kvleaf-2258')
source=Path('/srv/opentallas-scratch2/claude/s81-kits-d/ns')
records=[]
for t in (1,3,4,5):
    name=f'ot_s81sl_kv_leaf__t{t}';kit=source/name/name
    il=next((kit/'run/results/asap7').glob('*/base/1_1_yosys_canonicalize.rtlil'))
    text=il.read_text();rom=[]
    for match in re.finditer(r'(?ms)^module ([^\n]+)\n(.*?)^end$',text):
        module,body=match.groups()
        cells=[]
        for c in re.finditer(r'(?ms)^  cell (\S+) ([^\n]+)\n(.*?)^  end$',body):
            kind,inst,data=c.groups();mid=re.search(r'(?m)^    parameter \\MEMID "([^"]+)"$',data)
            if mid:cells.append((kind,inst,mid.group(1),data))
        for m in re.finditer(r'(?m)^  memory width (\d+) size (\d+) (\S+)$',body):
            width,rows,mid=m.groups();width,rows=int(width),int(rows)
            if width*rows<=6272:continue
            users=[c for c in cells if c[2]==mid]
            assert users,(name,module,mid,'no memory cells')
            assert not any(c[0].startswith('$memwr') for c in users),(name,module,mid,'runtime write')
            init=[c for c in users if c[0].startswith('$meminit')]
            assert init,(name,module,mid,'no const init')
            bits=[]
            for c in init:
                d=re.search(r"(?m)^    connect \\DATA (\d+)'([01]+)$",c[3]);assert d,(name,module,mid,'nonconstant init')
                assert int(d[1])==len(d[2]);bits.append(len(d[2]))
            assert sum(bits)==width*rows,(name,module,mid,bits)
            assert all(c[0].startswith(('$memrd','$meminit')) for c in users),(name,module,mid,'unexpected memory operation')
            rom.append(dict(module=module,memory=mid,width=width,rows=rows,constant_bits=sum(bits),runtime_write_ports=0))
    assert len(rom)==2,(name,rom)
    log=next((kit/'run/logs/asap7').glob('*/base/1_2_yosys.log')).read_text()
    largest=int(re.search(r'Largest single memory instance: (\d+) bits',log)[1]);assert largest==15616,(name,largest)
    dest=root/'kv_fix'/name
    assert not dest.exists(),dest
    shutil.copytree(kit,dest,copy_function=shutil.copy2)
    cfg=dest/'config.mk';c=cfg.read_text();assert c.count('export SYNTH_MEMORY_MAX_BITS = 6272')==1
    cfg.write_text(c.replace('export SYNTH_MEMORY_MAX_BITS = 6272','export SYNTH_MEMORY_MAX_BITS = 15616'))
    records.append(dict(type=name,canonical_sha256=hashlib.sha256(il.read_bytes()).hexdigest(),
                        optimized_largest_bits=largest,oversized_memories=rom,retry=str(dest),
                        scope='Only constant read-only arithmetic truth tables exceed previous6272; no runtime RAM added. Goal synth only; collect flat cell count before P&R.'))
runner=source/'ot_s81sl_kv_leaf__t1/run_kit.sh';shutil.copy2(runner,root/'kv_fix/run_kit.sh')
(root/'kv_constrom_proof.json').write_text(json.dumps(dict(verdict='PASS',types=records),indent=1)+'\n')
print(json.dumps(dict(verdict='PASS',types=len(records),constant_read_only=True,max_bits=15616)))
