"""No argparse/tool failure can become a harmless missing-clock warning."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pre_route_gate as P

def check(text):
 g=P.Gate();ok=P.check_textbook_execution(g,text);return ok,g

def test_current_pass_and_real_refusal():
 for rc,v in [('0','PASS'),('3','REFUSE')]:assert check(f'GATE_TB_RC={rc}\nGATE_TB textbook_lint: {v} tile cells 1 flops 1\n')[0]

def test_tool_failures_and_missing_verdict_refuse():
 for s in ['usage: textbook_lint.py\nerror: unrecognized arguments: --balanced-reset-profile\n','GATE_TB_RC=2\n','GATE_TB_RC=2\nGATE_TB textbook_lint: PASS tile cells 1\n','GATE_TB_RC=0\n','GATE_TB_RC=0\nGATE_TB_RC=2\nGATE_TB textbook_lint: PASS tile cells 1\n']:
  ok,g=check(s);assert not ok and any(i['check']=='textbook_execution' for i in g.items)

def test_historical_log_still_requires_actual_unique_verdict():
 assert check('GATE_TB textbook_lint: PASS tile cells 1\n')[0]
 assert not check('GATE_TB textbook_lint: PASS tile cells 1\nGATE_TB textbook_lint: PASS tile cells 1\n')[0]

def test_script_preserves_process_exit_and_reset_args():
 assert 'GATE_TB_RC=${{PIPESTATUS[0]}}' in P.REMOTE_SH
 assert '--refuse-checks {RC}{TBX}{BRP} |' in P.REMOTE_SH


def test_process_exit_must_agree_with_actual_verdict():
 for rc,v in [('3','PASS'),('3','WARN'),('0','REFUSE')]:
  ok,g=check(f'GATE_TB_RC={rc}\nGATE_TB textbook_lint: {v} tile cells 1 flops 1\n')
  assert not ok and any(i['check']=='textbook_execution' for i in g.items)
