import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Search, Download, ChevronLeft, ChevronRight, ShieldCheck, ArrowUpRight, Building2, MapPin, TrendingUp, LayoutDashboard, ListFilter, Layers3, Copy, FlaskConical, Database, MessageSquareText, Users, CircleAlert, Sun, Moon, ClipboardCopy, Inbox } from 'lucide-react';
import { Sidebar, SidebarProvider, SidebarInset, SidebarHeader, SidebarContent, SidebarFooter, SidebarMenu, SidebarMenuItem, SidebarMenuButton, SidebarTrigger } from '@/components/ui/sidebar';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table';
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import './globals.css';
import './six.css';

type Row = Record<string, any>;
const count = (n: unknown) => n == null ? 'Not available' : Number(n).toLocaleString('en-IN');
const rupees = (n: unknown) => n == null ? 'Not observed' : new Intl.NumberFormat('en-IN', {style:'currency',currency:'INR',maximumFractionDigits:2}).format(Number(n)/100);
const crore = (n: unknown) => n == null ? 'Not observed' : `₹${(Number(n)/1e9).toLocaleString('en-IN',{maximumFractionDigits:2})} cr`;
const percent = (n: unknown) => n == null ? 'Not available' : `${(Number(n)*100).toFixed(1)}%`;
const COHORT_LABEL: Record<string,string> = {lok_sabha:'Lok Sabha', rs_sitting:'Rajya Sabha (sitting)', rs_retired:'Rajya Sabha (retired)'};
const heat = (frac: number) => `hsl(${Math.round(12 + 96 * Math.max(0, 1 - frac / 0.09))} 82% ${Math.round(94 - 34 * Math.min(1, frac / 0.09))}%)`;
const normState = (s: string) => s.toLowerCase().replace(/&/g,'and').replace(/[^a-z ]/g,' ').replace(/\b(the|island|islands)\b/g,' ').replace(/\s+/g,' ').trim();
const aliasState = (n: string) => (n.includes('dadra')||n.includes('daman'))?'dadra daman':n==='orissa'?'odisha':n==='uttaranchal'?'uttarakhand':n==='pondicherry'?'puducherry':n;
const stateKey = (s: string) => aliasState(normState(s));
const signals: [string,string][] = [['','All signals'],['open_over_one_year_flag','Open beyond one year'],['no_payment_three_months_flag','No payment observed after 3 months'],['pending_recommendation_45d_flag','Pending recommendation >45 days'],['sanction_delay_45d_flag','Sanction delay proxy >45 days'],['repeat_payment_report_flag','Repeated payment-report rows'],['march_rush_flag','Year-end (March) disbursement concentration'],['high_cost_peer_flag','High historical peer amount'],['high_similarity_review_flag','Similar work descriptions'],['dbscan_outlier_flag','Unsupervised pattern outlier (DBSCAN)'],['paid_over_sanction_flag','Payments above sanction'],['completion_over_sanction_flag','Completion amount above sanction'],['completion_without_payment_flag','Completion without payment evidence'],['description_changed_flag','Description differs at completion'],['recommendation_missing_flag','Recommendation row missing']];

const NAV: [string,string,any][] = [['overview','Overview',LayoutDashboard],['ask','Ask the data',MessageSquareText],['queue','Work investigation',ListFilter],['mp','MP view',Users],['entities','Entities',Layers3],['pairs','Similar works',Copy],['validation','A/B validation',FlaskConical],['sources','Data & research',Database]];
const HEAD: Record<string,[string,string]> = {
  overview:['A national-to-local view of the works that need a closer look.','MONITOR · INVESTIGATE · REVIEW'],
  ask:['Ask plain-English questions answered locally over the connected data.','LOCAL QUERY'],
  queue:['Follow recommendations, sanctions, completion and vendor payments in one record.','CASE QUEUE'],
  mp:['Allocation, utilisation, progress and flagged works for a member.','MEMBER VIEW'],
  entities:['Full-extract profiles for MPs, authorities and vendors.','CONNECTED ENTITIES'],
  pairs:['Compare near-identical work descriptions within an authority and activity.','DUPLICATE REVIEW'],
  validation:['Equal-capacity baseline vs enhanced screening, offline.','EVALUATION'],
  sources:['Sources, feature dictionary, evidence limits and research.','PROVENANCE'],
};

async function get<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url,{signal}); const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
function useData<T>(url: string | null, revision=0) {
  const [data,setData]=useState<T|null>(null); const [error,setError]=useState('');
  useEffect(()=>{setData(null);setError('');if(!url)return;const abort=new AbortController();get<T>(url,abort.signal).then(setData).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return ()=>abort.abort()},[url,revision]);
  return {data,error};
}
function Band({b}:{b:string}) { return <span className={`band band-${String(b).toLowerCase()}`}>{b}</span>; }
function Pick({label,value,items,onChange}:{label:string,value:string,items:[string,string][],onChange:(v:string)=>void}) {
  const values=items.map(([value,label])=>({value:value||'__all',label}));
  return <div className="pick"><label>{label}</label><Select items={values} value={value||'__all'} onValueChange={v=>onChange(v==='__all'?'':String(v))}><SelectTrigger className="pick-trigger" aria-label={label}><SelectValue/></SelectTrigger><SelectContent>{values.map(v=><SelectItem key={v.value} value={v.value}>{v.label}</SelectItem>)}</SelectContent></Select></div>;
}
function Pager({offset,total,onChange}:{offset:number,total:number,onChange:(n:number)=>void}) {
  const page=Math.floor(offset/50)+1, pages=Math.max(1,Math.ceil(total/50));
  return <div className="pager"><span>{total ? `${count(offset+1)}–${count(Math.min(offset+50,total))} of ${count(total)}`:'No matching records'}</span><div style={{display:'flex',gap:10,alignItems:'center'}}><button disabled={!offset} onClick={()=>onChange(Math.max(0,offset-50))}><ChevronLeft size={16}/>Previous</button><span className="page-number">{total?`Page ${count(page)} / ${count(pages)}`:''}</span><button disabled={offset+50>=total} onClick={()=>onChange(offset+50)}>Next<ChevronRight size={16}/></button></div></div>;
}
function Skeleton({card}:{card?:boolean}) {return <div className="sk-rows" aria-hidden="true">{[0,1,2,3].map(i=><div key={i} className={`sk ${card?'sk-card':'sk-bar'}`} style={card?undefined:{width:`${92-i*13}%`}}/>)}</div>;}
function Status({error,loading,card}:{error:string,loading:boolean,card?:boolean}) {return error?<div role="alert" className="s6-empty"><CircleAlert size={24}/><span>{error}</span></div>:loading?<div role="status" aria-label="Loading local records"><Skeleton card={card}/></div>:null;}
function Empty({label}:{label:string}) {return <div className="s6-empty"><Inbox size={26}/><span>{label}</span></div>;}
function DownloadLink({file,children}:{file:string,children:React.ReactNode}) {return <a className="text-link" href={`/api/download/${file}`} download><Download size={15}/>{children}</a>;}
function Metric({label,value,note}:{label:string,value:React.ReactNode,note?:string}) {return <div className="metric"><span className="metric-label">{label}</span><strong>{value}</strong>{note&&<span>{note}</span>}</div>;}

