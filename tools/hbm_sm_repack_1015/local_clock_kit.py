import json,pathlib,re
r=pathlib.Path(__file__).resolve().parents[2]
s=json.loads((r/'physical/ref_tile/smh_tile_rp3/spec.json').read_text());plan=json.loads((r/'results/arch/hbm_sm_repack_1015/rp4_clock_candidate/plan.json').read_text())
s.update(name='smh_tile_rp4',top='ot_hbm_smh_rp4_entries',clock='hybrid_entries',clock_port='clk_hard[0]',clock_ports=[f'clk_hard[{i}]' for i in range(18)]+[f'clk_pin[{i}]' for i in range(3)]+[f'clk_oper[{i}]' for i in range(4)]+[f'clk_region[{i}]' for i in range(3)],clock_cts_roots=[f'clk_pin[{i}]' for i in range(3)]+[f'clk_oper[{i}]' for i in range(4)]+[f'clk_region[{i}]' for i in range(3)],outline={'w':406.08,'h':1321.92},child_lattice_um=4.32)
s.pop('spine_through_icg',None)
s['sources']+=['rtl/hbm_accel/sm/repack/ot_hbm_smh_rp4_clocks.sv']
s['children']=[{'view':c['view'],'count':1,'at':c['at_um'],'orient':c['orient'],'inst':c['inst'].replace('[','?').replace(']','?')} for c in plan['children']]
s['pins']['N']=[p for p in s['pins']['N'] if p not in ['clk','cgi','cgo']]
s['pins']['W']+=['clk_hard','clk_pin','clk_oper','clk_region']
s['io_tcl']='physical/ref_tile_specs/smh/smh_tile_rp4_pins.tcl'
s['orfs_vars']={'OT_IO_REF_CLASS':'1'}
s['pin_regs']['reason']='Actual RTL pin capture and launch registers retained from rp3, explicit18hard-child clocks and10local roots; no data edge change. rin/bin land in own pin flops, rout/bout launch from existing hard row/beat cells, gin/gout from existing input/output registers, xs_* through retained five-stage strap registers, rst_n through regional reset relay. External gating companion is separately instantiated actual RTL, never replaced by free-running production clocks.'
s['job'].update(branch='claude/hsm-rp4-0030',tag='rp4',owner='Codex H-SM recovery',structural_change='rp3 measured14,491 sinks with1,292-1,322ps insertion: remove6556 row-group soft sinks into four existing CLOSED hard row children and replace monolithic clock tree by18direct child-clock entries plus10localized own-soft roots. Hard geometry expands129.6um height; retains all data edges and actual28-root gated companion external to this master. No timing gate relaxation.',purpose='MATVEC body clock-structure closure only; not attention/fullSM/native chip qualification.')
s['job']['benches']=[dict(name='rp4_lockstep',expect='pass',pass_regex='PASS total_cycles [1-9]',threads=8,peak_ram_gb=72,cmd='python3 tools/hbm_sm_repack_1015/local_clock_lockstep.py --out {RUN}/positive.json --workdir {RUN}/positive --jobs 8'),dict(name='rp4_clockdrop',expect='fail',fail_regex='FAIL total_cycles',threads=8,peak_ram_gb=72,cmd='python3 tools/hbm_sm_repack_1015/local_clock_lockstep.py --mut-clockdrop --out {RUN}/mutant.json --workdir {RUN}/mutant --jobs 8')]
s['job']['extra_paths']+=['tools/hbm_sm_repack_1015','tools/dshbm_sm_pq_seq.py','rtl/test/tb_hbm_accel_sm_pq_seq.sv']
p=r/'physical/ref_tile_specs/smh/smh_tile_rp4.json';p.write_text(json.dumps(s,indent=1)+'\n')
# Retain all existing data-face locations; shift only north-face y with the outline.
lines=[]
for line in (r/'physical/ref_tile_specs/smh/smh_tile_rp3_pins.tcl').read_text().splitlines():
 if any('{'+x+'}' in line for x in ['clk','cgi','cgo']):continue
 lines.append(line.replace('1192.32}', '1321.92}'))
# Local clock entries at legal west-face stations nearest their clock regions.
# Clock stations avoid dense data-face interval y499..701; west face uses horizontal M4.
ys=[1100,1170,1200,1250,1270,200,260,320,370,420,470,472,474,476,478,786,722,480,450,452,454,1030,1070,230,270,1150,760,160]
for port,y in zip(s['clock_ports'],ys):lines.append(f'place_pin -pin_name {{{port}}} -layer M4 -location {{0 {y+0.012:.3f}}} -pin_size {{0.192 0.024}} -force_to_die_boundary')
(r/s['io_tcl']).write_text('\n'.join(lines)+'\n')
print(p)
