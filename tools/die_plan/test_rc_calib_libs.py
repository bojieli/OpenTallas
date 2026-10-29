import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc_calib as R


def test_exact_selected_library_loader_survives_probe_extraction():
    setup = '''proc exact_load {config receipt} {
  foreach lib [selected $config] {read_liberty $lib}
}
exact_load /work/config.mk /out/libraries.json
'''
    text = R.library_prefix(setup + 'read_db /base/6_final.odb\nread_sdc /sdc/golden.sdc\n', '/w/ff.json')
    assert text == setup.replace('/out/libraries.json', '/w/ff.json')
    # The previous grep extractor omitted the loader call and loaded no libs.
    assert not any(line.startswith(('foreach l', 'read_liberty')) for line in setup.splitlines())


def test_legacy_loader_keeps_exact_lines():
    setup = 'foreach l {/lib/A.lib /lib/B.lib} {read_liberty $l}\n'
    assert R.library_prefix(setup + 'read_db /base/6_final.odb\n', '/w/ff.json') == setup


def test_missing_db_boundary_is_an_error():
    with pytest.raises(ValueError, match='read_db boundary'):
        R.library_prefix('proc loader {} {}\n', '/w/ff.json')
