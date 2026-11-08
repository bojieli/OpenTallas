"""Only the declared native-reset selector reaches topology preparation."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K


def test_absent_selector_keeps_command_unchanged():
    assert K.topology_env_prefix({}) == ''
    assert K.topology_env_prefix(dict(gen_env=dict(OT_FLOW_TAG='tag',OTHER='$(bad)'))) == ''


def test_only_exact_allowlisted_selector_is_forwarded():
    assert K.topology_env_prefix(dict(gen_env=dict(OT_NATIVE_RESET_SCOPE='selected',OTHER='$(bad)'))) == 'OT_NATIVE_RESET_SCOPE=selected '


@pytest.mark.parametrize('value', ['', 'all', 'selected; touch /tmp/bad', True, 1])
def test_invalid_selector_rejected(value):
    with pytest.raises(ValueError):
        K.topology_env_prefix(dict(gen_env=dict(OT_NATIVE_RESET_SCOPE=value)))


def test_capture_path_requires_selector_and_is_shell_literal():
    import shlex
    with pytest.raises(ValueError):
        K.topology_env_prefix(dict(gen_env=dict(OT_NATIVE_PRODUCER_CONTEXT='/tmp/capture.json')))
    with pytest.raises(ValueError):
        K.topology_env_prefix(dict(gen_env=dict(OT_NATIVE_RESET_SCOPE='selected',OT_NATIVE_PRODUCER_CONTEXT='relative.json')))
    path='/tmp/captured plan/$(touch BAD)'
    prefix=K.topology_env_prefix(dict(gen_env=dict(OT_NATIVE_RESET_SCOPE='selected',OT_NATIVE_PRODUCER_CONTEXT=path)))
    assert shlex.split(prefix)==['OT_NATIVE_RESET_SCOPE=selected','OT_NATIVE_PRODUCER_CONTEXT='+path]


def test_item_env_narrow_capture_path_support():
    env=dict(OT_NATIVE_RESET_SCOPE='selected',OT_NATIVE_PRODUCER_CONTEXT='/srv/own/capture.json')
    assert K.item_env(dict(item_env={'T':env}),'T')==env
    for bad in (
        dict(OT_NATIVE_PRODUCER_CONTEXT='/srv/own/capture.json'),
        dict(OTHER='/srv/own/capture.json'),
        dict(OT_OTHER='/srv/own/capture.json'),
        dict(OT_NATIVE_RESET_SCOPE='selected',OT_NATIVE_PRODUCER_CONTEXT='/tmp/$(touch_BAD)'),
    ):
        with pytest.raises(ValueError): K.item_env(dict(item_env={'T':bad}),'T')