function WorkEvidence({id,onClose,onWork,onEntity}:{id:string|null,onClose:()=>void,onWork:(id:string)=>void,onEntity:(key:string,value:string)=>void}) {
  const detail=useData<Row>(id?`/api/work/${id}`:null);
  const [paymentOffset,setPaymentOffset]=useState(0);const [revision,setRevision]=useState(0);
  const payments=useData<Row>(id?`/api/table?kind=payments&work_id=${id}&offset=${paymentOffset}`:null);
  const reviews=useData<Row>(id?'/api/reviews':null,revision);
  const [note,setNote]=useState('');const [outcome,setOutcome]=useState('Needs evidence');const [saveState,setSaveState]=useState('');const [saving,setSaving]=useState(false);
  useEffect(()=>{setPaymentOffset(0);setNote('');setOutcome('Needs evidence');setSaveState('')},[id]);
  async function save() {
    if(!detail.data)return;setSaving(true);setSaveState('');
    try {const response=await fetch('/api/reviews',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key:id,outcome,note,version:detail.data.version})});const result=await response.json();if(!response.ok)throw new Error(result.error);setSaveState('Saved on this computer.');setRevision(r=>r+1);setNote('')}catch(e){setSaveState(e instanceof Error?e.message:'Save failed')}finally{setSaving(false)}
  }
  const w=detail.data?.work;
  return <Sheet open={!!id} onOpenChange={open=>{if(!open)onClose()}}><SheetContent className="s6-sheet evidence-sheet"><SheetHeader><SheetTitle>Work {id} · Evidence</SheetTitle><SheetDescription>Source-backed observations for investigation, not a finding of misuse.</SheetDescription></SheetHeader><div className="s6-evidence"><Status error={detail.error} loading={!w}/>{w&&<>
    <h2 className="case-description">{w.description || 'Description not supplied'}</h2><p>{w.ida_name} · {w.state} · <Band b={w.priority_band}/></p><div className="s6-inline"><button onClick={()=>onEntity('mp',w.mp_key)}>MP: {w.mp_name}<ArrowUpRight size={14}/></button><button onClick={()=>onEntity('ida',w.ida_key)}>Other authority works<ArrowUpRight size={14}/></button></div>
    <div className="s6-lifecycle">{[['Recommended',w.recommendation_date,w.in_recommended?'Source 03':'Date from sanction; source 03 row absent'],['Sanctioned',w.sanction_date,'Source 04'],['Reported complete',w.completion_date,'Source 05']].map(([name,date,source])=><div key={name}><strong>{name}</strong><span>{date||'Not observed'}</span><small>{source}</small></div>)}</div>
    <h3>Financial reconciliation</h3><dl className="s6-facts">{[['Recommended',w.recommended_amount_paise],['Sanctioned',w.sanction_amount_paise],['Successful payments (reported)',w.has_successful_payment_evidence?w.successful_payment_paise:null],['In-progress payments (not settled)',w.pending_payment_paise],['Completion actual amount',w.completion_actual_paise],['One-row-per-fingerprint sensitivity',w.has_successful_payment_evidence?w.unique_fingerprint_sensitivity_paise:null],['Completion actual less observed payments',w.completion_payment_gap_paise]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{rupees(value)}</dd></div>)}</dl>
    <p className="quiet">Missing payments are not assumed to be zero in the real world. The fingerprint sensitivity retains one identical report row; it is not corrected expenditure. Completion and payment differences need invoices, taxes/retention and source-coverage checks.</p>
    <h3>Why this work is in the queue · {w.priority_score}/100</h3>{detail.data!.reasons.length?<ul className="s6-reasons">{detail.data!.reasons.map((r:Row)=><li key={r.rule}><strong>+{r.points} · {r.reason}</strong><span>{r.caution}</span></li>)}</ul>:<p>No active weighted rule. Routine does not mean verified issue-free.</p>}
    <p>Isolation-Forest atypicality percentile: <strong>{Number(w.isolation_percentile).toFixed(1)}</strong>{w.dbscan_outlier_flag?' · flagged as a DBSCAN pattern outlier':''}. These unsupervised views are separate from the rule queue and are neither fraud probability nor forecast.</p>
    <h3>Historical cost comparison</h3><dl className="s6-facts"><div><dt>Reference</dt><dd>{w.peer_level} · {count(w.peer_count)} earlier-year works</dd></div><div><dt>Peer median</dt><dd>{w.peer_median_inr==null?'Not available':rupees(w.peer_median_inr*100)}</dd></div><div><dt>Amount / peer median</dt><dd>{w.cost_peer_ratio==null?'Not available':Number(w.cost_peer_ratio).toFixed(2)+'×'}</dd></div></dl><p className="quiet">The current work and current financial year do not set the benchmark. Amount comparisons are not unit-cost estimates.</p>
    <h3>Payment evidence</h3><Status error={payments.error} loading={!payments.data}/>{payments.data&&<><Table><TableHeader><TableRow>{['Date','Vendor','Amount','Status','Identical rows'].map(h=><TableHead key={h}>{h}</TableHead>)}</TableRow></TableHeader><TableBody>{payments.data.items.map((p:Row)=><TableRow key={p.source_record}><TableCell>{p.payment_date}</TableCell><TableCell><button className="record-title" onClick={()=>onEntity('vendor',p.vendor_id)}>{p.vendor_name}</button><small className="record-meta">ID {p.vendor_id} · source record {p.source_record}</small></TableCell><TableCell className="amount-cell">{rupees(p.amount_paise)}</TableCell><TableCell>{p.payment_status}</TableCell><TableCell>{p.same_fingerprint_count}</TableCell></TableRow>)}</TableBody></Table><Pager offset={paymentOffset} total={payments.data.total} onChange={setPaymentOffset}/></>}
    <h3>Similar-work candidates</h3><p className="quiet">At most 100 connected candidates shown here. See the complete pair export for all edges.</p>{detail.data!.pairs.length?detail.data!.pairs.map((p:Row)=><button className="s6-pair-link" key={p.pair_id} onClick={()=>onWork(p.work_id_a===id?p.work_id_b:p.work_id_a)}>Work {p.work_id_a===id?p.work_id_b:p.work_id_a} · similarity {percent(p.similarity)}{p.number_conflict?' · number conflict':''}{p.continuation_cue?' · phase/extension cue':''}</button>):<p>No retained candidate. Candidate search is bounded and not exhaustive.</p>}
    <h3>Record your review</h3><Pick label="Disposition" value={outcome} onChange={setOutcome} items={['Needs evidence','Expected variation','Data issue','Substantiated issue'].map(v=>[v,v])}/><label className="s6-note-input">Evidence or next action<textarea maxLength={3000} value={note} onChange={e=>setNote(e.target.value)} placeholder="Record the document checked, finding, or evidence still needed."/></label><button disabled={saving||!note.trim()} onClick={save}>{saving?'Saving…':'Save review locally'}</button><p role="status">{saveState}</p><Status error={reviews.error} loading={!reviews.data}/>{reviews.data?.history.filter((r:Row)=>r.record_key===id).slice().reverse().map((r:Row)=><div className="s6-review" key={r.id}><strong>{r.outcome}</strong><small>{r.created}</small><p>{r.note}</p></div>)}
    <details><summary>All {Object.keys(w).length} work fields and source row references</summary><dl className="s6-facts">{Object.entries(w).map(([key,value])=><div key={key}><dt>{key}</dt><dd>{value==null?'Not available':String(value)}</dd></div>)}</dl></details>
  </>}</div></SheetContent></Sheet>;
}

