#!/usr/bin/env python3
"""Elaborate actual canonical PQ producer hierarchy without a numerical testbench."""
import argparse,hashlib,json,os,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[2]
sources=[x for x in (root/'physical/s81_pq_hier/pinned').rglob('*.sv') if x.name!='ot_sram_1r1w_128x256_m1_r2c2.sv']
sources+=list((root/'rtl/dsrom_sys/s81_ph/pq').glob('*.sv'))
sources+=[root/x for x in ['rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv','rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_produced.sv','rtl/dsrom_sys/s81_static_control/ot_s81_pq_command_endpoint.sv','rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv','rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_rom.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v']]
defines=['OT_PQ_ROM_PORTS','OT_PQ_CTL_STATIC','OT_PQ_QB_PIPE','OT_PQ_QB_PHYS_SPLIT','OT_PQ_AQ_PHYS_SPLIT','OT_PQ_IX_PHYS_SPLIT','OT_PQ_IX_BANK_SPLIT','OT_PQ_BC_SLICED','DSFD_PQ_STATIC_X2','OT_PQ_CTL_STATE_PINS']
xml=(a.out/'hierarchy.xml').resolve();tool=os.environ.get('OT_XML_VERILATOR','/usr/bin/verilator')
cmd=[tool,'--xml-only','--timing','--top-module','dsfd_sp_pq_produced','--xml-output',str(xml),'--Mdir',str((a.out/'obj').resolve()),'-Wno-fatal','-Wno-lint','-Wno-style',*[f'+define+{d}'for d in defines],*[str(x)for x in sources]]
with(a.out/'elaborate.log').open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
tree=ET.parse(xml);mods={x.get('name'):x.attrib for x in tree.findall('.//module')};cells=[]
for c in tree.findall('.//cells//cell'):
 m=mods.get(c.get('submodname'),{});cells.append(dict(c.attrib,original_master=m.get('origName',c.get('submodname')),module_attributes=m))
record=dict(scope='Actual elaborated producer source hierarchy. This does not provide physical views, die placement or canonical numerical workload coverage.',top='dsfd_sp_pq_produced',defines=defines,actual_cells=cells,source_sha256={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources},external_programme_rom_requirement=dict(master='ot_rom_4096x72_m8',phase=2,stream=4,stream_bank_select='actual two-bit registered index and48bit response mux remain parent placement obligations'),release_qualified=False)
(a.out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print('PQ_HIERARCHY PASS actual_cells='+str(len(cells)))
