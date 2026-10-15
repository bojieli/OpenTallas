#!/usr/bin/env python3
"""Actual production cap bench: PIPE1 and exactly one serial edge of added age."""
import sys, pathlib, subprocess, json, hashlib
out=pathlib.Path(sys.argv[1]).resolve()
PIPE=int(sys.argv[2]) if len(sys.argv)>2 else 1   # 2 = pure pin flops + decode stage, +2 serial vs legacy (claude F2 1015)
assert PIPE in (1,2)
out.mkdir(parents=True,exist_ok=False)
vm=pathlib.Path('rtl/dsrom_sys/s81_ph/vm')
for n in ['ot_s81_vm_x34.sv','dsfd_vm_static_capl.sv','dsfd_vm_static_capl_pipe.sv','dsfd_vm_static_capl_pre.sv','dsfd_vm_static_cap_leaf.sv','dsfd_vm_static_cap.sv']:
 (out/n).write_bytes((vm/n).read_bytes())
s=pathlib.Path('rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_static_cap.sv').read_text()
a='.ck(s_ck), .rst(rst), .cks(t_ck), .rss(rss)'
b='.ck_control_s(s_ck), .rst_control_s(rst), .ck_lane_s({16{s_ck}}), .ck_x34_s({16{s_ck}}), .rst_x34_s({16{rst}}), .ck_x34_t({16{t_ck}}), .rss_x34_t({16{rss}})'
assert s.count(a)==1;s=s.replace(a,b)
(out/'tb_dsfd_vm_static_cap.sv').write_text(s)
p=out/'tb_dsfd_vm_static_cap.sv';s=p.read_text()
a='dsfd_vm_static_cap #(.E(8))';b=f'dsfd_vm_static_cap #(.E(8), .CAP_PIPE({PIPE}))'
assert s.count(a)==1;s=s.replace(a,b)
assert s.count('q = p + 2;')==1;s=s.replace('q = p + 2;',f'q = p + {2+PIPE};')
if PIPE==2:   # NAT=1 3:4 transfer: stream output one more stream edge (claude F2 1015)
 assert s.count('t_of = 4 * (q / 3) + 2 + (q % 3);')==1;s=s.replace('t_of = 4 * (q / 3) + 2 + (q % 3);','t_of = 4 * (q / 3) + 3 + (q % 3);')   # PIPE serial edges added (claude F2: PIPE2 = +2)
p.write_text(s)
(out/'pipe_age_receipt.json').write_text(json.dumps(dict(source='de6ef76d6',PIPE=PIPE,default_PIPE=0,serial_age_delta=PIPE,II=1,bench_changes=[a+' -> '+b,f'q=p+2 -> q=p+{2+PIPE}'],x34_first_visibility=f'4*floor((P+{2+PIPE})/3)+{2+(PIPE==2)}+((P+{2+PIPE})%3); existing output checker +1 unchanged',native_clock_claim=False,hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.sv')}),indent=2)+'\n')
