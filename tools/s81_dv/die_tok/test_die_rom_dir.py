"""TOK-DS-2: die_rom_dir.py links frame-local writer images to bound original-path selectors."""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_links_and_coverage(tmp_path):
    rtl = tmp_path / 'rtl'; rtl.mkdir()
    (rtl / 's81_bound_top.sv').write_text('col #(.P_a_INSTANCE("u_f_7L10.u_r1.u_c5_0"), .P_b_INSTANCE("u_f_7L10.u_r1.u_e5")) c0 ();\n')
    (rtl / 'col_x.sv').write_text('ot_rom_4096x72_m8 #(.INSTANCE("u_f_0L01.u_r2.u_c11_0")) r ();\n')
    img = tmp_path / 'img'; img.mkdir()
    for n in ('u_f_7L10_c5_0', 'u_f_7L10_e5_0', 'u_f_7L10_e5b_1', 'u_f_7L10_e1e_0'):
        (img / f'{n}.viamap.hex').write_text('0\n')
    out = tmp_path / 'rom'
    subprocess.run([sys.executable, str(HERE / 'die_rom_dir.py'), '--rtl', str(rtl), '--out', str(out), str(img)], check=True)
    assert (out / 'u_f_7L10.u_r1.u_c5_0.viamap.hex').resolve() == (img / 'u_f_7L10_c5_0.viamap.hex').resolve()
    assert (out / 'u_f_7L10.u_r1.u_e5_0.viamap.hex').exists() and (out / 'u_f_7L10.u_r1.u_e5b_1.viamap.hex').exists()
    rep = json.loads((out / 'die_rom_dir.json').read_text())
    assert rep['selectors'] == 3 and rep['with_image'] == 2 and rep['n_unmapped'] == 1      # e1e: no bound selector
    assert rep['frames']['u_f_7L10'] == [2, 2] and rep['frames_none'] == ['u_f_0L01']