function Choropleth({states,selected,onPick}:{states:Row[],selected:string,onPick:(s:string)=>void}) {
  const geo=useData<Row>('/india-states.geojson');
  const [hover,setHover]=useState<Row|null>(null);
  const byKey=new Map(states.map(s=>[stateKey(s.state),s]));
  const view=(()=>{
    const g=geo.data;if(!g)return null;
    let minx=1e9,miny=1e9,maxx=-1e9,maxy=-1e9;
    for(const f of g.features)for(const poly of f.geometry.coordinates)for(const ring of poly)for(const p of ring){if(p[0]<minx)minx=p[0];if(p[0]>maxx)maxx=p[0];if(p[1]<miny)miny=p[1];if(p[1]>maxy)maxy=p[1];}
    const W=440,sx=W/(maxx-minx),H=(maxy-miny)*sx;
    const paths=g.features.map((f:Row)=>{let d='';for(const poly of f.geometry.coordinates){for(const ring of poly){ring.forEach((p:number[],i:number)=>{d+=(i?'L':'M')+((p[0]-minx)*sx).toFixed(1)+' '+((maxy-p[1])*sx).toFixed(1);});d+='Z';}}return {geo:f.properties.state,row:byKey.get(stateKey(f.properties.state)),d};});
    return {W,H,paths};
  })();
  return <div className="panel"><div className="panel-head"><div><h2>State risk map</h2><p>Shaded by share of works in the High band. Hover for detail; click to drill. Telangana and Ladakh have no separate boundary in the base map.</p></div><MapPin size={18}/></div><div style={{padding:'0 20px 18px'}}>
    <Status error={geo.error} loading={!geo.data}/>
    {view&&<div className="s6-mapwrap"><svg viewBox={`0 0 ${view.W} ${view.H}`} className="s6-map" role="img" aria-label="India state risk choropleth">{view.paths.map((p:Row)=>{const r=p.row;const f=r?r.high/r.works:null;const on=r&&selected===r.state;const lab=r?`${r.state}: ${count(r.works)} works, ${(r.high/r.works*100).toFixed(1)}% high band`:`${p.geo}: no matching works`;return <path key={p.geo} d={p.d} fill={f==null?'#e6eaee':heat(f)} stroke={on?'#0f2233':'#9fb0be'} strokeWidth={on?1.4:0.4} style={{cursor:r?'pointer':'default'}} tabIndex={r?0:-1} role={r?'button':undefined} aria-label={lab} onFocus={()=>setHover(r||{state:p.geo,_nomatch:true})} onBlur={()=>setHover(null)} onKeyDown={e=>{if(r&&(e.key==='Enter'||e.key===' ')){e.preventDefault();onPick(selected===r.state?'':r.state);}}} onMouseEnter={()=>setHover(r||{state:p.geo,_nomatch:true})} onMouseLeave={()=>setHover(null)} onClick={()=>r&&onPick(selected===r.state?'':r.state)}/>;})}</svg>
      <div className="s6-maplegend"><span>Lower</span><i style={{background:heat(0)}}/><i style={{background:heat(0.03)}}/><i style={{background:heat(0.05)}}/><i style={{background:heat(0.07)}}/><i style={{background:heat(0.09)}}/><span>Higher High-band share</span></div>
      {hover&&<div className="s6-maptip">{hover._nomatch?<><strong>{hover.state}</strong><span>No matching works in this extract</span></>:<><strong>{hover.state}</strong><span>{count(hover.works)} works · {count(hover.high)} High ({(hover.high/hover.works*100).toFixed(1)}%)</span><span>{crore(hover.sanction_paise)} sanctioned</span></>}</div>}</div>}
  </div></div>;
}

