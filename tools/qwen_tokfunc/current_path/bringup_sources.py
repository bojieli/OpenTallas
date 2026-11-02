"""Compose the explicit quiescent QC bringup source list; never qualifies a token."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--code-files', type=Path, required=True)
p.add_argument('--table-overlay', type=Path, required=True)
p.add_argument('--phy-dir', type=Path, required=True)
p.add_argument('--vehicle', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
v = json.loads((a.vehicle / 'vehicle.json').read_text())
assert v['phy_bringup_only'] and v['core_period_ps'] == 833 and v['serdes_period_ps'] == 1000
paths = [Path(s) for s in a.code_files.read_text().splitlines() if s.strip()]
removed = [s for s in paths if s.name in ('ot_qfd_ucie_x64_phy_bb.v', 'ot_qfd_serdes_112g_x12_phy_s597_bb.v')]
assert len(removed) == 2, removed
paths = [s for s in paths if s not in removed]
roms = [s for s in paths if s.name == 'sim_ot_rom_4096x266_m8.v']
assert len(roms) == 1, roms
paths[paths.index(roms[0])] = a.table_overlay
generic = [s for s in paths if s.name == 'ot_qkvd_ucie_x64_phy_model.sv']
assert len(generic) <= 1, generic
reference = a.phy_dir / 'registered_fdi_model.sv'
if generic:
    assert generic[0].read_bytes() == reference.read_bytes(), 'generic FDI model differs'
else:
    paths.append(reference)
paths += [a.phy_dir / 'qc_phy_bringup.sv', a.vehicle / 'start_stages_fn.sv', a.vehicle / 'tb_qcdie.sv']
assert len(paths) == len(set(paths))
for s in paths:
    assert s.is_file(), s
a.out.mkdir(parents=True, exist_ok=True)
(a.out / 'source.f').write_text(''.join(str(s.resolve()) + '\n' for s in paths))
(a.out / 'source.json').write_text(json.dumps(dict(
    scope='SOURCE COMPOSITION ONLY; quiescent external PHY bringup, no mission/token qualification',
    required_plusargs=['+QC_PHY_BRINGUP_ONLY=1', '+OT_QC_CODE_ROM_DIR=<rank-code-dir>', '+OT_QC_TABLE_ROM_DIR=<rank-native-table-dir>'],
    core_period_ps=833, external_phy_period_ps=1000,
    removed_external_blackboxes=[str(s) for s in removed],
    generic_fdi_definitions=1, native_required=['collective peer', 'SerDes host/peer', 'KV mission peer', 'current programme'],
    sha256={str(s): hashlib.sha256(s.read_bytes()).hexdigest() for s in paths}), indent=2) + '\n')
print('QC_BRINGUP_SOURCE_READY', len(paths), 'files; mission TX fatal; full execution NOT_RUN')
