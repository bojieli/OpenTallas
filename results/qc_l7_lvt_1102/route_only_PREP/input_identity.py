from pathlib import Path
import hashlib,json
expected={'LVT_DATA_GEOMETRY_CHECKPOINT.odb': 'ed1fe2db2277f10b7c9726f631c6e61fd68bb36ccc0dcb1b4cb75fdde1e74110', 'constraint.sdc': '2567d64ff6f72a858cfb7d417769fc3fd61aeeac276e6c26664c50b101033ebf', 'config.mk': 'f9d3e56a2ea1345bae5483771bc3d38900e1711edce41ab10b79ef7d26d7ab2c', 'orfs_hold_mm.py': '65338108b9d94a62af8167f7232a2d1996d8057b2644bdd1baf43ab2f0f3d40e', 'orfs_hold_mm.tcl': '45e004f796e67435f9539914dcc3594e2267e8a0616c8d59623d290cad983ab1'}
actual={name:hashlib.sha256((Path('/work')/name).read_bytes()).hexdigest() for name in expected}
assert actual==expected,actual
Path('/route/INPUT_IDENTITY.json').write_text(json.dumps(actual,indent=2))
