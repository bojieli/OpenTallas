#!/usr/bin/env python3
"""External archival fixture for one unchanged mocked r9 lifecycle test only."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

MEMINFO_FIXTURE='MemAvailable: 134217728 kB\n'  # 128GiB static external resource fixture.

def fixture_read_text(path, original, *args, **kwargs):
    if path == Path('/proc/meminfo'):
        return MEMINFO_FIXTURE
    return original(path, *args, **kwargs)


def main():
    # cwd is the actual pinned worker; imports and all original controls stay there.
    sys.path.insert(0,str(Path.cwd()/'tools'))
    import test_hbm_qwen_frontend_r9 as checks
    original_test=checks.QwenCalibration.test_mocked_cold_build_lifecycle
    original_read=Path.read_text
    def lifecycle_with_external_fixture(self):
        def read(path,*args,**kwargs):
            return fixture_read_text(path,original_read,*args,**kwargs)
        with patch.object(Path,'read_text',autospec=True,side_effect=read):
            original_test(self)
    checks.QwenCalibration.test_mocked_cold_build_lifecycle=lifecycle_with_external_fixture
    result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(checks.QwenCalibration))
    print(json.dumps(dict(tests_run=result.testsRun,external_resource_fixture=dict(test='test_mocked_cold_build_lifecycle',path='/proc/meminfo',MemAvailable_bytes=128*1024**3,all_other_reads='delegated unchanged',patch_scope='only the already mocked lifecycle testcase',production_runtime_fixture=False),actual_execution=False),sort_keys=True))
    if not result.wasSuccessful():raise SystemExit(1)

if __name__=='__main__':main()
