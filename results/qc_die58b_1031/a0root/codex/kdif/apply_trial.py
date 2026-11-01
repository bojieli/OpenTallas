#!/usr/bin/env python3
"""Prepare exact NW18/G4 K-limit backup in a NEW PRIVATE trial kit; macro stays OFF by default."""
from pathlib import Path
import argparse,shutil,json
ap=argparse.ArgumentParser();ap.add_argument('kit');ap.add_argument('--enable',action='store_true');a=ap.parse_args()
k=Path(a.kit).resolve()
assert '/codex-qca0/' in str(k), 'private trial kit only'
assert not (k/'run').exists(), 'apply only before a new trial build; never mutate a progressing checkpoint'
p=k/'rtl/ot_qwen_w12_matvec_land32.sv';s=p.read_text()
old="""            wire [31:0] c32 = (gb + gk) & ((1 << sa) - 1);
            always @(posedge clk) begin
                kdif[gk] <= ({{(32-NW){1'b0}}, kt} > c32) ? (kt - c32[NW:0] + ((1 << sd) - 1)) : {(NW+1){1'b0}};
                klim[gk] <= kdif[gk] >> sb;
"""
new="""            wire [31:0] c32 = (gb + gk) & ((1 << sa) - 1);
`ifdef OT_KDIF_FAST_EXPERIMENT
            // Exact isolated SAT gate on every production G4 constant. Same register and same cycle.
            wire [18:0] kdif_fast;
            localparam integer KDW = NW+1;
            if (NW == 18 && G == 4) begin: g_kdif_fast
                ot_kdif_candidate #(.GK(gk)) u_kdf (.gb(gb),.kt(18'(kt)),.sa(sa),.sd(sd),.q(kdif_fast));
            end else begin: g_kdif_unused
                assign kdif_fast = 19'd0;
            end
`endif
            always @(posedge clk) begin
`ifdef OT_KDIF_FAST_EXPERIMENT
                if (NW == 18 && G == 4) kdif[gk] <= KDW'(kdif_fast);
                else
`endif
                kdif[gk] <= ({{(32-NW){1'b0}}, kt} > c32) ? (kt - c32[NW:0] + ((1 << sd) - 1)) : {(NW+1){1'b0}};
                klim[gk] <= kdif[gk] >> sb;
"""
assert s.count(old)==1, 'source vehicle changed; diagnose before applying'
p.write_text(s.replace(old,new))
here=Path(__file__).resolve().parent
shutil.copy2(here/'kdif_allgroups.sv',k/'rtl/ot_kdif_backup.sv')
p=k/'config.mk';s=p.read_text()
needle='export VERILOG_FILES = '
assert s.count(needle)==1
s=s.replace(needle,needle+'/work/rtl/ot_kdif_backup.sv ',1)
if a.enable:s=s.replace('export VERILOG_DEFINES = ','export VERILOG_DEFINES = -DOT_KDIF_FAST_EXPERIMENT ',1)
p.write_text(s)
# rtl_lint.ys parses the same helper/define; production default is off.
p=k/'rtl_lint.ys';s=p.read_text();n='read_verilog -defer -sv -noautowire -I/work/rtl '
assert n in s
s=s.replace(n,'read_verilog -defer -sv -noautowire -I/work/rtl /work/rtl/ot_kdif_backup.sv\n'+n,1)
if a.enable:s=s.replace('verilog_defines ','verilog_defines -DOT_KDIF_FAST_EXPERIMENT ',1)
p.write_text(s)
(k/'KDIF_EXPERIMENT.json').write_text(json.dumps({'enabled':a.enable,'macro':'OT_KDIF_FAST_EXPERIMENT','scope':'NW18/G4/REGROOT<8 only','reference':'original same integer expression','proof':'SAT all58inputs eachGK0..3 + missingcarry mutant','extra_cycles':0,'production_default':'off','physical_timing':'NOT RUN; complete current plan/geometry gates first'},indent=2)+'\n')
