from pathlib import Path
p=Path('pgkit02/psm');s=(p/'pdn.tcl').read_text();lines=s.splitlines();assert lines[-2].startswith('define_pdn_grid -name {parts}') and lines[-1].startswith('add_pdn_connect -grid {parts}')
(p/'pdn_top_only.tcl').write_text('\n'.join(lines[:-2])+'\n')
t=(p/'pg_only.tcl').read_text().replace('source /work/psm/pdn.tcl','source /work/psm/pdn_top_only.tcl').replace('/work/psm/pdn_grid.odb','/work/psm/pdn_top_only.odb')
(p/'pg_top_only.tcl').write_text(t)
print('TOP_GRID_ONLY: disconnected macro connectors explicitly excluded; upper PG geometry diagnostic only')
