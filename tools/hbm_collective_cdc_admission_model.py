#!/usr/bin/env python3
"""Correctness admission before native protectedCDC integration. No selected change."""
import json
from hbm_collective_cdc_model import model as cdc_model

def model():
 base=cdc_model();deep=cdc_model(aw=8)
 return dict(status='MODEL_ONLY_NO_NATIVE_ADOPTION',existing=dict(rx_queue_depth=256,rx_cdc_depth=64,advertised_credit_fixture=256,
  real_producer='No switchegress RTL in native TU: original tb_hbm_accel_tu_endpoint.sv initializes stub eg_cred=1<<RXAW. PHY/FEC/switch remain external boundary.',
  hazard='Protected AW6 readII3 cannot absorb a legal256flit burst at oneflit/PHYcycle; packetSRAM matchedproof retained oldII1 CDC.'),
  variants=dict(
   credit64=dict(advertised_credit_limit=64,cdc_depth=64,read_II=3,extra_encoded_storage_bits=0,
    invariant='Each port: launched_not_finally_retired = forwardPHYflight + CDCmemory_including_held_head + WSTGflight + packetqueue_including_held_head <=64. Head is not an extra slot because readpointer advances only on acceptance.',
    producer='Requires source-owned acknowledged initial grant of64 from receiver, switch starts0 and spendsbeforePHYlaunch; return only on actual RXpacketqueue retirement, notCDCpop.',
    startup='One initial grant per coordinatedcoldreset generation; no regrant at contextarm. Counter/config protection and duplicate/stale grant rejection required.',
    storage_safety='All admitted traffic fits CDC64 even if downstreamstops and all64 accumulate. Inflight packets are partofsame64 outstanding tokens, not extra unreserved headroom.',
    rate_formula='min(1/3,64/(forward_flight_cycles+CDC_read_and_sync_cycles+14+packet_visibility_cycles+downstream_stall_cycles+return_credit_cycles)) flits/corecycle',
    physical_forward_flight_cycles=None,physical_return_credit_cycles=None,
    fixture_credit_return_ns=113.8,fixture_value_not_physical_contract=True,
    cost='II3 sustaineddrain and potentially smaller bandwidth-delay window; exact eventcalendar delta pending actualproducerjoin.'),
   refill_II1=dict(cdc_depth=64,read_II=1,extra_encoded_storage_bits=0,
    mechanism='On validhead pop, capture next encodedmemory word into protectedhead if nextpointer != synchronizedwritepointer; retain head phasevalid. CE/UE checks suppress nextpermission untilcorrect/normal. Empty startup retains2capture/validation cycles.',
    newlogic='nextpointergray compare and alternate captureaddress; data64:1readselect remains. Same protectedhead bank and pointer widths; contextual readmux/ECCtiming must close.',
    same_cycle_credit_reuse=False,proof_obligations=['fullstreamacceptance with phase offsets','pop/refill singleerror repair and UE','empty/full boundary and reset','native ingress256creditburst plus backendstalls'],
    limitation='II1read alone does not license downstream queue overflow or multiple creditreturns; finite globalcredit proof remains required.'),
   depth256=dict(cdc_depth=256,read_II=3,encoded_storage_bits=deep['encoded_storage_bits'],added_encoded_storage_bits=deep['encoded_storage_bits']-base['encoded_storage_bits'],
    safety='All256 externalreserved flits fit CDCalone under stop; source producer stillmust reservebeforePHYlaunch.',
    timing='2sync/capture and II3unchanged; larger256:1readmux requires physicalsplit/pipeline',
    area='No freefit: 4xencodedCDC storage plus decoder/readmux growth; no standardcellarea closure yet')),
  physical_outline='Unselected: await actualmappedstorage/control/parity/dualrail inventory plus HA2/currenthubwire/clock/PG budgets',
  selected_variant=None)
if __name__=='__main__':print(json.dumps(model(),indent=2))
