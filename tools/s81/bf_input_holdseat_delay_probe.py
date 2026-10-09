#!/usr/bin/env python3
"""Generate minimal real-lib hold-seat delay probes, with no placement claim."""
import argparse
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    p.add_argument('--seats', type=int, default=4)
    a = p.parse_args()
    if a.seats < 1:
        raise ValueError('positive seat count required')
    a.output.mkdir(parents=True, exist_ok=True)
    v = ['module bf_chain(input a, input clk, output y);',
         f'wire [{a.seats}:0] d;', 'assign d[0]=a;']
    for s in range(a.seats):
        v.append(f'HB2xp67_ASAP7_75t_R u_hb{s} (.A(d[{s}]), .Y(d[{s+1}]));')
    v += [f'DFFHQNx1_ASAP7_75t_R u_q (.D(d[{a.seats}]), .CLK(clk), .QN(y));', 'endmodule']
    (a.output/'chain.v').write_text('\n'.join(v)+'\n')
    for corner in ('TT', 'FF'):
        plat = '/OpenROAD-flow-scripts/flow/platforms/asap7'
        t = [f'read_lef {plat}/lef/asap7_tech_1x_201209.lef',
             f'read_lef {plat}/lef/asap7sc7p5t_28_R_1x_220121a.lef',
             f'read_liberty {plat}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz',
             f'read_liberty {plat}/lib/NLDM/asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib',
             'read_verilog /probe/chain.v', 'link_design bf_chain',
             'create_clock -name core_clk -period 833.333 [get_ports clk]',
             'set_clock_uncertainty -setup 60 [get_clocks core_clk]',
             'set_clock_uncertainty -hold 25 [get_clocks core_clk]',
             'set_input_delay -max 250 -clock core_clk [get_ports a]',
             'set_input_delay -min 0 -clock core_clk [get_ports a]',
             f'puts "BF_HOLDSEAT_PROBE corner={corner} seats={a.seats} ideal_clock=1 no_wire_delay_credit=1"',
             'puts "BF_CHAIN_SETUP [sta::worst_slack_cmd max]"',
             'puts "BF_CHAIN_HOLD [sta::worst_slack_cmd min]"',
             'report_checks -from [get_ports a] -to [get_pins u_q/D] -path_delay min -format full_clock_expanded -digits 3',
             'report_checks -from [get_ports a] -to [get_pins u_q/D] -path_delay max -format full_clock_expanded -digits 3',
             'exit']
        (a.output/f'chain_{corner.lower()}.tcl').write_text('\n'.join(t)+'\n')


if __name__ == '__main__':
    main()