function Overview({inspect}:{inspect:(key:string,value:string)=>void}) {
  const [state,setState]=useState('');
  const data=useData<Row>('/api/overview'+(state?`?state=${encodeURIComponent(state)}`:''));
  const months=useData<Row>('/api/months');
  const n=data.data?.national;const d=data.data;
  const settledFrac=(r:Row)=>r.sanction_paise>0?r.successful_payment_paise/r.sanction_paise:null;
  const topStates=(d?.states||[]).slice(0,10).map((s:Row)=>({name:s.state.length>12?s.state.slice(0,11)+'…':s.state,High:s.high}));
  const trend=(months.data?.items||[]).map((m:Row)=>({month:m.payment_month,Settled:Math.round(m.successful_payment_paise/1e7)/100}));
  const idas=state?d?.idas:d?.top_idas;
  return <><Status error={data.error} loading={!n} card/>{n&&<>
    <div className="metric-grid">
      <Metric label="Connected works" value={count(n.works)}/>
      <Metric label="High-priority reviews" value={count(n.high)}/>
      <Metric label="Sanctioned" value={crore(n.sanction_paise)}/>
      <Metric label="Settled / sanctioned" value={percent(settledFrac(n))} note={`${crore(n.successful_payment_paise)} settled`}/>
      <Metric label="Open beyond one year" value={count(n.open_over_year)}/>
      <Metric label="No payment after 3 months" value={count(n.no_payment_3m)}/>
      <Metric label="Members with works" value={count(n.mp_count)}/>
      <Metric label="District authorities" value={count(n.ida_count)}/>
    </div>

    <div className="metric-grid" style={{gridTemplateColumns:'repeat(3,minmax(0,1fr))'}}>{(d!.cohorts||[]).map((c:Row)=><div key={c.cohort} className="metric"><span className="metric-label">{COHORT_LABEL[c.cohort]||c.cohort}</span><strong style={{fontSize:26}}>{count(c.works)}</strong><span>{count(c.high)} High · {crore(c.sanction_paise)} sanctioned · {percent(settledFrac(c))} settled</span></div>)}</div>

    <div className="overview-grid">
      <div className="panel"><div className="panel-head"><div><h2>Top states by high-priority works</h2></div><TrendingUp size={18}/></div><div style={{padding:'6px 16px 18px'}}><ResponsiveContainer width="100%" height={230}><BarChart data={topStates} margin={{top:4,right:8,bottom:4,left:0}}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="name" tick={{fontSize:11}} interval={0} angle={-30} textAnchor="end" height={56}/><YAxis tick={{fontSize:11}} allowDecimals={false}/><Tooltip/><Bar dataKey="High" fill="#c96263" radius={[3,3,0,0]}/></BarChart></ResponsiveContainer></div></div>
      <div className="panel"><div className="panel-head"><div><h2>Monthly settled payments (₹ cr)</h2></div><TrendingUp size={18}/></div><div style={{padding:'6px 16px 18px'}}><ResponsiveContainer width="100%" height={230}><LineChart data={trend} margin={{top:4,right:8,bottom:4,left:0}}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="month" tick={{fontSize:10}} interval={Math.ceil(trend.length/8)}/><YAxis tick={{fontSize:11}}/><Tooltip/><Line dataKey="Settled" stroke="#2f7f91" dot={false} strokeWidth={2}/></LineChart></ResponsiveContainer></div></div>
    </div>

    <Choropleth states={d!.states} selected={state} onPick={setState}/>

    <div className="panel"><div className="panel-head"><div><h2>State risk heatmap</h2><p>Cell shade = share of works in the High band. Select a state for its authorities; “Investigate” opens the filtered queue.</p></div></div>
      <div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{['State / UT','Works','High','High %','Open >1yr','Sanctioned','Settled/sanction','Mean priority',''].map(h=><TableHead key={h}>{h}</TableHead>)}</TableRow></TableHeader><TableBody>{d!.states.map((s:Row)=>{const f=s.high/s.works;return <TableRow key={s.state}><TableCell><button className="record-title" onClick={()=>setState(state===s.state?'':s.state)}>{s.state}</button></TableCell><TableCell>{count(s.works)}</TableCell><TableCell>{count(s.high)}</TableCell><TableCell><span className="s6-heatcell" style={{background:heat(f)}}>{(f*100).toFixed(1)}%</span></TableCell><TableCell>{count(s.open_over_year)}</TableCell><TableCell className="amount-cell">{crore(s.sanction_paise)}</TableCell><TableCell>{percent(settledFrac(s))}</TableCell><TableCell>{Number(s.mean_priority).toFixed(1)}</TableCell><TableCell><button onClick={()=>inspect('state',s.state)}>Investigate<ArrowUpRight size={13}/></button></TableCell></TableRow>})}</TableBody></Table></div></div>

    <div className="panel"><div className="panel-head"><div><h2>{state?`District authorities · ${state}`:'Highest-risk district authorities (national top 20)'}</h2></div><Building2 size={18}/></div>{state&&<p className="section-note"><button className="text-link" onClick={()=>setState('')}>Back to national top 20</button></p>}<div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{['Authority','State','Works','High','Open >1yr','Sanctioned','Settled','Investigate'].map(h=><TableHead key={h}>{h}</TableHead>)}</TableRow></TableHeader><TableBody>{(idas||[]).map((r:Row)=><TableRow key={r.ida_key}><TableCell className="record-title">{r.ida_name}</TableCell><TableCell>{r.state}</TableCell><TableCell>{count(r.works)}</TableCell><TableCell>{count(r.high)}</TableCell><TableCell>{count(r.open_over_year)}</TableCell><TableCell className="amount-cell">{crore(r.sanction_paise)}</TableCell><TableCell className="amount-cell">{crore(r.successful_payment_paise)}</TableCell><TableCell><button onClick={()=>inspect('ida',r.ida_key)}>Works<ArrowUpRight size={13}/></button></TableCell></TableRow>)}</TableBody></Table></div></div>
    </>}</>;
}

