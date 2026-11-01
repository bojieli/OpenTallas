from pathlib import Path
import hashlib,json,shutil,sys
o=Path(__file__).resolve().parent;k=Path(sys.argv[1]);r=json.loads((o/'private_reset_provider.json').read_text())
p=k/'reset_tree.tcl';have=hashlib.sha256(p.read_bytes()).hexdigest()
if have not in [r['before_sha256'],r['after_sha256']]:raise SystemExit('reset tree source changed; scoped provider overlay refuses')
if have==r['before_sha256']:
 b=k/'prior_private_reset_provider';b.mkdir(exist_ok=True);shutil.copy2(p,b/'reset_tree.tcl')
 shutil.copy2(o/'reset_tree.private_provider.tcl',p)
for n in ['reset_provider.tcl','provider_contract.tcl']:shutil.copy2(o/n,k/n)
print('PRIVATE_PROVIDER_OVERLAY fourROM +15relative; startup NOT_QUALIFIED')
