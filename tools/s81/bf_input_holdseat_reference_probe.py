#!/usr/bin/env python3
"""Prepare fresh preserved-BF TT/FF STA at measured boundary references."""
import argparse
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path)
    a = p.parse_args()
    for corner in ('tt', 'ff'):
        t = (a.bundle/f'{corner}_sign.tcl').read_text()
        # Preserve every original load/clock/budget and reported failing path.
        # The historical distribution appendix calls unsupported all_fanout;
        # use actual STA endpoint paths instead, and retain the original file.
        marker = '# I2R distribution:'
        if marker not in t:
            raise ValueError('unexpected preserved reference diagnostic')
        t = t.split(marker, 1)[0]
        expected = f'RVT_{corner.upper()}_nldm'
        if expected not in t or '/signoff_ref.sdc' not in t:
            raise ValueError('actual library corner or reference contract missing')
        t += f'puts "BF_REFERENCE_PROBE actual_corner={corner} measured_boundary=1"\n'
        for delay in ('max', 'min'):
            t += ('report_checks -path_delay '+delay+
                  ' -from [all_inputs] -to [all_registers -data_pins]'
                  ' -group_path_count 1 -format full_clock_expanded -digits 3\n')
            t += ('report_checks -path_delay '+delay+
                  ' -from [all_registers -clock_pins] -to [all_registers -data_pins]'
                  ' -group_path_count 1 -format full_clock_expanded -digits 3\n')
        if corner == 'tt':
            # Preserve the actual original route target (730 ps); only the
            # boundary reference changes from borrowed SS to measured TT.
            t += ('create_clock -name core_clk -period 730 [get_ports clk]\n'
                  'set_propagated_clock [all_clocks]\n'
                  'puts "BF_TT_ROUTE_REFERENCE period_ps=730 uncertainty_ps=60/25 measured_TT_IO=1"\n'
                  'report_checks -path_delay max -from [all_inputs]'
                  ' -to [all_registers -data_pins] -group_path_count 1'
                  ' -format full_clock_expanded -digits 3\n')
        t += 'exit\n'
        (a.bundle/f'{corner}_reference_probe.tcl').write_text(t)


if __name__ == '__main__':
    main()