function Ask({inspect}:{inspect:(key:string,value:string)=>void}) {
  const [draft,setDraft]=useState('');const [query,setQuery]=useState('');
  const data=useData<Row>('/api/ask'+(query?`?q=${encodeURIComponent(query)}`:''));
  const examples:string[]=data.data?.examples||[];
  const answered=!!(data.data?.columns?.length);
  const clarify=!!query&&!!data.data&&!answered?data.data.summary:'';
  const cell=(kind:string,v:unknown)=>kind==='money'?crore(v):kind==='pct'?percent(v):kind==='num'?(v==null?'—':Number(v).toFixed(1)):kind==='count'?count(v):(v==null?'—':String(v));
  return <>
    <form className="s6-ask" onSubmit={e=>{e.preventDefault();setQuery(draft.trim())}}><Search size={18}/><input value={draft} onChange={e=>setDraft(e.target.value)} placeholder="e.g. Which districts in Bihar have the most delays?"/><button type="submit" disabled={!draft.trim()}>Ask</button></form>
    <div className="s6-chips">{examples.map(x=><button key={x} className="s6-chip" onClick={()=>{setDraft(x);setQuery(x)}}>{x}</button>)}</div>
    <Status error={data.error} loading={!!query&&!data.data}/>
    {answered&&<div className="panel"><div className="panel-head"><div><h2>{data.data!.summary}</h2><p>Interpreted as: {data.data!.interpretation}</p></div></div>
      <div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{data.data!.columns.map((c:Row)=><TableHead key={c.key}>{c.label}</TableHead>)}</TableRow></TableHeader><TableBody>{data.data!.rows.map((r:Row,i:number)=><TableRow key={i}>{data.data!.columns.map((c:Row)=><TableCell key={c.key} className={c.kind==='money'||c.kind==='count'?'amount-cell':''}>{c.key==='_dim'?<button className="record-title" onClick={()=>{if(data.data!.interpretation.toLowerCase().startsWith('state'))inspect('state',String(r._dim))}}>{cell(c.kind,r[c.key])}</button>:cell(c.kind,r[c.key])}</TableCell>)}</TableRow>)}</TableBody></Table></div>
      <p className="section-note">{data.data!.caveat}</p>
      <details style={{padding:'0 24px 22px'}}><summary>Generated SQL ({data.data!.row_count} rows)<button className="copy-btn" onClick={e=>{e.preventDefault();try{navigator.clipboard?.writeText(data.data!.sql);}catch{}}}><ClipboardCopy size={13}/>Copy</button></summary><pre className="s6-sql">{data.data!.sql}{data.data!.params.length?`\n-- parameters: ${data.data!.params.join(', ')}`:''}</pre></details></div>}
    {!!clarify&&<div className="panel"><div className="panel-head"><div><h2>Couldn't answer that directly</h2><p>{clarify}</p></div></div><p className="section-note">{data.data!.caveat}</p></div>}
  </>;
}

function MPView({open}:{open:(id:string)=>void}) {
  const [query,setQuery]=useState('');const [search,setSearch]=useState('');const [mp,setMp]=useState<Row|null>(null);
  useEffect(()=>{const t=setTimeout(()=>setSearch(query),300);return()=>clearTimeout(t)},[query]);
  const list=useData<Row>(mp?null:'/api/table?'+new URLSearchParams({kind:'mps',q:search}));
  const works=useData<Row>(mp?`/api/works?mp=${encodeURIComponent(mp.mp_key)}&sort=priority_score&order=desc`:null);
  const light=(m:Row)=>{const f=m.work_count?m.high_priority_count/m.work_count:0;return f>=0.06?['#c96263','High attention']:f>=0.03?['#d5a64c','Some attention']:['#388e8a','Mostly routine'];};
  if(!mp){
    return <div className="panel"><div className="queue-controls"><div className="search-box"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search member by name"/></div></div>
      <Status error={list.error} loading={!list.data}/>{list.data&&<div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{['Member','State','Works','High-priority','Settled / allocation'].map(h=><TableHead key={h}>{h}</TableHead>)}</TableRow></TableHeader><TableBody>{list.data.items.map((m:Row)=><TableRow key={m.mp_key}><TableCell><button className="record-title" onClick={()=>setMp(m)}>{m.mp_name}<ArrowUpRight size={14}/></button></TableCell><TableCell>{m.state}</TableCell><TableCell>{count(m.work_count)}</TableCell><TableCell>{count(m.high_priority_count)}</TableCell><TableCell>{percent(m.observed_paid_to_allocation_ratio)}</TableCell></TableRow>)}</TableBody></Table></div>}</div>;
  }
  const [colour,label]=light(mp);
  return <><div className="page-heading" style={{marginTop:-8}}><div><p className="eyebrow" style={{color:colour}}>● {label}</p><h1 style={{fontSize:26}}>{mp.mp_name}</h1><p className="page-description">{mp.constituency?mp.constituency+' · ':''}{mp.state} — {count(mp.high_priority_count)} of {count(mp.work_count)} works in the High band</p></div><button onClick={()=>{setMp(null);setQuery('')}}><ChevronLeft size={16}/>Back to search</button></div>
    <div className="metric-grid">
      <Metric label="Allocated (limit snapshot)" value={crore(mp.allocated_paise)}/>
      <Metric label="Sanctioned" value={crore(mp.sanction_paise)}/>
      <Metric label="Settled (reported)" value={crore(mp.successful_payment_paise)}/>
      <Metric label="Settled / allocation" value={percent(mp.observed_paid_to_allocation_ratio)}/>
      <Metric label="Sanction / allocation" value={percent(mp.sanction_to_allocation_ratio)}/>
      <Metric label="Calamity consent" value={crore(mp.consented_paise)}/>
    </div>
    <div className="overview-grid">
      <div className="panel"><div className="panel-head"><div><h2>Work progress</h2></div></div><dl className="s6-facts" style={{padding:'4px 24px 20px'}}>{[['Recommended records',count(mp.recommended_record_count)],['Sanctioned',count(mp.sanctioned_count)],['Reported complete (export)',count(mp.completed_count)],['Reported completion / sanction',percent(mp.completion_to_sanction_ratio)],['Open beyond one year',count(mp.open_over_one_year_count)],['No payment after 3 months',count(mp.no_payment_three_months_count)]].map(([l,v])=><div key={l}><dt>{l}</dt><dd>{v}</dd></div>)}</dl></div>
      <div className="panel"><div className="panel-head"><div><h2>Compliance checks</h2></div></div><dl className="s6-facts" style={{padding:'4px 24px 8px'}}>{[['SC-area allocation (15% mandate)'],['ST-area allocation (7.5% mandate)'],['Trust/society ₹75L ceiling'],['Jurisdiction of recommendation']].map(([l])=><div key={l}><dt>{l}</dt><dd>Unavailable</dd></div>)}</dl><p className="section-note">These mandates need beneficiary-area tags, a trust register and geocoding not in the supplied exports. They are shown as <strong>unavailable, not passed</strong>.</p></div>
    </div>
    <div className="panel"><div className="panel-head"><div><h2>Flagged and recent works</h2></div></div><Status error={works.error} loading={!works.data}/>{works.data&&<><div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{['Work / purpose','Lifecycle','Sanctioned','Settled','Review priority'].map(h=><TableHead key={h}>{h}</TableHead>)}</TableRow></TableHeader><TableBody>{works.data.items.map((w:Row)=><TableRow key={w.work_id}><TableCell className="work-cell"><button className="record-title" onClick={()=>open(w.work_id)}>{w.description||'No description supplied'}</button><small className="record-meta">#{w.work_id}</small></TableCell><TableCell>{w.lifecycle}<small className="record-meta">{w.sanction_date||'No observed sanction'}</small></TableCell><TableCell className="amount-cell">{rupees(w.sanction_amount_paise)}</TableCell><TableCell className="amount-cell">{rupees(w.successful_payment_paise)}</TableCell><TableCell><Band b={w.priority_band}/> <span className="quiet">{w.priority_score}</span></TableCell></TableRow>)}</TableBody></Table></div><p className="section-note">Highest priority first ({works.data.items.length} of {count(works.data.summary.total)}). Open a work for its evidence trail.</p></>}</div></>;
}

function Queue({open,entity,clearEntity}:{open:(id:string)=>void,entity:Row,clearEntity:()=>void}) {
  const options=useData<Row>('/api/options');const [state,setState]=useState('');const [year,setYear]=useState('');const [lifecycle,setLifecycle]=useState('');const [signal,setSignal]=useState('');const [query,setQuery]=useState('');const [search,setSearch]=useState('');const [offset,setOffset]=useState(0);const [sort,setSort]=useState('priority_score');
  useEffect(()=>{const t=setTimeout(()=>setSearch(query),300);return()=>clearTimeout(t)},[query]);
  useEffect(()=>setOffset(0),[state,year,lifecycle,signal,search,sort,entity]);
  const args=new URLSearchParams({state,fy:year,lifecycle,signal,q:search,sort,offset:String(offset),...entity});const works=useData<Row>('/api/works?'+args);
  const summary=works.data?.summary;
  return <div className="panel">
    <div className="queue-controls"><div className="search-box"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Work ID, description, MP or authority"/></div><Pick label="State / UT" value={state} onChange={setState} items={[['','All states'],...(options.data?.states||[]).map((v:string)=>[v,v])]}/><Pick label="Sanction FY" value={year} onChange={setYear} items={[['','All years'],...(options.data?.years||[]).map((v:string)=>[v,v])]}/><Pick label="Lifecycle" value={lifecycle} onChange={setLifecycle} items={[['','All lifecycles'],...['Not in sanction export','Sanctioned / open','Reported complete'].map(v=>[v,v] as [string,string])]}/><Pick label="Signal" value={signal} onChange={setSignal} items={signals}/><Pick label="Sort" value={sort} onChange={setSort} items={[['priority_score','Rule priority'],['isolation_percentile','Model atypicality'],['sanction_amount_paise','Sanction amount'],['successful_payment_paise','Successful payments'],['sanction_age_days','Sanction age']]}/><DownloadLink file="Work_Features.csv">Dataset</DownloadLink></div>
    {!!Object.keys(entity).length&&<div className="selection-summary">Connected-entity filter: {Object.keys(entity).join(', ')} <button onClick={clearEntity}>Clear</button></div>}
    <Status error={works.error||options.error} loading={!works.data}/>{summary&&<>
    <div className="selection-summary"><strong>{count(summary.total)}</strong> matching · {count(summary.completions)} complete · {crore(summary.sanction_paise)} sanctioned · {crore(summary.successful_payment_paise)} settled · {count(summary.open_over_year)} open &gt;1yr · {count(summary.no_payment_three_months)} no payment 3mo</div>
    <div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{['Work / purpose','MP / authority','Lifecycle','Sanctioned','Settled','Review priority'].map(h=><TableHead key={h}>{h}</TableHead>)}</TableRow></TableHeader><TableBody>{works.data!.items.map((w:Row)=><TableRow key={w.work_id}><TableCell className="work-cell"><button className="record-title" onClick={()=>open(w.work_id)}>{w.description||'No description supplied'}</button><small className="record-meta">#{w.work_id} · {w.activity_type}</small></TableCell><TableCell>{w.mp_name}<small className="record-meta">{w.ida_name} · {w.state}</small></TableCell><TableCell>{w.lifecycle}<small className="record-meta">{w.sanction_date||'No observed sanction'}</small></TableCell><TableCell className="amount-cell">{rupees(w.sanction_amount_paise)}</TableCell><TableCell className="amount-cell">{rupees(w.successful_payment_paise)}</TableCell><TableCell><div className="score-line"><Band b={w.priority_band}/><strong>{w.priority_score}</strong></div><small className="record-meta">Model pct {Number(w.isolation_percentile).toFixed(0)} · {w.data_quality_issue_count} DQ</small></TableCell></TableRow>)}</TableBody></Table></div><Pager offset={offset} total={summary.total} onChange={setOffset}/></>}
  </div>;
}

function Entities({inspect}:{inspect:(key:string,value:string)=>void}) {
  const [kind,setKind]=useState('mps');const [query,setQuery]=useState('');const [offset,setOffset]=useState(0);const [focus,setFocus]=useState<Row|null>(null);
  const data=useData<Row>('/api/table?'+new URLSearchParams({kind,q:query,offset:String(offset)}));
  useEffect(()=>{setOffset(0);setFocus(null)},[kind,query]);
  return <div className="panel"><div className="queue-controls"><Pick label="Entity" value={kind} onChange={setKind} items={[["mps","Members of Parliament"],["idas","District authorities"],["vendors","Vendors"]]}/><div className="search-box"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search name"/></div><DownloadLink file={kind==='mps'?'MP_Features.csv':kind==='idas'?'IDA_Features.csv':'Vendor_Features.csv'}>Dataset</DownloadLink></div><Status error={data.error} loading={!data.data}/>{data.data&&<><div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{['Entity','Connected works','Successful payments','Pending payments','Details'].map(v=><TableHead key={v}>{v}</TableHead>)}</TableRow></TableHeader><TableBody>{data.data.items.map((r:Row)=>{const key=r.mp_key||r.ida_key||r.vendor_id;return <TableRow key={key}><TableCell className="record-title">{r.mp_name||r.ida_name||r.vendor_name}<small className="record-meta">{r.state||`Vendor ID ${r.vendor_id}`}</small></TableCell><TableCell>{count(r.work_count)}</TableCell><TableCell className="amount-cell">{rupees(r.successful_payment_paise)}</TableCell><TableCell className="amount-cell">{rupees(r.pending_payment_paise)}</TableCell><TableCell><button onClick={()=>setFocus(r)}>Profile</button> <button onClick={()=>inspect(kind==='mps'?'mp':kind==='idas'?'ida':'vendor',key)}>Works</button></TableCell></TableRow>})}</TableBody></Table></div><Pager offset={offset} total={data.data.total} onChange={setOffset}/></>}{focus&&<div style={{padding:24,borderTop:'1px solid #edf1f5'}}><h2 style={{margin:'0 0 6px'}}>{focus.mp_name||focus.ida_name||focus.vendor_name}</h2><p className="quiet">Allocation ratios use the supplied limit snapshot, not a certified bank balance. Shared vendor names do not mean the same legal entity. Concentration is descriptive, not evidence of collusion.</p><dl className="s6-facts">{Object.entries(focus).filter(([k])=>k.toLowerCase()===k).map(([k,v])=><div key={k}><dt>{k.replaceAll('_',' ')}</dt><dd>{k.endsWith('_paise')?rupees(v):k.endsWith('_ratio')?percent(v):v==null?'Not observed':String(v)}</dd></div>)}</dl></div>}</div>;
}

function Pairs({open}:{open:(id:string)=>void}) {
  const [offset,setOffset]=useState(0);const data=useData<Row>(`/api/duplicates?offset=${offset}`);
  return <div className="panel"><div className="panel-head"><div><h2>Similar-work candidates</h2><p>Compare both records. Matching descriptions do not establish duplicate assets.</p></div><DownloadLink file="Duplicate_Candidates.csv">All pairs</DownloadLink></div><Status error={data.error} loading={!data.data}/>{data.data&&<><div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{['First work','Second work','Similarity','Cautions'].map(h=><TableHead key={h}>{h}</TableHead>)}</TableRow></TableHeader><TableBody>{data.data.items.map((p:Row)=><TableRow key={p.pair_id}><TableCell className="work-cell"><button className="record-title" onClick={()=>open(p.work_id_a)}>{p.description_a}</button><small className="record-meta">#{p.work_id_a} · {rupees(p.amount_a)}</small></TableCell><TableCell className="work-cell"><button className="record-title" onClick={()=>open(p.work_id_b)}>{p.description_b}</button><small className="record-meta">#{p.work_id_b} · {rupees(p.amount_b)}</small></TableCell><TableCell><strong>{percent(p.similarity)}</strong></TableCell><TableCell className="quiet">{[p.number_conflict?'Different number tokens':'',p.continuation_cue?'Phase/repair cue':'',p.generic_text?'Generic text':''].filter(Boolean).join(' · ')||'Location and scope still need verification'}</TableCell></TableRow>)}</TableBody></Table></div><Pager offset={offset} total={data.data.total} onChange={setOffset}/></>}<p className="section-note">Bounded same-authority/activity matching; cross-authority pairs and matches outside candidate windows may be missed. No measured real duplicate recall.</p></div>;
}

function Validation() {
  const data=useData<Row>('/api/validation');const [budget,setBudget]=useState('0.2');
  const result=data.data?.budgets.find((r:Row)=>String(r.fraction)===budget);
  return <><Status error={data.error} loading={!data.data}/>{data.data&&<><p className="coverage-strip"><FlaskConical size={16}/><span>{data.data.design}</span></p><div className="global-filters"><Pick label="Review capacity" value={budget} onChange={setBudget} items={['0.05','0.1','0.2','0.3'].map(v=>[v,percent(v)])}/></div>{result&&<>
    <div className="metric-grid"><Metric label="Baseline A recovery" value={percent(result.a_recovery)}/><Metric label="Enhanced B recovery" value={percent(result.b_recovery)}/><Metric label="Difference" value={`${(result.difference*100).toFixed(1)} pp`}/><Metric label="Paired 95% interval" value={`${(result.ci95[0]*100).toFixed(1)} to ${(result.ci95[1]*100).toFixed(1)} pp`}/></div>
    <div className="panel"><div className="panel-head"><div><h2>Per-family recovery</h2><p>A vs B selection across {result.scenarios[0]?.assigned} synthetic contexts at this budget.</p></div></div><div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{['Injected scenario','Assigned','A recovered','B recovered'].map(v=><TableHead key={v}>{v}</TableHead>)}</TableRow></TableHeader><TableBody>{result.scenarios.map((r:Row)=><TableRow key={r.scenario}><TableCell className="record-title">{r.scenario}</TableCell><TableCell>{r.assigned}</TableCell><TableCell>{r.a_selected}</TableCell><TableCell>{r.b_selected}</TableCell></TableRow>)}</TableBody></Table></div><p className="section-note">Actual held-out queue overlap: {percent(result.actual_queue_overlap)}. Overlap describes different selections, not correctness.</p></div></>}<div className="global-filters"><DownloadLink file="AB_Report.md">Methods & results</DownloadLink><DownloadLink file="ab_actual_scores.csv">Synthetic scored cases</DownloadLink><DownloadLink file="ab_controlled_benchmark.csv">Controlled benchmark</DownloadLink></div><ul className="quiet" style={{paddingLeft:20}}>{data.data.limitations.map((v:string)=><li key={v} style={{margin:'7px 0'}}>{v}</li>)}</ul></>}</>;
}

function Sources({meta}:{meta:Row}) {
  const [query,setQuery]=useState('');const [offset,setOffset]=useState(0);const dictionary=useData<Row>('/api/table?'+new URLSearchParams({kind:'dictionary',q:query,offset:String(offset)}));
  useEffect(()=>setOffset(0),[query]);
  return <><div className="panel"><div className="panel-head"><div><h2>Source coverage</h2><p>{meta.scope}. Assessment date {meta.as_of}; source extraction timestamps were not supplied.</p></div></div><div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{['Source','Original records','Accepted','Quarantined'].map(v=><TableHead key={v}>{v}</TableHead>)}</TableRow></TableHeader><TableBody>{meta.sources.map((r:Row,i:number)=><TableRow key={i}><TableCell className="record-title">{r.file}</TableCell><TableCell>{count(r.rows)}</TableCell><TableCell>{count(r.accepted_rows)}</TableCell><TableCell>{r.quarantined_rows}</TableCell></TableRow>)}</TableBody></Table></div><p className="section-note">One expenditure record is truncated. Repeated payment fingerprints remain in reported sums. Missing documents or payments do not establish ghost assets, misuse or unpaid liabilities.</p><p className="section-note"><DownloadLink file="MPLADS_Review.xlsx">Excel review workbook</DownloadLink> &nbsp; <DownloadLink file="audit.json">Audit & source hashes</DownloadLink> &nbsp; <DownloadLink file="Quarantine.csv">Quarantined record</DownloadLink></p></div>
    <div className="panel"><div className="panel-head"><div><h2>Evidence limits & research</h2></div></div><ul className="quiet" style={{padding:'0 24px 8px 44px'}}>{meta.limits.map((v:string)=><li key={v} style={{margin:'7px 0'}}>{v}</li>)}</ul><div style={{padding:'0 24px 20px'}}>{meta.research.map((r:Row)=><p key={r.id} className="quiet" style={{margin:'10px 0'}}><a className="text-link" href={r.url} target="_blank" rel="noreferrer">{r.title}</a> · {r.date}<br/>{r.use}</p>)}</div></div>
    <div className="panel"><div className="panel-head"><div><h2>Feature dictionary</h2></div><input className="dictionary-search s6-input" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search a field"/></div><Status error={dictionary.error} loading={!dictionary.data}/>{dictionary.data&&<><div style={{overflowX:'auto'}}><Table><TableHeader><TableRow>{['Table / field','Definition','Unit / availability'].map(v=><TableHead key={v}>{v}</TableHead>)}</TableRow></TableHeader><TableBody>{dictionary.data.items.map((r:Row)=><TableRow key={r.table+r.field}><TableCell className="record-title">{r.table}<small className="record-meta">{r.field}</small></TableCell><TableCell>{r.definition}</TableCell><TableCell>{r.unit}<small className="record-meta">{r.availability}</small></TableCell></TableRow>)}</TableBody></Table></div><Pager total={dictionary.data.total} offset={offset} onChange={setOffset}/></>}</div>
  </>;
}

function App() {
  const meta=useData<Row>('/api/meta');const [view,setView]=useState('overview');const [selected,setSelected]=useState<string|null>(null);const [entity,setEntity]=useState<Row>({});
  const [theme,setTheme]=useState<'light'|'dark'>(()=>{try{return (localStorage.getItem('mplads-theme') as 'light'|'dark')||'light'}catch{return 'light'}});
  useEffect(()=>{try{document.documentElement.dataset.theme=theme;localStorage.setItem('mplads-theme',theme)}catch{}},[theme]);
  function inspect(key:string,value:string){setEntity({[key]:value});setSelected(null);setView('queue')}
  const cohorts=(meta.data?.cohorts||[]).map((c:string)=>COHORT_LABEL[c]||c).join(' · ');
  const [desc,eyebrow]=HEAD[view];
  const label=NAV.find(n=>n[0]===view)?.[1]||'';
  return <SidebarProvider style={{'--sidebar-width':'15.5rem'} as React.CSSProperties}>
    <Sidebar className="app-sidebar">
      <SidebarHeader className="brand"><div className="brand-symbol"><ShieldCheck size={25}/></div><div><strong>MPLADS<span>GUARD</span></strong><small>Investigation workspace</small></div></SidebarHeader>
      <SidebarContent><p className="nav-caption">WORKSPACE</p><SidebarMenu>{NAV.map(([key,label,Icon])=><SidebarMenuItem key={key}><SidebarMenuButton isActive={view===key} onClick={()=>setView(key)} className="nav-item"><Icon size={19}/><span>{label}</span></SidebarMenuButton></SidebarMenuItem>)}</SidebarMenu></SidebarContent>
      <SidebarFooter><div className="sidebar-source"><span className="connection-dot"/>Local source connected<small>{cohorts||'MPLADS'}</small>{meta.data&&<small>{count(meta.data.totals.works)} works · as of {meta.data.as_of}</small>}</div><div className="sidebar-foot">PS 26102 <span>Local</span></div></SidebarFooter>
    </Sidebar>
    <SidebarInset className="app-main">
      <header className="topbar"><div><SidebarTrigger/><span className="crumb">MPLADS / <strong>{label}</strong></span></div><div style={{display:'flex',gap:12,alignItems:'center'}}><span className="environment-pill"><span/>Local processing · review signals, not findings of fraud</span><button className="theme-toggle" onClick={()=>setTheme(t=>t==='dark'?'light':'dark')} aria-label={`Switch to ${theme==='dark'?'light':'dark'} mode`}>{theme==='dark'?<Sun size={15}/>:<Moon size={15}/>}<span>{theme==='dark'?'Light':'Dark'}</span></button></div></header>
      <main className="main-content">
        <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{label}</h1><p className="page-description">{desc}</p></div>{view==='overview'&&meta.data&&<DownloadLink file="audit.json">National audit</DownloadLink>}</div>
        <Status error={meta.error} loading={!meta.data}/>{meta.data&&<>
          {view==='overview'&&<Overview inspect={inspect}/>}
          {view==='ask'&&<Ask inspect={inspect}/>}
          {view==='queue'&&<Queue open={setSelected} entity={entity} clearEntity={()=>setEntity({})}/>}
          {view==='mp'&&<MPView open={setSelected}/>}
          {view==='entities'&&<Entities inspect={inspect}/>}
          {view==='pairs'&&<Pairs open={setSelected}/>}
          {view==='validation'&&<Validation/>}
          {view==='sources'&&<Sources meta={meta.data}/>}
        </>}
        <footer className="workspace-footer"><div>Local research prototype · no officer authentication or audit certification.</div><a className="text-link" href="/api/reviews" target="_blank" rel="noreferrer">Export local review history</a></footer>
      </main>
      <WorkEvidence id={selected} onClose={()=>setSelected(null)} onWork={setSelected} onEntity={inspect}/>
    </SidebarInset>
  </SidebarProvider>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
