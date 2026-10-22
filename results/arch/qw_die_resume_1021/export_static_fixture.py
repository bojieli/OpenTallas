from pathlib import Path
import sys,json,re,hashlib
r=Path('/srv/opentallas-scratch/claude/mu-die-qw/dv2f21g5r10bfp');sys.path.insert(0,str(r/'src/tools'))
from qwen_split.source_pin_plan import rtl_ports
src=r/'src/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv'
p=rtl_ports(src,'qfd_d2d_static');lef=(r/'out/case/elements.lef').read_text();body=re.search(r'MACRO qfd_d2d_static\n(.*?)END qfd_d2d_static',lef,re.S).group(1)
actual={}
for pin in re.findall(r'\n  PIN (\S+)',body):
 if pin in ('VDD','VSS'):continue
 m=re.fullmatch(r'(.+)\[(\d+)\]',pin);assert m,pin
 actual.setdefault(m[1],[]).append(int(m[2]))
assert {n:sorted(bs)for n,bs in actual.items()}=={n:list(range(w))for n,(w,d)in p.items()}
physical={n:['pins',w]for n,(w,d)in p.items()};joins={};bits=[]
width=p['transport_fault'][0];del physical['transport_fault']
for b in range(width):
 alias=f'flt_transport_fault_{b}';physical[alias]=['pins',1];joins[alias]=['transport_fault',[b]];bits.append(dict(inst='d2d_rom',port=alias,real='transport_fault',bit=b))
print(json.dumps(dict(source_ports=p,physical_ports=physical,joins=joins,fault_bits=bits,rtl_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),case_LEF_sha256=hashlib.sha256(lef.encode()).hexdigest(),scope='Actual emitted RTL/LEF canonical bits, with exact SOURCE_BITS transport_fault scalar projection')))
