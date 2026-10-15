/* Physical connections are distinct from token dependencies. Missing direction,
 * rate or placement is displayed as unknown; widths never imply bits/cycle. */
(function () {
'use strict';
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const rate = n => Number.isFinite(n) && n >= 0 ? n >= 1e9 ? (n/1e9).toFixed(2)+' Gbit/s' : n >= 1e6 ? (n/1e6).toFixed(2)+' Mbit/s' : n.toLocaleString()+' bit/s' : 'unknown';
const width = e => Number.isFinite(e.width_bits) && e.width_bits > 0 ? e.width_bits.toLocaleString()+' bits' : 'width unknown';
const endpointName = p => typeof p === 'string' ? p : p?.instance ?? p?.name ?? '';
window.ChipDataflow = {mount({state, redraw}) {
  const button = document.getElementById('dataflow'), center = document.getElementById('center');
  const panel = document.createElement('section'); panel.hidden = true; panel.className = 'df-panel';
  panel.setAttribute('aria-label', 'Data flow connections');
  panel.innerHTML = '<b>Data flow</b><div class="df-controls"><select aria-label="Connection scope"><option value="all">All connections</option><option value="selected">Selected element</option><option value="critical">Critical paths</option></select><label><input type="checkbox" checked> Width labels</label></div><input class="df-search" type="search" aria-label="Filter connections" placeholder="Filter connection or endpoint"><div class="df-summary" role="status"></div><div class="df-list"></div><div class="df-detail"></div>';
  center.append(panel);
  const style = document.createElement('style'); style.textContent = '.df-panel{position:absolute;right:10px;top:76px;width:min(350px,calc(100% - 20px));max-height:54%;overflow:auto;background:#070b16ed;border:1px solid #2a3558;border-radius:10px;padding:10px;z-index:6;font:11px var(--mono);color:var(--ink)}.df-controls{display:flex;gap:8px;align-items:center;margin:7px 0;flex-wrap:wrap}.df-controls select{max-width:180px;font-size:11px}.df-controls label{white-space:nowrap}.df-search{width:100%;font-size:11px!important}.df-summary{color:var(--dim);line-height:1.5;margin:7px 0}.df-list{max-height:160px;overflow:auto}.df-list button{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line);background:none;padding:6px;color:var(--ink);font:11px var(--mono);cursor:pointer;overflow-wrap:anywhere}.df-list button:hover,.df-list button[aria-pressed=true]{background:#16244a}.df-detail{white-space:normal;overflow-wrap:anywhere;line-height:1.5;color:var(--dim);margin-top:8px}.df-detail b{color:var(--ink)}'; document.head.append(style);
  const scope = panel.querySelector('select'), labels = panel.querySelector('input[type=checkbox]'), search = panel.querySelector('input[type=search]');
  const summary = panel.querySelector('.df-summary'), list = panel.querySelector('.df-list'), detail = panel.querySelector('.df-detail');
  let enabled = false, currentDie = null, data = null, error = '', loading = false, serial = 0, key = '', picked = null, segments = [];
  let filteredData=null, filteredSelection=null, filteredQuery='', filteredScope='', filtered=[];
  const helper = import('/explorer/dataflow.js');
  function names(e) { return e.endpoints?.length ? e.endpoints.map(endpointName) : [endpointName(e.src), endpointName(e.dst)]; }
  function visibleEdges(g) {
    if (!data) return [];
    const s = state(), chosen = new Set((s.sel?.insts || []).map(i => g.names[i])), q = search.value.trim().toLowerCase();
    if(filteredData===data && filteredSelection===s.sel && filteredQuery===q && filteredScope===scope.value)return filtered;
    filteredData=data;filteredSelection=s.sel;filteredQuery=q;filteredScope=scope.value;
    return filtered=data.edges.filter(e => (scope.value !== 'selected' || names(e).some(n => chosen.has(n))) &&
      (scope.value !== 'critical' || e.critical === true) && (!q || [e.id,e.label,...names(e)].join(' ').toLowerCase().includes(q)))
      .sort((a,b) => (b.width_bits || 0)-(a.width_bits || 0));
  }
  function select(e) {
    picked = e.id;
    const ns = names(e), source = typeof e.source === 'object' ? JSON.stringify(e.source) : e.source;
    detail.innerHTML = '<b>'+esc(e.label || e.id)+'</b><br>'+ns.map(esc).join(e.direction === 'unknown' || !e.direction ? ' ↔ ' : ' → ')+'<br><b>'+esc(width(e))+'</b><br>Required bandwidth: '+esc(rate(e.required_bps))+'<br>Capacity: '+esc(rate(e.capacity_bps))+'<br>Direction: '+esc(e.direction || 'unknown')+'<br>Path: '+esc(e.route_kind || 'logical connection; physical route not supplied')+'<br>Source: '+esc(source || data.provenance?.source || 'not supplied');
    key = ''; redraw();
  }
  function update(g, edges, mapped) {
    const s = state(), next = [currentDie,loading,error,data?.edges.length,scope.value,search.value,(s.sel?.insts || []).join(','),picked].join('|');
    if (next === key) return; key = next;
    if (loading) summary.textContent = 'Loading source connections…';
    else if (error) summary.textContent = 'Connections unavailable: '+error;
    else summary.textContent = edges.length.toLocaleString()+' matching connections; '+mapped.toLocaleString()+' drawn (up to 300). '+(data?.edges.length ? 'Dashed paths have unverified direction. Straight lines show connectivity, not routed wires. Bandwidth is unknown without a source schedule. Snapshot '+(data.provenance?.commit?.slice(0,12)||'source not supplied')+'. '+(data.coverage?.omitted_broadcast_endpoints ? data.coverage.omitted_broadcast_endpoints.toLocaleString()+' broadcast endpoints omitted by this cached geometry.' : '') : 'No source connection data is available for this geometry.');
    list.replaceChildren();
    for (const e of edges.slice(0,80)) {
      const b = document.createElement('button'); b.type='button'; b.setAttribute('aria-pressed',String(picked===e.id));
      b.textContent = width(e)+' · '+(e.label || e.id || names(e).join(' — ')); b.onclick=()=>select(e); list.append(b);
    }
    if (!edges.length && scope.value === 'selected' && !s.sel) detail.textContent='Select an element on the map to inspect its connections.';
    else if (!edges.length && scope.value === 'critical') detail.textContent='No source-qualified critical-path mapping is available in this scope.';
  }
  async function load(die) {
    currentDie=die; data=null; error=''; loading=true; picked=null; detail.textContent=''; key=''; const request=++serial; redraw();
    try {
      const [mod,r] = await Promise.all([helper,fetch('/api/explorer/dataflow?die='+encodeURIComponent(die)+(new URLSearchParams(location.search).has('safe')?'&safe=1':''),{cache:'no-store'})]);
      if (!r.ok) throw new Error('HTTP '+r.status);
      const payload=await r.json(); if (request!==serial) return;
      data=mod.normalizeDataflow(payload);
    } catch(e) { if(request===serial) error=e.message; }
    finally { if(request===serial){loading=false;key='';redraw();} }
  }
  button.onclick=()=>{enabled=!enabled;panel.hidden=!enabled;button.setAttribute('aria-pressed',String(enabled));if(enabled && currentDie!==state().die)load(state().die);redraw();};
  for(const control of [scope,labels,search])control.addEventListener(control===search?'input':'change',()=>{key='';redraw();});
  return {
    setDie(die){if(enabled && currentDie!==die)load(die);},
    paint(g,X,Y){
      if(!enabled)return;
      const edges=visibleEdges(g), index=g.dataflowIndex ||= new Map(g.names.map((n,i)=>[n,i])); segments=[];
      const c=document.getElementById('map').getContext('2d');c.save();c.lineCap='round';
      let mapped=0, nlabels=0;const occupied=[];
      for(const e of edges){
        if(mapped>=300)break;
        const eps=e.endpoints?.length?e.endpoints:[{instance:e.src,point:e.from},{instance:e.dst,point:e.to}];
        const pts=eps.map(p=>{
          if(Array.isArray(p.point)&&p.point.length===2&&p.point.every(Number.isFinite))return[X(p.point[0]),Y(p.point[1])];
          const i=index.get(endpointName(p));return i===undefined?null:[X(g.x[i]+g.w[i]/2),Y(g.y[i]+g.h[i]/2)];
        }).filter(Boolean);
        if(pts.length<2)continue;
        const known=e.direction && e.direction!=='unknown' && e.direction!=='undirected';
        const color=picked===e.id?'#fff':known?'#5ee7ff':'#fbbf24';
        c.strokeStyle=color;c.fillStyle=color;c.globalAlpha=picked && picked!==e.id ? .45 : .85;
        c.lineWidth=Math.min(5,1+Math.log2((e.width_bits||1)+1)/4);c.setLineDash(known?[]:[5,4]);
        for(let j=1;j<pts.length;j++){
          const a=pts[0],b=pts[j],dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy);if(len<2)continue;
          c.beginPath();c.moveTo(...a);c.lineTo(...b);c.stroke();segments.push({a,b,e});
          if(known){const angle=Math.atan2(dy,dx);c.setLineDash([]);c.beginPath();c.moveTo(...b);c.lineTo(b[0]-9*Math.cos(angle-.45),b[1]-9*Math.sin(angle-.45));c.lineTo(b[0]-9*Math.cos(angle+.45),b[1]-9*Math.sin(angle+.45));c.closePath();c.fill();}
          if(labels.checked && nlabels<35 && len>45){
            const text=width(e),x=(a[0]+b[0])/2,y=(a[1]+b[1])/2;c.font='11px ui-monospace,monospace';const w=c.measureText(text).width+8;
            if(!occupied.some(r=>Math.abs(r.x-x)<(r.w+w)/2 && Math.abs(r.y-y)<16)){occupied.push({x,y,w});c.fillStyle='#070b16';c.fillRect(x-w/2,y-9,w,15);c.fillStyle=color;c.textAlign='center';c.fillText(text,x,y+2);nlabels++;}
          }
        }mapped++;
      }
      c.restore();update(g,edges,mapped);
    },
    inspect(px,py){if(!enabled)return false;let best=null,distance=7;for(const s of segments){const dx=s.b[0]-s.a[0],dy=s.b[1]-s.a[1],v=dx*dx+dy*dy;if(!v)continue;const t=Math.max(0,Math.min(1,((px-s.a[0])*dx+(py-s.a[1])*dy)/v));const d=Math.hypot(px-s.a[0]-t*dx,py-s.a[1]-t*dy);if(d<distance){distance=d;best=s.e;}}if(best){select(best);return true;}return false;}
  };
}};
})();
