from pathlib import Path
import re
p=Path(__file__).resolve().parent
case=p/'case_mu6b_m8'
s=(case/'run.tcl').read_text()
head=s[:s.index('read_verilog')]
contract=next(x for x in s.splitlines() if x.startswith('set ::ot_die_rep_fclk_data_ports '))
probe=head+"""read_db /work/die_repeaters.fclk.fail.odb
source /work/die_repeaters.tcl
source /work/fclk_audit.tcl
source /work/probe_original_names.tcl
"""+contract+"""
set bad [ot_die_rep_fclk_audit /work/probe/before {n*_fck*} {BUFx8_ASAP7_75t_R}]
if {$bad != 1} {error "expected original one failing hop, got $bad"}
set unfix [ot_die_rep_fclk_equalize_data /work/probe/data_pre {n*_fck*} {BUFx8_ASAP7_75t_R}]
if {$unfix != 0} {error "unfixable $unfix"}
set bad [ot_die_rep_fclk_audit /work/probe/after {n*_fck*} {BUFx8_ASAP7_75t_R}]
if {$bad != 0} {error "still failing $bad"}
write_db /work/probe/balanced.odb
puts OT_PROBE_PASS
"""
(case/'probe.tcl').write_text(probe)

names=re.findall(r'^\s*\S+\s+(\S+)\s+\(', (case/'die.v').read_text(), re.M)
assert len(names)>9000
(case/'probe_original_names.tcl').write_text('array unset ::ot_die_rep_fclk_old\n'+''.join('set ::ot_die_rep_fclk_old('+n+') 1\n' for n in names))
print('reconstructed original instances',len(names))
