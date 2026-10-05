import pathlib as P,json,datetime,math
out=P.Path('/tmp/opentallas-disk-recovery-20261001/results/maintenance/remote_disk_recovery_20261001');pool=json.load(open('/tmp/claude-1000/agd_pool.json'));locks=json.load(open(out/'local_gate_slot_locks.json'));rows=[]
for host,vm in pool.items():
 p=out/(host+'_probe_raw.json')
 try:r=json.load(open(p))
 except (OSError,ValueError):rows.append({'host':host,'probe_failed':True});continue
 numeric=[x for x in locks if P.Path(x['path']).name.startswith(host+'.') and P.Path(x['path']).name[len(host)+1:].isdigit()];held=sum(bool(x['lock_lines']) for x in numeric);configured=vm['ram_gb']//8;unlocked=max(0,configured-held);mem=r['mem_available_bytes']/2**30;load=r['loadavg'][0];cpus=r['cpu_count']
 row={'host':host,'observed_utc':datetime.datetime.fromtimestamp(r['timestamp'],datetime.timezone.utc).isoformat(),'disk_free_GB':round(r['home_free_bytes']/1e9,2),'disk_free_bytes':r['home_free_bytes'],'memory_available_GiB':round(mem,2),'memory_total_GiB':round(r['mem_total_bytes']/2**30,2),'physical_ram_pool_GiB':vm.get('physical_ram_gb'),'cpu_count':cpus,'load1':round(load,2),'configured_8GiB_slots':configured,'locked_numeric_slots':held,'unlocked_configured_slots':unlocked,'ram_fitting_8GiB_slots':int(mem//8),'gate_16GiB_fits_now':unlocked>=2 and mem>=16 and load<cpus,'gate_20GiB_fits_now':unlocked>=3 and mem>=20 and load<cpus,'docker_running_count':sum(c['state'].get('Running',False) for c in r['docker_containers']),'docker_success':r['docker_query_returncode']==r['docker_inspect_returncode']==0,'process_read_errors':r['process_read_errors'],'manifest_count':len(r['manifests']),'host_manifest_count':sum(m['host_process'] for m in r['manifests']),'images':r['docker_images'],'tools':r['tools']}
 row['note']='Configured slots use overstated pool RAM; apply measured MemAvailable and actual physical capacity. Read-only observation, no reservation or launch.'
 if load>=cpus:row['blocking_reason']='CPU load exceeds core count; small-job gate rejects. Large-job gate bypasses CPU check, but host is saturated.'
 elif mem<20:row['blocking_reason']='Less than20GiB MemAvailable for default gate request.'
 elif unlocked<3:row['blocking_reason']='Fewer than3 unlocked8GiB configured slots.'
 rows.append(row)
(out/'worker_slot_summary.json').write_text(json.dumps({'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workers':rows,'policy':'No new builds.16/20GiB fit checks mirror current remote_gate small-job admission memory/load/numeric lock conditions; observational only. Never price capacity from overcommitted pool RAM alone.'},indent=2)+'\n')
for r in rows:print(r['host'],r.get('disk_free_GB'),r.get('memory_available_GiB'),r.get('load1'),r.get('locked_numeric_slots'),r.get('unlocked_configured_slots'),'16GiB',r.get('gate_16GiB_fits_now'),'20GiB',r.get('gate_20GiB_fits_now'))
