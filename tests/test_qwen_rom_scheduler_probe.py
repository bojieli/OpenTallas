"""CPU observations must not treat disabled wait counters as a contention proof."""
import copy
import sys
from pathlib import Path

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_scheduler_probe as P


def samples(enabled=True):
 b=dict(start_ticks=42,schedstats_enabled=enabled,hz=100,
  threads={'100':dict(start_ticks=43,run_ns=10**9,wait_ns=0,slices=1,nice=0,processor=0,allowed='0-27')},
  cpus={'cpu':dict(total=100,idle=50,iowait=0,steal=0)},
  processes={'100':dict(start_ticks=42,ticks=100,name='qwen_rom_rt',nice=0)})
 a=copy.deepcopy(b);a['threads']['100']['run_ns']+=8*10**9;a['threads']['100']['wait_ns']+=2*10**9
 a['cpus']['cpu'].update(total=200,idle=100);a['processes']['100']['ticks']+=800
 return b,a


def test_valid_wait_measurement_and_cpu_rate():
 b,a=samples();r=P.summarize(b,a,10)
 assert r['dominant_thread']['cpu_percent']==80 and r['dominant_thread']['wait_fraction']==.2
 assert r['material_runqueue_wait_observed'] is True and r['runqueue_wait_counters_valid']
 assert r['host_cpu']['cpu']['idle_fraction']==.5 and not r['actions_taken']


def test_disabled_scheduler_accounting_never_proves_absent_or_present_wait():
 b,a=samples(False);r=P.summarize(b,a,10)
 assert r['material_runqueue_wait_observed'] is None and not r['runqueue_wait_counters_valid']
 assert r['total_process_cpu_percent']==80


def test_unknown_accounting_validity_is_inconclusive():
 b,a=samples();del b['schedstats_enabled']
 assert P.summarize(b,a,10)['material_runqueue_wait_observed'] is None


def test_recycled_original_pid_is_rejected():
 b,a=samples();a['start_ticks']=99
 with pytest.raises(ValueError,match='PID recycled'):P.summarize(b,a,10)


def test_recycled_thread_is_not_measured_as_original():
 b,a=samples();a['threads']['100']['start_ticks']=99
 r=P.summarize(b,a,10)
 assert not r['thread_samples'] and r['dominant_thread'] is None


def test_counter_regression_is_rejected():
 b,a=samples();a['threads']['100']['run_ns']=0
 with pytest.raises(ValueError,match='regressed'):P.summarize(b,a,10)
