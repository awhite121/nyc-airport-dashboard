(() => {
  'use strict';

  const DATA = window.APP_DATA;
  if (!DATA) {
    document.body.innerHTML = '<main style="padding:40px;color:white;font-family:system-ui"><h1>Dashboard data did not load.</h1><p>Use the standalone dashboard file or serve this folder with a local web server.</p></main>';
    return;
  }

  const DOW = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
  const FULL_DOW = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
  const fmtInt = new Intl.NumberFormat('en-US');
  const zoneById = new Map(DATA.zones.map(z => [Number(z.id), z]));
  const state = {
    tab: 'planner',
    zoneId: zoneById.has(161) ? 161 : DATA.zones[0].id,
    airport: 'JFK',
    risk: 'standard',
    mapMode: 'manhattan',
    analyticsAirport: 'ALL',
    analyticsMetric: 'avg',
    showZones: 10,
    lastPlan: null,
  };

  const $ = (sel, root=document) => root.querySelector(sel);
  const $$ = (sel, root=document) => [...root.querySelectorAll(sel)];
  const clamp = (v,min,max) => Math.max(min,Math.min(max,v));
  const pct = v => `${Math.round((v || 0) * 100)}%`;
  const mins = v => `${Math.round(v)} min`;
  const formatTime = d => d.toLocaleTimeString([], {hour:'numeric', minute:'2-digit'});
  const formatDate = d => d.toLocaleDateString([], {weekday:'long', month:'short', day:'numeric'});
  const titleHour = h => new Date(2020,0,1,h).toLocaleTimeString([], {hour:'numeric'});
  const localDow = d => (d.getDay() + 6) % 7;

  function showToast(message) {
    const el = $('#toast');
    el.textContent = message;
    el.classList.add('show');
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => el.classList.remove('show'), 2200);
  }

  function setDefaults() {
    const now = new Date();
    const flight = new Date(now);
    flight.setDate(flight.getDate() + 1);
    flight.setHours(15,0,0,0);
    $('#flightDate').value = `${flight.getFullYear()}-${String(flight.getMonth()+1).padStart(2,'0')}-${String(flight.getDate()).padStart(2,'0')}`;
    $('#flightTime').value = '15:00';
    $('#flightType').value = 'domestic';
    $('#passengers').value = String(DATA.defaults.passengers || 1);
  }

  function populateZones() {
    const select = $('#zoneSelect');
    select.innerHTML = DATA.zones.map(z => `<option value="${z.id}">${escapeHtml(z.name)}</option>`).join('');
    select.value = String(state.zoneId);
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  }

  function setTab(tab, pushHash=true) {
    state.tab = tab;
    $$('.tab').forEach(b => b.classList.toggle('is-active', b.dataset.tab === tab));
    $$('.view').forEach(v => v.classList.toggle('is-active', v.dataset.view === tab));
    if (pushHash) history.replaceState(null,'',`#${tab}`);
    if (tab === 'analytics') renderAnalytics();
    if (tab === 'model') renderModel();
    window.scrollTo({top:0,behavior:'smooth'});
  }

  function setAirport(airport) {
    state.airport = airport;
    $$('.segment').forEach(b => b.classList.toggle('is-active', b.dataset.airport === airport));
    renderPlannerMap();
    calculateRecommendation(false);
  }

  function prediction(zoneId, airport, dateOrDow, hourMaybe) {
    let dow, hour;
    if (dateOrDow instanceof Date) {
      dow = localDow(dateOrDow);
      hour = dateOrDow.getHours();
    } else {
      dow = Number(dateOrDow);
      hour = Number(hourMaybe);
    }
    const raw = DATA.predictions[`${zoneId}|${airport}|${dow}|${hour}`];
    if (!raw) return null;
    return {
      expected: raw[0], p80: raw[1], p90: raw[2], risk: raw[3], distance: raw[4],
      exactTrips: raw[5], support: raw[6], actualMean: raw[7], actualP80: raw[8], actualRisk: raw[9],
      dow, hour,
    };
  }

  function baseRiskBuffer(risk) {
    if (risk >= .62) return 28;
    if (risk >= .48) return 22;
    if (risk >= .34) return 17;
    if (risk >= .21) return 12;
    return 7;
  }

  function roadBudgetFor(pred, style) {
    const base = baseRiskBuffer(pred.risk);
    if (style === 'safer') return Math.max(pred.p90, pred.p80 + 8, pred.expected + base + 10);
    if (style === 'maximum') return Math.max(pred.p90 + 15, pred.p80 + 20, pred.expected + base + 24);
    return Math.max(pred.p80, pred.expected + base);
  }

  function readFlightDate() {
    const date = $('#flightDate').value;
    const time = $('#flightTime').value;
    if (!date || !time) return null;
    const d = new Date(`${date}T${time}:00`);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function solvePlan() {
    const flight = readFlightDate();
    if (!flight) return {error:'Choose a valid flight date and time.'};
    const checkin = $('#flightType').value === 'international' ? 150 : 90;
    const pickupWait = state.risk === 'maximum' ? 12 : state.risk === 'safer' ? 10 : 8;
    const terminal = new Date(flight.getTime() - checkin * 60000);
    let leave = new Date(terminal.getTime() - 65 * 60000);
    let pred = prediction(state.zoneId, state.airport, leave);
    let roadBudget = 0;
    for (let i=0;i<6;i++) {
      pred = prediction(state.zoneId, state.airport, leave);
      if (!pred) return {error:'No prediction is available for this selection.'};
      roadBudget = roadBudgetFor(pred, state.risk);
      leave = new Date(terminal.getTime() - (roadBudget + pickupWait) * 60000);
    }
    pred = prediction(state.zoneId, state.airport, leave);
    roadBudget = roadBudgetFor(pred, state.risk);
    leave = new Date(terminal.getTime() - (roadBudget + pickupWait) * 60000);
    return {flight,terminal,leave,pred,checkin,pickupWait,roadBudget};
  }

  function calculateRecommendation(notify=true) {
    const plan = solvePlan();
    if (plan.error) { showToast(plan.error); return; }
    state.lastPlan = plan;
    const zone = zoneById.get(state.zoneId);
    const {flight,terminal,leave,pred,checkin,pickupWait,roadBudget} = plan;

    $('#leaveTime').textContent = formatTime(leave);
    $('#leaveDate').textContent = `${formatDate(leave)} · includes ${pickupWait} min pickup allowance`;
    $('#riskPercent').textContent = pct(pred.risk);
    $('#routeFrom').textContent = zone.name;
    $('#routeTo').textContent = state.airport;
    $('#terminalArrival').textContent = `${formatTime(terminal)} · ${formatDate(terminal)}`;
    $('#flightBufferLabel').textContent = `${checkin} min airport buffer before ${formatTime(flight)} flight`;
    $('#expectedDuration').textContent = mins(pred.expected);
    $('#p80Duration').textContent = mins(pred.p80);
    $('#roadBudget').textContent = mins(roadBudget);
    $('#tripDistance').textContent = `${pred.distance.toFixed(1)} mi`;

    const confidence = pred.support >= 500 ? 'High' : pred.support >= 150 ? 'Medium' : 'Limited';
    $('#confidenceBadge').textContent = `${confidence} confidence`;
    $('#confidenceBadge').style.color = confidence === 'High' ? 'var(--accent)' : confidence === 'Medium' ? 'var(--warning)' : 'var(--danger)';

    renderDrivers(plan);
    renderAlternatives(plan);
    renderPlannerMap();
    if (notify) showToast('Leave-by recommendation updated');
  }

  function renderDrivers(plan) {
    const {pred,leave} = plan;
    const zone = zoneById.get(state.zoneId);
    const baseline = prediction(state.zoneId,state.airport,1,10);
    const otherAirport = state.airport === 'JFK' ? 'LGA' : 'JFK';
    const other = prediction(state.zoneId,otherAirport,leave);
    const apStat = DATA.analytics.airports.find(a => a.airport === state.airport);
    const timeDelta = pred.expected - baseline.expected;
    const airportDelta = other ? pred.expected - other.expected : 0;
    const zoneDelta = pred.expected - apStat.avg;
    const items = [
      {icon:'◷',title:`${FULL_DOW[pred.dow]} around ${titleHour(pred.hour)}`,copy:`Compared with a Tuesday 10 AM trip from the same zone`,value:`${timeDelta >= 0 ? '+' : ''}${Math.round(timeDelta)} min`},
      {icon:'✈',title:`${state.airport} route effect`,copy:`Compared with ${otherAirport} from the same pickup zone and hour`,value:`${airportDelta >= 0 ? '+' : ''}${Math.round(airportDelta)} min`},
      {icon:'⌖',title:zone.name,copy:`Compared with the ${state.airport} average across Manhattan`,value:`${zoneDelta >= 0 ? '+' : ''}${Math.round(zoneDelta)} min`},
      {icon:'!',title:'Unusually slow-trip probability',copy:DATA.meta.lateDefinition,value:pct(pred.risk)},
    ];
    $('#driverList').innerHTML = items.map(i => `<div class="driver-row"><div class="driver-icon">${i.icon}</div><div class="driver-copy"><strong>${escapeHtml(i.title)}</strong><span>${escapeHtml(i.copy)}</span></div><div class="driver-value">${escapeHtml(i.value)}</div></div>`).join('');

    const exact = pred.exactTrips;
    const historical = exact >= 5 && pred.actualMean != null
      ? `<strong>${fmtInt.format(exact)} closely matched rides</strong> averaged ${Math.round(pred.actualMean)} minutes; their 80th percentile was ${Math.round(pred.actualP80)} minutes.`
      : `<strong>${fmtInt.format(pred.support)} rides support this zone-to-airport route.</strong> The exact weekday/hour bucket has ${fmtInt.format(exact)} rides, so the model borrows strength from nearby patterns.`;
    $('#evidenceBox').innerHTML = `${historical} The instant prediction uses pre-scored model output for this zone, airport, weekday, and hour.`;
  }

  function renderAlternatives(plan) {
    const choices = [
      {offset:-30,label:'Extra breathing room'},
      {offset:0,label:'Recommended window'},
      {offset:15,label:'Tighter departure'},
    ];
    $('#alternativeList').innerHTML = choices.map(c => {
      const depart = new Date(plan.leave.getTime() + c.offset * 60000);
      const p = prediction(state.zoneId,state.airport,depart);
      const projectedTerminal = new Date(depart.getTime() + (p.p80 + plan.pickupWait) * 60000);
      const slack = Math.round((plan.terminal - projectedTerminal)/60000);
      const status = slack >= 15 ? `${slack} min cushion` : slack >= 0 ? `${slack} min cushion` : `${Math.abs(slack)} min late vs target`;
      return `<div class="alternative-row"><div class="alt-time">${formatTime(depart)}</div><div class="alt-copy"><strong>${c.label}</strong><span>${status} · ${Math.round(p.p80)} min slower-range drive</span></div><div class="alt-risk">${pct(p.risk)} risk</div></div>`;
    }).join('');
  }

  function mapBounds(mode, airport) {
    if (mode === 'route') {
      return airport === 'JFK'
        ? {minLon:-74.035,maxLon:-73.755,minLat:40.615,maxLat:40.895}
        : {minLon:-74.035,maxLon:-73.845,minLat:40.69,maxLat:40.895};
    }
    return {minLon:-74.025,maxLon:-73.90,minLat:40.69,maxLat:40.89};
  }

  function projector(bounds, width, height, padding=32) {
    return (lon,lat) => {
      const x = padding + (lon-bounds.minLon)/(bounds.maxLon-bounds.minLon)*(width-padding*2);
      const y = height-padding - (lat-bounds.minLat)/(bounds.maxLat-bounds.minLat)*(height-padding*2);
      return [x,y];
    };
  }

  function svgGrid(width,height) {
    let s='';
    for(let x=50;x<width;x+=70)s+=`<line class="map-grid" x1="${x}" y1="20" x2="${x}" y2="${height-20}"/>`;
    for(let y=50;y<height;y+=70)s+=`<line class="map-grid" x1="20" y1="${y}" x2="${width-20}" y2="${y}"/>`;
    return s;
  }

  function renderPlannerMap() {
    const svg = $('#zoneMap');
    if (!svg) return;
    const W=760,H=510,bounds=mapBounds(state.mapMode,state.airport),project=projector(bounds,W,H,36);
    const selected=zoneById.get(state.zoneId), ap=DATA.airports[state.airport];
    const [sx,sy]=project(selected.lon,selected.lat),[ax,ay]=project(ap.lon,ap.lat);
    let html=svgGrid(W,H);
    if(state.mapMode==='route') html+=`<line class="route-line-svg" x1="${sx}" y1="${sy}" x2="${ax}" y2="${ay}"/>`;
    DATA.zones.forEach(z=>{
      const [x,y]=project(z.lon,z.lat);
      if(x<0||x>W||y<0||y>H)return;
      const isSelected=z.id===state.zoneId;
      const r=isSelected?7:clamp(3.2+Math.sqrt(z.trips)/24,3.2,5.8);
      html+=`<circle class="zone-point${isSelected?' selected':''}" data-zone-id="${z.id}" tabindex="0" role="button" aria-label="Select ${escapeHtml(z.name)}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}" fill="${isSelected?'var(--accent)':'#66857a'}" opacity="${isSelected?1:.73}"/>`;
    });
    if(state.mapMode==='route'){
      html+=`<circle class="airport-marker" cx="${ax}" cy="${ay}" r="9"/><text class="map-label" x="${ax+14}" y="${ay-3}">${state.airport}</text><text class="map-sublabel" x="${ax+14}" y="${ay+11}">selected airport</text>`;
    }
    html+=`<text class="map-label" x="${sx+12}" y="${sy-8}">${escapeHtml(shortZone(selected.name))}</text><text class="map-sublabel" x="${sx+12}" y="${sy+5}">selected pickup</text>`;
    svg.innerHTML=html;
    bindMapPoints(svg,$('#mapTooltip'));
  }

  function shortZone(name){return name.length>24?`${name.slice(0,22)}…`:name}

  function bindMapPoints(svg,tooltip){
    $$('.zone-point',svg).forEach(point=>{
      const id=Number(point.dataset.zoneId),zone=zoneById.get(id);
      const activate=()=>{state.zoneId=id;$('#zoneSelect').value=String(id);renderPlannerMap();calculateRecommendation(false)};
      point.addEventListener('click',activate);
      point.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate()}});
      point.addEventListener('pointerenter',e=>showMapTooltip(e,tooltip,zone));
      point.addEventListener('pointermove',e=>positionTooltip(e,tooltip));
      point.addEventListener('pointerleave',()=>tooltip.classList.remove('is-visible'));
      point.addEventListener('focus',e=>showMapTooltip(e,tooltip,zone,true));
      point.addEventListener('blur',()=>tooltip.classList.remove('is-visible'));
    });
  }

  function showMapTooltip(e,tooltip,zone,keyboard=false){
    const ap=zone.airports[state.airport]||zone;
    tooltip.innerHTML=`<strong>${escapeHtml(zone.name)}</strong><span>${fmtInt.format(ap.trips||zone.trips)} ${state.airport} rides · ${Math.round(ap.avg||zone.avg)} min average</span>`;
    tooltip.classList.add('is-visible');
    if(!keyboard)positionTooltip(e,tooltip);
    else {tooltip.style.left='50%';tooltip.style.top='18%'}
  }
  function positionTooltip(e,tooltip){
    const rect=tooltip.parentElement.getBoundingClientRect();
    tooltip.style.left=`${e.clientX-rect.left}px`;tooltip.style.top=`${e.clientY-rect.top}px`;
  }

  function aggregateRows(rows,keyField,keyValue) {
    const filtered = keyValue==='ALL' ? rows : rows.filter(r=>r.airport===keyValue);
    const groups=new Map();
    filtered.forEach(r=>{
      const key=r[keyField];
      const g=groups.get(key)||{trips:0,avgNum:0,p80Num:0,riskNum:0};
      g.trips+=r.trips;g.avgNum+=r.avg*r.trips;g.p80Num+=r.p80*r.trips;g.riskNum+=r.lateRate*r.trips;groups.set(key,g);
    });
    return [...groups.entries()].map(([key,g])=>({[keyField]:Number(key),trips:g.trips,avg:g.avgNum/g.trips,p80:g.p80Num/g.trips,lateRate:g.riskNum/g.trips})).sort((a,b)=>a[keyField]-b[keyField]);
  }

  function selectedZoneMetric(z,airport,metric) {
    const s=airport==='ALL'?z:z.airports[airport];
    return s ? Number(s[metric]) : 0;
  }

  function renderAnalytics() {
    const airport=state.analyticsAirport,metric=state.analyticsMetric;
    const hourly=aggregateRows(DATA.analytics.hourly,'hour',airport);
    const weekdays=aggregateRows(DATA.analytics.weekdays,'dow',airport);
    const zones=DATA.zones.map(z=>({z,value:selectedZoneMetric(z,airport,metric)})).filter(x=>Number.isFinite(x.value));
    const tripRows=airport==='ALL'?DATA.analytics.airports:DATA.analytics.airports.filter(a=>a.airport===airport);
    const total=tripRows.reduce((s,r)=>s+r.trips,0);
    const avg=tripRows.reduce((s,r)=>s+r.avg*r.trips,0)/total;
    const p80=tripRows.reduce((s,r)=>s+r.p80*r.trips,0)/total;
    const risk=tripRows.reduce((s,r)=>s+r.lateRate*r.trips,0)/total;
    const peak=hourly.reduce((a,b)=>b[metric]>a[metric]?b:a,hourly[0]);
    const unit=metric==='lateRate'?'%':'min';
    const peakText=metric==='lateRate'?pct(peak[metric]):mins(peak[metric]);
    $('#analyticsKpis').innerHTML=[
      ['Trips analyzed',fmtInt.format(total),airport==='ALL'?'Both airports':airport],
      ['Average duration',mins(avg),'historical mean'],
      ['Slower-range',mins(p80),'weighted p80'],
      ['Late-trip rate',pct(risk),DATA.meta.lateDefinition],
      ['Peak exposure',titleHour(peak.hour),peakText],
    ].map(([l,v,s])=>`<article class="metric-card"><span>${l}</span><strong>${v}</strong><small>${escapeHtml(s)}</small></article>`).join('');
    $('#hourlyChartTitle').textContent=`${metricLabel(metric)} throughout the day`;
    $('#hourlyUnit').textContent=unit==='%'?'percent':'minutes';
    renderLineChart($('#hourlyChart'),hourly.map(r=>({x:r.hour,y:metric==='lateRate'?r[metric]*100:r[metric]})),unit);
    renderWeekdayBars($('#weekdayChart'),weekdays,metric);
    renderAirportComparison();
    renderHeatmap();
    renderZoneTable(zones);
    renderAnalyticsMap(zones);
  }

  function metricLabel(metric){return metric==='avg'?'Average duration':metric==='p80'?'80th-percentile duration':'Late-trip rate'}

  function renderLineChart(host,points,unit){
    const W=860,H=300,p={l:48,r:20,t:18,b:36};
    const ys=points.map(d=>d.y),min=Math.min(...ys),max=Math.max(...ys),lo=Math.max(0,min-(max-min)*.2),hi=max+(max-min||1)*.18;
    const x=v=>p.l+v/23*(W-p.l-p.r),y=v=>H-p.b-(v-lo)/(hi-lo)*(H-p.t-p.b);
    const path=points.map((d,i)=>`${i?'L':'M'}${x(d.x).toFixed(1)},${y(d.y).toFixed(1)}`).join(' ');
    let grid='';for(let i=0;i<5;i++){const val=lo+(hi-lo)*i/4,yy=y(val);grid+=`<line class="chart-axis" x1="${p.l}" y1="${yy}" x2="${W-p.r}" y2="${yy}"/><text class="chart-axis-text" x="${p.l-8}" y="${yy+3}" text-anchor="end">${unit==='%'?Math.round(val)+'%':Math.round(val)}</text>`}
    const labels=points.filter(d=>[0,4,8,12,16,20,23].includes(d.x)).map(d=>`<text class="chart-axis-text" x="${x(d.x)}" y="${H-12}" text-anchor="middle">${titleHour(d.x)}</text>`).join('');
    const circles=points.map(d=>`<circle class="chart-point" cx="${x(d.x)}" cy="${y(d.y)}" r="3"><title>${titleHour(d.x)}: ${d.y.toFixed(1)}${unit}</title></circle>`).join('');
    host.innerHTML=`<svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Hourly ${metricLabel(state.analyticsMetric)} chart"><defs><linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--accent)" stop-opacity=".24"/><stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></linearGradient></defs>${grid}<path class="chart-area" d="${path} L${x(23)},${H-p.b} L${x(0)},${H-p.b} Z"/><path class="chart-path" d="${path}"/>${circles}${labels}</svg>`;
  }

  function renderWeekdayBars(host,rows,metric){
    const values=rows.map(r=>metric==='lateRate'?r[metric]*100:r[metric]),max=Math.max(...values)*1.08;
    const W=520,H=300,p={l:78,r:45,t:10,b:10},rowH=(H-p.t-p.b)/7;
    let html='';rows.forEach((r,i)=>{const val=values[i],w=(W-p.l-p.r)*val/max,y=p.t+i*rowH+8;html+=`<text class="bar-label" x="${p.l-10}" y="${y+10}" text-anchor="end">${DOW[r.dow]}</text><rect class="bar-track" x="${p.l}" y="${y}" width="${W-p.l-p.r}" height="14" rx="7"/><rect class="bar-fill" x="${p.l}" y="${y}" width="${w}" height="14" rx="7"><title>${DOW[r.dow]}: ${metric==='lateRate'?val.toFixed(1)+'%':val.toFixed(1)+' min'}</title></rect><text class="bar-value" x="${p.l+w+7}" y="${y+10}">${metric==='lateRate'?val.toFixed(1)+'%':val.toFixed(1)}</text>`});
    host.innerHTML=`<svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Weekday comparison">${html}</svg>`;
  }

  function renderAirportComparison(){
    $('#airportComparison').innerHTML=DATA.analytics.airports.map(a=>`<article class="airport-compare-card"><div class="airport-row"><div><strong>${a.airport}</strong><span>${escapeHtml(DATA.airports[a.airport].name)}</span></div><b>${fmtInt.format(a.trips)} rides</b></div><div class="compare-metrics"><div><small>Average</small><b>${mins(a.avg)}</b></div><div><small>P80</small><b>${mins(a.p80)}</b></div><div><small>Late rate</small><b>${pct(a.lateRate)}</b></div></div></article>`).join('');
  }

  function modeledHeatRows(){
    const aps=state.analyticsAirport==='ALL'?['JFK','LGA']:[state.analyticsAirport];
    const metric=state.analyticsMetric,rows=[];
    for(let dow=0;dow<7;dow++)for(let hour=0;hour<24;hour++){
      const vals=[];
      DATA.zones.forEach(z=>aps.forEach(ap=>{const p=prediction(z.id,ap,dow,hour);vals.push(metric==='avg'?p.expected:metric==='p80'?p.p80:p.risk)}));
      rows.push({dow,hour,value:vals.reduce((a,b)=>a+b,0)/vals.length});
    }
    return rows;
  }

  function renderHeatmap(){
    const rows=modeledHeatRows(),vals=rows.map(r=>r.value),min=Math.min(...vals),max=Math.max(...vals),metric=state.analyticsMetric;
    let html='<div></div>'+Array.from({length:24},(_,h)=>`<div class="heat-label">${h%3===0?h:''}</div>`).join('');
    for(let d=0;d<7;d++){
      html+=`<div class="heat-label heat-day">${DOW[d]}</div>`;
      for(let h=0;h<24;h++){
        const r=rows.find(x=>x.dow===d&&x.hour===h),t=(r.value-min)/(max-min||1),alpha=.08+t*.88;
        const display=metric==='lateRate'?pct(r.value):mins(r.value);
        html+=`<div class="heat-cell" style="background:rgba(104,224,180,${alpha.toFixed(3)})" data-tip="${DOW[d]} ${titleHour(h)} · ${display}"></div>`;
      }
    }
    $('#heatmap').innerHTML=`<div class="heatmap-grid">${html}</div>`;
  }

  function renderZoneTable(zoneValues){
    const desc=[...zoneValues].sort((a,b)=>b.value-a.value).slice(0,state.showZones);
    const max=Math.max(...desc.map(x=>x.value),1),metric=state.analyticsMetric;
    $('#showAllZones').textContent=state.showZones===10?'Show 15':'Show 10';
    $('#zoneTable').innerHTML=`<table class="zone-table"><thead><tr><th>Zone</th><th>Trips</th><th>${metricLabel(metric)}</th></tr></thead><tbody>${desc.map((x,i)=>{const s=state.analyticsAirport==='ALL'?x.z:x.z.airports[state.analyticsAirport];const display=metric==='lateRate'?pct(x.value):mins(x.value);return `<tr><td><div class="rank-zone"><span class="rank-num">${i+1}</span><span>${escapeHtml(x.z.name)}<div class="metric-bar"><i style="width:${x.value/max*100}%"></i></div></span></div></td><td>${fmtInt.format(s?.trips||x.z.trips)}</td><td><strong>${display}</strong></td></tr>`}).join('')}</tbody></table>`;
  }

  function renderAnalyticsMap(zoneValues){
    const svg=$('#analyticsMap'),W=620,H=470,bounds=mapBounds('manhattan','JFK'),project=projector(bounds,W,H,28);
    const vals=zoneValues.map(x=>x.value),min=Math.min(...vals),max=Math.max(...vals),byId=new Map(zoneValues.map(x=>[x.z.id,x.value]));
    let html=svgGrid(W,H);
    DATA.zones.forEach(z=>{const [x,y]=project(z.lon,z.lat),v=byId.get(z.id)||0,t=(v-min)/(max-min||1),r=clamp(3+Math.sqrt(z.trips)/22,3.5,8),alpha=.14+t*.85;html+=`<circle class="zone-point" data-zone-id="${z.id}" cx="${x}" cy="${y}" r="${r}" fill="rgba(104,224,180,${alpha})" tabindex="0"><title>${escapeHtml(z.name)}: ${state.analyticsMetric==='lateRate'?pct(v):mins(v)}</title></circle>`});
    svg.innerHTML=html;
    const tt=$('#analyticsTooltip');
    $$('.zone-point',svg).forEach(point=>{const zone=zoneById.get(Number(point.dataset.zoneId));point.addEventListener('pointerenter',e=>{const v=byId.get(zone.id);tt.innerHTML=`<strong>${escapeHtml(zone.name)}</strong><span>${metricLabel(state.analyticsMetric)}: ${state.analyticsMetric==='lateRate'?pct(v):mins(v)}</span>`;tt.classList.add('is-visible');positionTooltip(e,tt)});point.addEventListener('pointermove',e=>positionTooltip(e,tt));point.addEventListener('pointerleave',()=>tt.classList.remove('is-visible'));point.addEventListener('click',()=>{state.zoneId=zone.id;$('#zoneSelect').value=String(zone.id);setTab('planner');calculateRecommendation(false)})});
  }

  function renderModel(){
    const m=DATA.model,bench=m.benchmarks;
    $('#modelName').textContent=m.name.replace('Random Forest','Gradient-boosted');
    $('#modelKpis').innerHTML=[
      ['Duration MAE',`${m.durationMetrics.mae.toFixed(1)} min`,'chronological holdout'],
      ['Duration R²',m.durationMetrics.r2.toFixed(3),'variance explained'],
      ['Risk ROC-AUC',m.riskMetrics50.roc_auc.toFixed(3),'ranking performance'],
      ['Recall @ 0.40',pct(m.riskMetrics40.recall),'late rides caught'],
      ['Holdout rows',fmtInt.format(m.holdoutRows),m.split],
    ].map(([l,v,s])=>`<article class="metric-card"><span>${l}</span><strong>${v}</strong><small>${escapeHtml(s)}</small></article>`).join('');
    $('#pipelineDiagram').innerHTML=[
      ['01','Trip inputs','Zone, airport, flight time'],['02','Feature layer','Hour, weekday, typical distance'],['03','Duration models','Expected, p80 and p90'],['04','Risk model','Probability of unusually slow ride'],['05','Decision policy','Airport + pickup buffers'],
    ].map(x=>`<div class="pipeline-step"><span>${x[0]}</span><strong>${x[1]}</strong><small>${x[2]}</small></div>`).join('');
    renderImportance($('#durationImportance'),m.durationImportance);
    renderImportance($('#riskImportance'),m.riskImportance);
    updateThreshold();
    $('#benchmarkCards').innerHTML=`
      <div class="benchmark-card"><div><strong>Original Random Forest duration</strong><b>${bench.regression.random_forest_test_mae.toFixed(2)} min MAE</b></div><p>Project benchmark on the supplied modeling workflow.</p></div>
      <div class="benchmark-card"><div><strong>Original XGBoost duration</strong><b>${bench.regression.xgboost_test_mae.toFixed(2)} min MAE</b></div><p>Compared with a ${bench.regression.baseline_mae.toFixed(2)} minute baseline MAE.</p></div>
      <div class="benchmark-card"><div><strong>Original CatBoost risk</strong><b>${bench.classification.catboost_auc.toFixed(3)} ROC-AUC</b></div><p>At 0.40 threshold: ${pct(bench.classification.catboost_threshold_040.recall)} recall and ${pct(bench.classification.catboost_threshold_040.precision)} precision.</p></div>`;
  }

  function renderImportance(host,rows){
    const max=Math.max(...rows.map(r=>r.importance),.0001);
    host.innerHTML=rows.map(r=>`<div class="importance-row"><span>${escapeHtml(r.feature)}</span><div class="importance-track"><i style="width:${r.importance/max*100}%"></i></div><b>${pct(r.importance)}</b></div>`).join('');
  }

  function updateThreshold(){
    const slider=$('#thresholdSlider'),target=Number(slider.value)/100,m=DATA.model.thresholds.reduce((a,b)=>Math.abs(b.threshold-target)<Math.abs(a.threshold-target)?b:a,DATA.model.thresholds[0]);
    $('#thresholdValue').textContent=m.threshold.toFixed(2);
    $('#thresholdViz').innerHTML=`<div class="threshold-content"><div class="threshold-bars">${[['Precision',m.precision,'precision'],['Recall',m.recall,'recall'],['F1 score',m.f1,'f1']].map(([l,v,c])=>`<div class="threshold-stat"><span>${l}</span><div><i class="${c}" style="width:${v*100}%"></i></div><b>${pct(v)}</b></div>`).join('')}</div><div class="threshold-note"><strong>${pct(m.recall)} of late rides caught</strong>At a ${m.threshold.toFixed(2)} threshold, ${pct(m.precision)} of flagged rides are actually late. Lower thresholds catch more slow rides but create more warnings.</div></div>`;
  }

  function bindEvents(){
    $$('.tab').forEach(b=>b.addEventListener('click',()=>setTab(b.dataset.tab)));
    $$('.segment').forEach(b=>b.addEventListener('click',()=>setAirport(b.dataset.airport)));
    $('#zoneSelect').addEventListener('change',e=>{state.zoneId=Number(e.target.value);renderPlannerMap();calculateRecommendation(false)});
    ['flightDate','flightTime','flightType','passengers'].forEach(id=>$('#'+id).addEventListener('change',()=>calculateRecommendation(false)));
    $$('input[name="risk"]').forEach(r=>r.addEventListener('change',e=>{state.risk=e.target.value;calculateRecommendation(false)}));
    $('#calculateButton').addEventListener('click',()=>calculateRecommendation(true));
    $('#resetPlanner').addEventListener('click',()=>{state.zoneId=161;state.airport='JFK';state.risk='standard';populateZones();setDefaults();$$('input[name="risk"]').forEach(r=>r.checked=r.value==='standard');setAirport('JFK');calculateRecommendation(false);showToast('Planner reset')});
    $$('[data-map-mode]').forEach(b=>b.addEventListener('click',()=>{state.mapMode=b.dataset.mapMode;$$('[data-map-mode]').forEach(x=>x.classList.toggle('is-active',x===b));renderPlannerMap()}));
    $('#analyticsAirport').addEventListener('change',e=>{state.analyticsAirport=e.target.value;renderAnalytics()});
    $('#analyticsMetric').addEventListener('change',e=>{state.analyticsMetric=e.target.value;renderAnalytics()});
    $('#showAllZones').addEventListener('click',()=>{state.showZones=state.showZones===10?15:10;renderAnalytics()});
    $('#thresholdSlider').addEventListener('input',updateThreshold);
    window.addEventListener('hashchange',()=>{const t=location.hash.slice(1);if(['planner','analytics','model'].includes(t))setTab(t,false)});
  }

  function init(){
    $('#headerTripCount').textContent=fmtInt.format(DATA.meta.tripCount);
    $('#footerData').textContent=`Built from ${fmtInt.format(DATA.meta.tripCount)} supplied airport trips`;
    $('#mapNote').textContent=DATA.meta.mapNote;
    populateZones();setDefaults();bindEvents();renderPlannerMap();calculateRecommendation(false);
    const hash=location.hash.slice(1);if(['planner','analytics','model'].includes(hash))setTab(hash,false);
  }

  init();
})();
