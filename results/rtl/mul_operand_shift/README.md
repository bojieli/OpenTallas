# Multiplier operand shift without idle hold

Based on production ot_wide_mul_seq, the candidate removes reset and idle hold
from b_work only. It loads b at acceptance (!running && start), otherwise shifts
every clock. Loading takes priority over shifting. The accepted value is consumed
on the following clock exactly as before. Reset still clears protocol state and
public outputs; acceptance overwrites all b_work bits before arithmetic consumes
any of them. Other operand and accumulator contracts are unchanged.

The positive range-pipeline attribution identifies multiplier running-to-b_work
as the worst mapped control path. This candidate reduces that control load;
it does not promise lower dynamic power because private idle switching changes.

run_latency.py compares the full positive range-pipeline corpus with production
and candidate multipliers. Both produce exact results at the same cycle count.
The standalone 1 ns physical route remains pending, and production is unchanged.
