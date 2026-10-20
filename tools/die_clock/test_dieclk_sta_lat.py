"""GEN16 item 6: source latency = measured arrival - R for measured pins; ideal pins kept; too few measured fails."""
import os, subprocess, sys, tempfile
H = os.path.dirname(os.path.abspath(__file__))


def run(clk, arr, col, frac='0.5'):
    d = tempfile.mkdtemp()
    open(f'{d}/c.tcl', 'w').write(clk); open(f'{d}/a.tsv', 'w').write(arr)
    r = subprocess.run([sys.executable, f'{H}/dieclk_sta_lat.py', '--clocks', f'{d}/c.tcl', '--arrivals', f'{d}/a.tsv',
                        '--col', col, '--out', f'{d}/o.tcl', '--min-frac', frac], capture_output=True, text=True)
    return r.returncode, open(f'{d}/o.tcl').read() if os.path.exists(f'{d}/o.tcl') else ''


CLK = ('set_clock_latency -source -clock [get_clocks stream] -420.7 [get_pins {d2d_rom/ck}]\n'
       'set_clock_latency -source -clock [get_clocks stream] -0.000000 [get_pins {c16_0/ck_c0r0[0]}]\n'
       'set_clock_latency -source -clock [get_clocks stream] -0.000000 [get_pins {rly_x_1/ckf[0]}]\n')
ARR = 'd2d_rom/ck\t3000.0\t2500.0\t40\nc16_0/ck_c0r0\t2900.0\t2400.0\t40\n'


def test_late_early_and_ideal():
    rc, o = run(CLK, ARR, 'late')
    assert rc == 0 and '2579.3 [get_pins {d2d_rom/ck}]' in o and '2900.0 [get_pins {c16_0/ck_c0r0[0]}]' in o
    assert 'rly_x_1' not in o.split('\n', 2)[2] and 'measured=2 ideal=1 of 3' in o
    rc, o = run(CLK, ARR, 'early')
    assert rc == 0 and '2079.3 [get_pins {d2d_rom/ck}]' in o


def test_fails_closed_when_mostly_unmeasured():
    rc, _ = run(CLK, 'nothing/ck\t1\t1\t1\n', 'late')
    assert rc == 1


if __name__ == '__main__':
    test_late_early_and_ideal(); test_fails_closed_when_mostly_unmeasured(); print('DIECLK_STA_LAT TESTS PASS')
