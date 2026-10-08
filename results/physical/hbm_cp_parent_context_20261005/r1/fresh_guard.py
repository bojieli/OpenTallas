import os,time,sys,json
from pathlib import Path
def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
a=cpu();time.sleep(1);b=cpu();d=[y-x for x,y in zip(a,b)];idle=(d[3]+d[4])/sum(d)*os.cpu_count();load=os.getloadavg()[0]
print(json.dumps(dict(load1=load,measured_idle_cores=idle,required_cores=16)),flush=True)
if load>=128 or idle<16:sys.exit(75)
