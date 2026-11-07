from pathlib import Path
import hashlib
p=Path(__file__).parent
s=p.joinpath('gold.v').read_text()
old="  assign _0856_ = \\u_control.u_control.u_host.u_core.c_reqs  + 1'h1;"
assert s.count(old)==1
out=s.replace(old,p.joinpath('carry_patch.txt').read_text().rstrip())
assert out==p.joinpath('new.v').read_text()
print('Reproduction exact SHA256',hashlib.sha256(out.encode()).hexdigest())
