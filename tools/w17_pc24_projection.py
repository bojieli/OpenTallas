"""Conditional retained-source PC24 schedule and wall projection, no live probe."""
def projection(cycle,seconds_per_1000=320):
    if type(cycle) is not int or cycle<0 or type(seconds_per_1000) not in (int,float) or not 0<seconds_per_1000<1e9:raise ValueError('projection input')
    def interval(a,b):return dict(cycles=[a,b],remaining_cycles=[max(0,a-cycle),max(0,b-cycle)],estimated_remaining_seconds=[max(0,a-cycle)*seconds_per_1000/1000,max(0,b-cycle)*seconds_per_1000/1000])
    return dict(current_cycle=cycle,rate_seconds_per_1000=seconds_per_1000,conditional_PC_only_watchdog=interval(112202,112401),conditional_cold_refill=interval(136671,138146),refill_elapsed_cycles=[123964,125727],reads_per_rank=2176,rows_per_rank=128,guaranteed_completion_cycle=None,guaranteed_wall_bound=None,causal_service='BOUND_MISSING',live_health_or_deadlock='UNDETERMINED')

def core_debug(state):
    if type(state) is not int or not 0<=state<1<<64:raise ValueError('state envelope')
    return dict(core_st=(state>>24)&15,decoded_unit=(state>>21)&7,idles=(state>>16)&31,waited=(state>>14)&1)
