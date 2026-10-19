from pathlib import Path
import csv
ports=list(csv.DictReader(Path('canonical/ports.csv').open()))
# ASAP7 libraries are ps/fF; original833ps/60ps/25ps unchanged.
Path('out/coupon.sdc').write_text("""create_clock -name coupon_clk -period 833 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks coupon_clk]
set_clock_uncertainty -hold 25 [get_clocks coupon_clk]
set_input_delay -max 30 -clock coupon_clk [get_ports {lane_v* payload*}]
set_input_delay -min 30 -clock coupon_clk [get_ports {lane_v* payload*}]
set_output_delay -max 0 -clock coupon_clk [get_ports {compacted* pair_select* quad_select*}]
set_output_delay -min -30 -clock coupon_clk [get_ports {compacted* pair_select* quad_select*}]
set_load 80 [get_ports {compacted* pair_select* quad_select*}]
# Explicit native source-cell timing model; actual parent driver/wire qualification OPEN.
set_driving_cell -lib_cell BUFx8_ASAP7_75t_R -pin Y [get_ports {lane_v* payload*}]
# Ideal-wire source coupon only. Actual wire RC/CQ/clock insertion/neighbor OPEN.
""")
# Reviewable IO allocation only: commands are data, never executed here.
lines=['# MODEL ONLY. ROOT review before any engine. Full faces; exact .192 pitch.', '# All504 legal rows retained. No FENCE/REGION; single central allocation band.', '# Native PG birth-binding policy a92 REQUIRED, not activated by this kit.', 'set coupon_allocation_band {2.16 56.16 138.24 84.24}']
for r in ports:lines.append('dict set coupon_pin_model {'+r['port']+'} [list '+r['face']+' '+r['x_um']+' '+r['y_um']+']')
Path('out/io_band_pg_model.tcl').write_text('\n'.join(lines)+'\n')
