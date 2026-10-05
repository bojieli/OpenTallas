import importlib.util,json
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('decchar',P/'tools/dsrom_secded_fullwidth_characterize.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_full_widths_and_shared_model():
    v=m.model()
    assert (v['raw']['K'],v['raw']['N'],v['raw']['replicas_per_die'])==(256,266,412)
    assert (v['main']['K'],v['main']['N'])==(272,282)
    assert v['main']['selected_replica_count']==256
    assert v['state_bits_existing_decoder']==0 and not v['physical_build_admitted']
def test_both_corner_complete_cells_and_capture_load():
    ss,sc=m.merged('ss');ff,fc=m.merged('ff')
    assert set(sc)==set(fc)
    assert len(sc)>100
    assert 0<m.dcap(sc)<2 and 0<m.dcap(fc)<2
    assert m.input_pins(sc['XOR2xp5_ASAP7_75t_R'])=={'A','B'}
    assert 'FAKE' not in ss and 'FAKE' not in ff
def test_receipt_all_inputs_unchanged():
    r=json.loads((m.OUT/'inputs/receipt.json').read_text())
    for name,h in r['hashes'].items():assert m.sha(m.OUT/'inputs'/name)==h
    assert m.sha(m.OUT/'inputs/decoder.sv')==m.sha(P/'rtl/dft/ot_rom_secded_dec.sv')
def test_no_retry_on_existing_workdir(tmp_path):
    with pytest.raises(ValueError,match='first run'):m.run(tmp_path)
