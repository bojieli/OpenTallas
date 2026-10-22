import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('functional',Path(__file__).parent/'release72/g9f_functional.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_selected_zero_relay_ring_cannot_alias_storage_window():
    with pytest.raises(ValueError,match='cannot retain'):m.validate_local_ring_window(0,17,17,8)
    m.validate_local_ring_window(0,17,17,32)
    with pytest.raises(ValueError):m.validate_local_ring_window(0,2,17,32)
    with pytest.raises(ValueError):m.validate_local_ring_window(16,9,9,32)
