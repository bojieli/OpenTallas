#!/usr/bin/env python3
"""Prepare separate whole-record serialized observer successor; no build/run."""
import argparse,json
from pathlib import Path
from qwen_rom_source_observer_prepare import prepare,ROOT,sha

def successor(out):
 record=prepare(out)
 host=out/'qwen_rom_rt_observed.cpp';header=out/'qwen_rom_observer.hpp'
 if sha(host.read_bytes())!='d42a775f630831d3f7640e1b439902f1d3ee07d1b92629375f090a5e4b93b6ad' or sha(header.read_bytes())!='6c37db03c5fb524bd86a3b63621cdef2dc63e37bd626b6a5ea715d6b42245fcd':raise ValueError('reviewed original source/header changed')
 candidate=ROOT/'rtl/test/qwen_rom_runtime/observer/qwen_rom_observer_serialized_r1.hpp'
 header.write_bytes(candidate.read_bytes())
 record.update(status='PREPARED_SERIALIZED_HOST_SUCCESSOR_NO_BUILD_OR_RUN',host_sha256=sha(host.read_bytes()),serialized_header_sha256=sha(header.read_bytes()),original_header_sha256='6c37db03c5fb524bd86a3b63621cdef2dc63e37bd626b6a5ea715d6b42245fcd',whole_record_lock=True,model_added_DUT_cycles=0,model_added_hardware_area=0,original_live_job_modified=False)
 (out/'preparation.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
 return record

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();successor(a.out)

if __name__=='__main__':main()
