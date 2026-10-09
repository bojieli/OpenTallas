"""Before-build additive placement candidates for actual source-owned write joins."""
SLOTS=[dict(name='hb_write_join_'+q,x=x,y=y,w=250.584,h=250.584,orient=o) for q,x,y,o in [
 ('SW',9693.12,1211.76,'R0'),('SE',19787.328,1211.76,'MY'),
 ('NW',9693.12,23159.52,'MX'),('NE',19787.328,23159.52,'R180')]]
ORDINAL=dict(name='hb_ingest_write_ordinal',x=14763.6,y=7989.12,w=100.224,h=99.36,orient='R0')
def model(instances):
    collisions={}
    for s in SLOTS+[ORDINAL]:
        collisions[s['name']]=[i.name for i in instances if min(s['x']+s['w'],i.x+i.w)>max(s['x'],i.x) and min(s['y']+s['h'],i.y+i.h)>max(s['y'],i.y)]
    return dict(adopted=False,slots=SLOTS,ordinal=ORDINAL,collisions=collisions,
      replicas=dict(perstack_write_join=4,global_ingest_acceptance_ordinal=1),
      added_outline_um2=4*250.584**2+100.224*99.36,
      proposed_native_service_fields=dict(source=2,source_g=32,pending=1,busyPC=32,fault=1),
      prerequisite='Actual source-owned FIFO8 popGray and orderedACK; globalaccepted-stack FIFO cannot sum4local prefixACKs',
      service='Existing legacy16bitwq_g collar unchanged; fresh functional writer/servicemaster/collar must be source-pinned before any physicaljoin',
      phase='Held readyvalid merge cannot directly drive falling-fclk pulse landing; actual credit-controlled pulse adapter required',
      clock='Native K service1024ps; incoming forwarded writeclock and finiteCDC must match actual source implementation',
      latency='Actual component models fec7/6eacc and native writejoin model own service acceptance/ACK/readfence; additional diehop/finalsegment budget unmeasured',
      pin_grid='250.584 mirror dimensions have24nm phase modulo48nm for candidate M4/M5 collar; noM7viewassumed',
      physical='Geometry candidates only, no cellfit/nativepins/CTS/channelcapacity or route qualification')
