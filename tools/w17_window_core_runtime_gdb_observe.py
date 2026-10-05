"""Loaded only by the authorized GDB child. Observe; never change DUT state."""
import gdb,json,time,os
trace=os.environ['OT_CORE_DIAG_TRACE'];began=time.monotonic()
def emit(stage,**data):
 with open(trace,'a') as f:
  f.write(json.dumps({'stage':stage,'elapsed_seconds':time.monotonic()-began,**data})+'\n');f.flush()
class Marker(gdb.Breakpoint):
 def __init__(self,symbol,stage,limit=1):
  super().__init__(symbol,internal=True);self.stage=stage;self.limit=limit;self.count=0
 def stop(self):
  self.count+=1;emit(self.stage,hit=self.count)
  if self.count>=self.limit:self.enabled=False
  return False
class NextReturn(gdb.FinishBreakpoint):
 def __init__(self):super().__init__(gdb.newest_frame(),internal=True)
 def stop(self):
  emit('NEXT_SIMULATION_SLOT_RETURN',raw_rax_uint64=int(gdb.parse_and_eval('$rax')) & ((1<<64)-1));return False
class NextSlot(gdb.Breakpoint):
 def __init__(self):super().__init__('Vtb::nextTimeSlot()',internal=True);self.count=0
 def stop(self):
  self.count+=1;NextReturn()
  if self.count>=64:self.enabled=False
  return False
# Disable all GDB startup scripts, randomization changes and confirmations via driver.
Marker('main','MAIN_ENTER')
Marker('Vtb::Vtb(VerilatedContext*, char const*)','CONSTRUCTOR_ENTER')
Marker('Vtb::eval_step()','EVAL_STEP_ENTER',limit=16)
Marker('Vtb___024root___eval_static(Vtb___024root*)','INITIAL_STATIC_ENTER')
Marker('Vtb___024root___eval_initial(Vtb___024root*)','INITIAL_PROCESSES_ENTER')
Marker('Vtb___024root___eval_settle(Vtb___024root*)','INITIAL_SETTLE_ENTER')
Marker('Vtb___024root___eval(Vtb___024root*)','DUT_EVAL_ENTER',limit=16)
NextSlot()
emit('OBSERVERS_READY')
gdb.execute('run')
emit('GDB_RUN_RETURNED')
