import sys
from pathlib import Path
sys.path.insert(0,str(Path('src/tools/hbm_static').resolve()))
import su_programme_compile as C
m=C.lower_columns(Path('expected.mem'),Path('compiler_fixed'),resident_edges=7111)
a=Path('compiler_fixed/config.mem').read_text();b=Path('config_fixed.mem').read_text()
assert a==b,'compiler must exactly reproduce native-positive configuration'
assert all(x['index_banks']==4 for x in m['columns'])
assert m['cluster_macros']==sum(4+x['leaf_dictionary_banks'] for x in m['columns'])
C.lower_columns(Path('expected.mem'),Path('compiler_legacy'))
assert Path('compiler_legacy/config.mem').read_text()==Path('config_old.mem').read_text(),'default ABI changed'
try:C.lower_columns(Path('expected.mem'),Path('too_short'),resident_edges=43)
except AssertionError:pass
else:raise AssertionError('capacity guard missing')
print('COMPILER PASS native_configuration_identical legacy_default_unchanged capacity_guard')
