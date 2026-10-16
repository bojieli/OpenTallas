#!/usr/bin/env python3
"""Emit the full53-source/3-slot/16384-bit payload33 front differential fixture.
Uses unchanged original A2 reference and the proven threshold/metadata front
fixture; independent-root reset/global-OR coverage is in the epoch OR gate.
"""
import pathlib,json,hashlib,sys
import area_a2f_split4m_gate as M
G=M.G
G.SOURCES += ['rtl/dsrom_sys/s81_ph/vm/dsfd_vm_a2f_payload33.sv','tools/s81_vm/area_a2f_payload33_composed.sv']
s=G.BENCH.replace('s81_a2f_controlled_split4m dut(', 's81_a2f_controlled_split4m_payload33 dut(')
a=s.index('s81_a2f_controlled_split4m_payload33 dut(');b=s.index(' integer cycle',a)
s=s[:a]+s[a:b].replace('.ck_payload({4{ck}})', '.ck_payload({16{ck}})').replace('.rst_payload_n({4{rst}})', '.rst_payload_n({16{rst}})')+s[b:]
o=pathlib.Path(sys.argv[1]);o.mkdir(parents=True,exist_ok=True);(o/'bench.sv').write_text(s)
(o/'sources.txt').write_text('\n'.join(G.SOURCES)+'\n')
(o/'source_hashes.json').write_text(json.dumps({p:hashlib.sha256((G.ROOT/p).read_bytes()).hexdigest() for p in G.SOURCES+['tools/s81_vm/a2f_payload33_front_gate.py','tools/s81_vm/area_a2f_split4m_gate.py','tools/s81_vm/area_a2f_split4_equiv_gate.py']},indent=1)+'\n')
print('PAY33_FRONT emitted',len(G.SOURCES),'RTL files',o)
