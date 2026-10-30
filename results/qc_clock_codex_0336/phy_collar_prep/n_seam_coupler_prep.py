import json,gzip,math,bisect
from pathlib import Path
bits=[b for b in json.load(gzip.open('/tmp/qcclock0336/phy_native_to_outer_bits.json.gz','rt'))['bits'] if b['type']=='phy_serdes']
tracks=[]
for layer,pitch in [('M4',.048),('M6',.064)]:
 offset=pitch/2;start=math.ceil((19.44-offset)/pitch)
 for i in range(start,start+1800,2):
  y=offset+i*pitch
  if y<86.4-2.16:tracks.append({'layer':layer,'height_um':y,'intervals':[]})
tracks.sort(key=lambda z:(z['height_um'],z['layer']))
rows=[]
# NativeN moved to slotN-.096 by proposed normalinnerY4.104. Exact shapes unchanged +.270X.
for b in sorted(bits,key=lambda z:(-abs(z['native_xy_um'][0]+.270-z['outer_xy_um'][0]),z['outer_bus'],z['bit'])):
 x=b['native_xy_um'][0]+.270;ox=b['outer_xy_um'][0];lo,hi=sorted([x,ox]);chosen=None
 for tr in tracks:
  if all(hi<=l-.064 or lo>=h+.064 for l,h in tr['intervals']):chosen=tr;break
 if chosen is None:raise ValueError(('NO_TRACK',b['outer_bus'],b['bit']))
 chosen['intervals'].append([lo,hi]);y=chosen['height_um'];path=[[x,-.096],[x,y],[ox,y],[ox,0]];length=sum(abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(path,path[1:]));rows.append({'bus':b['outer_bus'],'bit':b['bit'],'native_pin':b['native_pin'],'track_layer':chosen['layer'],'track_height_um':y,'polyline_um':path,'wire_native_to_existing_face_pin_um':length,'max_with_existing_FF_R2_30_um':length+30})
summary={'status':'EXISTING-NEIGHBOUR-SOFTSPACE COMB PREP, no extraPHYdataFF proposed, no route or signoff','native_inputs_use_actual_M5_shapes':True,'native_outline_delta':'NONE fornormalN/S; bodyinsideexistingplanSlot atinnerX.270,innerY4.104 PREP','existing_neighbour_boundary_FF_status':'LOGICALmaponly; existingphysicalXYnotqualified. R2<=30endpointbound carried, notclaimed measured.','bits':len(rows),'Hlayers':['M4','M6'],'data_track_stride':'every2actualtracks,50pct perlayer (actual offset=pitch/2)','max_track_height_um':max(r['track_height_um'] for r in rows),'max_native_to_face_wire_um':max(r['wire_native_to_existing_face_pin_um'] for r in rows),'max_with_existing_FF_R2_30_um':max(r['max_with_existing_FF_R2_30_um'] for r in rows),'paths_over405_withFF30':sum(r['max_with_existing_FF_R2_30_um']>405 for r in rows),'required_neighbour_macrofree_S_band_um':86.4,'native_TO_existing_FF_cycles_added':0,'clock_entry_model':'actualnativeM5clk x753.288,yseam-.096 -> BUF24insoftspace x779.76,yseam+2.16 about29umwire; nativeclk50fF. Actualsourcetree/nativeinternalclockunbound.','current_macros_need_repack':'Currentcoll_sfirstSRAMy43.2 so86.4macrofreeSbandisnotcurrentlyavailable. Explicit12SRAMrepackstartingy>=86.4 fits734.4macro-onlyheight butcodec/data/clock/reset/CA/FT/PGneedconstruction.','HOLD':['repeaterplacementonactualrowssite/40pctreserve','exactexistingboundaryFFXYandmasters','actualSRAM+codec+softlogicrepackwith86.4Sband','sourceTT/FF/hold/slue andnativeFDIslew','fullnativepinaccessVIA/PDN/windows','normalN/Smetadata+rootgeometryeventreview'],'mirror_scope':'S forMX normal usesexactslottransform, same localconstruction mirrored, no independent inventedSview'}
Path('/tmp/qcclock0336/n_seam_coupler_prep.json').write_text(json.dumps({'summary':summary,'bits':rows,'tracks':tracks},indent=2)+'\n');print(json.dumps(summary,indent=2))
