"""Execute the real generator-staged wrapper: elapsed repair time is never a stop."""
import pytest
import test_grt183_kit as G
import core_flow as CF

PROGRESS = r'''printf '%s\n' '[INFO GRT-0303] Global routing runtime 0.1' 'OT_MAXWIRE repair_design -verbose' > $L/5_1_grt.tmp.log
for n in 1 2 3; do
  echo "progressing repair $n" >> $L/5_1_grt.tmp.log
  sleep 1
done
echo 'OT_MAXWIRE leaf instances 10 -> 11' >> $L/5_1_grt.tmp.log
echo COMPLETE > $R/5_1_grt.odb
echo finished > $L/5_1_grt.log
exit 0
'''


@pytest.mark.parametrize('mode', ['default', 'env_zero', 'config_zero'])
def test_generator_staged_wrapper_zero_and_default_are_uncapped(tmp_path, monkeypatch, mode):
    monkeypatch.delenv('OT_GRT_POST_MAX_S', raising=False)
    cfg = 'export OT_GRT_POST_MAX_S = 1\n' if mode == 'env_zero' else (
        'export OT_GRT_POST_MAX_S = 0\n' if mode == 'config_zero' else '')
    k, r, l, s = G.kit(tmp_path, cfg)
    CF.stage_grt183(k)
    staged = k / 'grt183_make.sh'
    assert staged.read_bytes() == G.W.read_bytes()
    assert 'cfg_num OT_GRT_POST_MAX_S 0)' in staged.read_text()
    monkeypatch.setattr(G, 'W', staged)
    env = dict(OT_GRT_STALL_RESUME='0', OT_GRT_REPAIR_LOG_S='0', OT_GRT_STALL_POLL='1', OT_FAILFAST='0')
    if mode == 'env_zero':
        env['OT_GRT_POST_MAX_S'] = '0'  # zero wins over a stale positive config value
    p = G.run(k, s, G.fake(tmp_path, PROGRESS), 'grt', env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert len(G.calls(k)) == 1  # neither killed nor silently retried
    assert (r / '5_1_grt.odb').read_text().strip() == 'COMPLETE'
    assert (r / '4_cts.odb').read_text() == 'cts'
    assert 'progressing repair 3' in (l / '5_1_grt.tmp.log').read_text()
    assert 'OT_GRT_TIMECAP' not in p.stdout and 'OT_GRT_TIMELOG' not in p.stdout


def test_positive_diagnostic_threshold_logs_but_cannot_stop_progress(tmp_path, monkeypatch):
    monkeypatch.delenv('OT_GRT_POST_MAX_S', raising=False)
    k, r, l, s = G.kit(tmp_path, 'export OT_GRT_POST_MAX_S = 1\n')
    CF.stage_grt183(k)
    monkeypatch.setattr(G, 'W', k / 'grt183_make.sh')
    p = G.run(k, s, G.fake(tmp_path, PROGRESS), 'grt', env=dict(
        OT_GRT_STALL_RESUME='0', OT_GRT_REPAIR_LOG_S='0', OT_GRT_STALL_POLL='1', OT_FAILFAST='0'))
    assert p.returncode == 0 and len(G.calls(k)) == 1, p.stdout + p.stderr
    assert (r / '5_1_grt.odb').read_text().strip() == 'COMPLETE'
    assert 'OT_GRT_TIMELOG' in p.stdout and 'NO CAP' in p.stdout
    assert 'OT_GRT_TIMECAP' not in p.stdout
