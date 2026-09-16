import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const here=path.dirname(fileURLToPath(import.meta.url)), root=path.resolve(here,'../..');
const input=path.join(root,'evaluation_18/local/run_v1'), output=path.join(root,'outputs/ps26102-ab-20260910'), previews=path.join(here,'previews');
await fs.mkdir(output,{recursive:true});await fs.mkdir(previews,{recursive:true});
const data=JSON.parse(await fs.readFile(path.join(input,'metrics.json'),'utf8'));
const reproducibility=JSON.parse(await fs.readFile(path.join(root,'evaluation_18/local/repro_verification.json'),'utf8'));
if(!reproducibility.passed)throw Error('Rebuild verification failed');
async function csv(name){
  const lines=(await fs.readFile(path.join(input,name+'.csv'),'utf8')).trim().split(/\r?\n/),headers=lines.shift().split(',');
  return lines.map(line=>{const cells=line.split(',');if(cells.length!==headers.length||line.includes('"'))throw Error('Aggregate CSV requires a quoted-field parser');return Object.fromEntries(headers.map((h,i)=>[h,cells[i]!==''&&Number.isFinite(Number(cells[i]))?Number(cells[i]):cells[i]]));});
}
const families=(await csv('Controlled_Families')).filter(x=>x.budget===.1),mix=(await csv('Real_Cohort_Mix')).filter(x=>x.budget===.1);
const wb=Workbook.create(),checks=[];
const font='Arial'; // Available as arial.ttf in Windows Fonts; reviewed in rendered output.
function sheet(name,title,note){const s=wb.worksheets.add(name);s.showGridLines=false;s.getRange('A2').values=[[title]];s.getRange('A2').format.font={name:font,size:14,bold:true,color:'#222222'};s.getRange('A3').values=[[note]];s.getRange('A3').format.font={name:font,size:10,color:'#555555'};return s;}
function table(s,start,headers,rows,widths){
  const r=s.getRangeByIndexes(start-1,0,rows.length+1,headers.length);r.values=[headers,...rows];r.format.font={name:font,size:10,color:'#222222'};r.format.rowHeight=24;r.format.verticalAlignment='center';
  const h=s.getRangeByIndexes(start-1,0,1,headers.length);h.format.fill='#E6E6E6';h.format.font={name:font,size:10,bold:true,color:'#222222'};h.format.wrapText=true;h.format.rowHeight=38;h.format.horizontalAlignment='center';
  widths.forEach((w,i)=>s.getRangeByIndexes(start-1,i,rows.length+1,1).format.columnWidth=w);
  for(let i=0;i<headers.length;i++){const body=s.getRangeByIndexes(start,i,rows.length,1);if(rows.some(row=>typeof row[i]==='number')){body.setNumberFormat('#,##0');body.format.horizontalAlignment='right';}else body.format.wrapText=true;}
  return s;
}
function note(s,row,text){s.getRange('A'+row).values=[[text]];s.getRange('A'+row).format.font={name:font,size:10,color:'#555555'};}
const primary=Object.fromEntries(data.controlled.metrics.filter(r=>r.budget===.1).map(r=>[r.arm,r]));
const interval=data.controlled.recovery_difference_95_interval;
const diffSeeds=data.controlled.tie_sensitivity.map(r=>r.recovery_difference);
const summary=sheet('Summary','MPLADS A/B comparison','PS 26102. 10 September 2026. Offline controlled test and retrospective real-data queues.');
table(summary,5,['Primary measure','Baseline A','Enhanced B','Interpretation'],[
  ['Cases reviewed',primary.A.reviewed,primary.B.reviewed,'Same 10% budget from 7,200 constructed test cases.'],
  ['Constructed positives recovered',primary.A.true_positive,primary.B.true_positive,'Nine additional positive cases in B under the main tie seed.'],
  ['Constructed normal cases selected',primary.A.false_positive,primary.B.false_positive,'These are controls with known synthetic truth, not real allegations.'],
  ['Constructed positives available',primary.A.positives,primary.B.positives,'50% constructed prevalence; not estimated national prevalence.'],
  ['Recovery rate',null,null,'Selected constructed positives / all constructed positives.'],
  ['Yield per review',null,null,'Selected constructed positives / reviewed cases.'],
], [37,18,18,79]);
summary.getRange('B10:C10').formulas=[['=B7/B9','=C7/C9']];summary.getRange('B11:C11').formulas=[['=B7/B6','=C7/C6']];summary.getRange('B10:C11').setNumberFormat('0.00%');summary.getRange('D6:D11').format.rowHeight=32;
table(summary,14,['Sensitivity measure','Value','Unit','Interpretation'],[
  ['B minus A recovery',null,'percentage points','Small improvement conditional on the main tie seed.'],
  ['Paired 95% interval, lower',interval[0]*100,'percentage points','1,000 resamples of whole synthetic contexts; fixed main tie seed.'],
  ['Paired 95% interval, upper',interval[1]*100,'percentage points','The interval does not measure real-world fraud detection.'],
  ['Alternative tie seeds: B wins',diffSeeds.filter(x=>x>0).length,'of 20 seeds','B loses on four seeds and ties once; superiority is not robust.'],
  ['Tie sensitivity, minimum',Math.min(...diffSeeds)*100,'percentage points','Synthetic primary budget only; real queue seed sensitivity not tested.'],
  ['Tie sensitivity, maximum',Math.max(...diffSeeds)*100,'percentage points','No seed was selected to improve the result.'],
], [37,18,18,79]);summary.getRange('B15').formulas=[['=(C10-B10)*100']];summary.getRange('B15:B17').setNumberFormat('0.000');summary.getRange('B19:B20').setNumberFormat('0.000');summary.getRange('A15:D20').format.rowHeight=34;
note(summary,23,'Decision: preserve the operational queue and show enhanced findings separately with source evidence.');
note(summary,24,'Real accuracy is unknown. Supporting documents and independent human adjudication are still needed.');
note(summary,26,'Rebuild: 17 result artifacts and manifest match exactly. All 71 verification checks passed; raw files unchanged.');

const control=sheet('Controlled budgets','Controlled test budgets','7,200 test cases, 3,600 constructed positives and 3,600 controls. Each arm uses identical capacity.');
table(control,5,['Budget','Arm','Positives','Controls','Reviewed','Positive selected','Control selected','Recovery','Yield','Control selection rate'],data.controlled.metrics.map(r=>[r.budget,r.arm,r.positives,r.negatives,r.reviewed,r.true_positive,r.false_positive,null,null,null]),[10,12,12,12,12,14,14,12,12,16]);
for(let r=6;r<=11;r++){control.getRange(`H${r}:J${r}`).formulas=[[`=F${r}/C${r}`,`=F${r}/E${r}`,`=G${r}/D${r}`]];}
control.getRange('A6:A11').setNumberFormat('0%');control.getRange('H6:J11').setNumberFormat('0.00%');
note(control,14,'Recovery uses all constructed positives; yield uses reviewed cases; control selection rate uses all controls.');
table(control,17,['Arm','Alerts > 0','Positive selected','Control selected','Recovery','Control selection rate'],data.controlled.thresholds.map(r=>[r.arm,r.alert_workload,r.true_positive,r.false_positive,r.recovery,r.normal_selection_rate]),[10,12,14,14,14,18]);
control.getRange('E18:F19').setNumberFormat('0.00%');note(control,22,'At unlimited capacity, enhanced screens recover more constructed positives and select more normal controls.');
note(control,23,'Every tested top-budget list has zero zero-score fillers. The full exports record each boundary-tie size.');

const familyRows=[];
for(const name of [...new Set(families.map(x=>x.family))]){
  const a=families.find(x=>x.family===name&&x.arm==='A'),b=families.find(x=>x.family===name&&x.arm==='B');
  familyRows.push([name.replaceAll('_',' '),a.synthetic_positive?'Constructed anomaly':'Constructed normal',a.population,a.selected,b.selected,null,null,null,a.observability==='information_limited'?'Missing supporting facts':'Visible mechanism']);
}
const family=sheet('Case families','Case families at 10% budget','For anomaly rows, higher recovery helps. For normal rows, lower selection helps. Each family has 400 cases.');
table(family,5,['Family','Constructed truth','Cases','A selected','B selected','A rate','B rate','B-A points','Evidence limit'],familyRows,[31,22,10,12,12,11,11,12,23]);
for(let r=6;r<6+familyRows.length;r++){family.getRange(`F${r}:H${r}`).formulas=[[`=D${r}/C${r}`,`=E${r}/C${r}`,`=(G${r}-F${r})*100`]];}
family.getRange('F6:G23').setNumberFormat('0.00%');family.getRange('H6:H23').setNumberFormat('0.00');family.getRange('A6:I23').format.rowHeight=36;family.freezePanes.freezeRows(5);
note(family,26,'Missing supporting facts include approved extensions, invoice/bank evidence, quantities and distinct asset IDs.');
note(family,27,'All benchmark examples are sanctioned. Separate known-answer tests cover pending recommendations and missing dates.');

const real=sheet('Real queues','Real-data queue comparison','160,701 work records across all three parliamentary cohorts. No confirmed truth labels are available.');
table(real,5,['Budget','Reviewed per arm','Shared works','New in B','Displaced from A','Jaccard overlap'],data.real.map(r=>[r.budget,r.reviewed_per_arm,r.overlap,r.new_b,r.displaced_a,null]),[12,21,19,19,23,26]);
for(let r=6;r<=8;r++)real.getRange(`F${r}`).formulas=[[`=C${r}/(B${r}+B${r}-C${r})`]];
real.getRange('A6:A8').setNumberFormat('0%');real.getRange('F6:F8').setNumberFormat('0.00%');
table(real,12,['Cohort at 10% budget','Arm','Selected works','Share'],mix.map(r=>[r.cohort.replaceAll('_',' '),r.arm,r.selected,r.share]),[33,12,19,19]);real.getRange('D13:D18').setNumberFormat('0.00%');real.getRange('A13:D18').format.rowHeight=30;
note(real,21,'10% queue changes: 1,682 works enter B and the same number leave A. This is not evidence that either set is correct.');
note(real,22,'Both methods use the same bounded candidate pairs. Exhaustive duplicate retrieval has not been validated.');
note(real,23,'All real queues are retrospective. No real precision, recall, fraud probability, financial savings or forecast is estimated.');

const methods=sheet('Methods and sources','Methods and sources','Protocol all-cohort-ab-v1. Screen counts are review priorities, not probabilities or legal findings.');
const methodRows=[
 ['Baseline A','Eight shared operational/payment screens plus guarded exact-description/equal-amount duplication.'],
 ['Enhanced B','The same eight screens, guarded near duplication replacing exact duplication, plus one historical peer-cost screen.'],
 ['Duplicate guard','Similarity >=0.96; equal known sanction; at least four meaningful tokens; no conflicting numbers or phase/repair cue. Synthetic pairs test scoring, not retrieval.'],
 ['Cost guard','At least 20 earlier-period state/activity peers, activity fallback; log-MAD scale floor 0.1; robust z>3.5 and amount/median>=2.'],
 ['Financial tolerance','Only successful payments count as spent. Differences must exceed INR1 for the over-sanction screen. This is an analytical rounding tolerance.'],
 ['Historical reference','36,762 sanctions through 31 March 2025 anchor synthetic cost/text frequencies. Synthetic sanctions are later. Real cost features use rolling prior-financial-year peers.'],
 ['Partitions','100 development contexts and 400 test contexts; 18 cases per context. No threshold, weight or supervised model was fit to their labels.'],
 ['Uncertainty','1,000 paired whole-context bootstrap draws. Primary 10% budget, 5%/20% secondary. Twenty alternative tie seeds cover the synthetic primary result only.'],
 ['Missing evidence','Extensions, unit quantities, invoices, bank references and physical asset IDs are not supplied. Similar visible inputs can have different true explanations.'],
 ['Verification','25 known-answer tests passed. Independent rebuild matched 17 result artifacts and manifest, with 71 source/code/reproducibility checks.'],
  ['Local data source','Supplied 18 CSVs; prepared release all-cohorts-2026-09-10-v2; computed offline run all-cohort-ab-v1. Exact record lineage and hashes are retained locally.'],
 ['MoSPI monitoring definitions','https://www.pib.gov.in/PressReleasePage.aspx?PRID=2153066&lang=2&reg=48'],
 ['Leakage safeguards','https://scikit-learn.org/stable/common_pitfalls.html'],
  ['Paired bootstrap method','https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html'],
  ['Benchmark scope','No dedicated exact-duplicate-positive or pending-recommendation family. These screens have known-answer tests; the benchmark does not represent the complete production case mix.'],
];
table(methods,5,['Topic','Definition or source'],methodRows,[31,145]);methods.getRange('A6:B20').format.rowHeight=42;methods.getRange('B6:B20').format.wrapText=true;methods.freezePanes.freezeRows(5);

wb.recalculate();
const before=summary.getRange('B7').values[0][0];summary.getRange('B7').values=[[before+1]];wb.recalculate();checks.push({check:'Recovery updates with selected positives',passed:Math.abs(summary.getRange('B10').values[0][0]-(before+1)/3600)<1e-12});summary.getRange('B7').values=[[before]];wb.recalculate();
checks.push({check:'Primary recovery restored',passed:Math.abs(summary.getRange('B10').values[0][0]-primary.A.recovery)<1e-12});
checks.push({check:'Primary difference agrees with evaluated result',passed:Math.abs(summary.getRange('B15').values[0][0]-(primary.B.recovery-primary.A.recovery)*100)<1e-10});
checks.push({check:'Family selected totals match primary arms',passed:familyRows.reduce((s,r)=>s+r[3],0)===primary.A.reviewed&&familyRows.reduce((s,r)=>s+r[4],0)===primary.B.reviewed});
checks.push({check:'Real Jaccard matches evaluation',passed:Math.abs(real.getRange('F7').values[0][0]-data.real[1].jaccard)<1e-12});
const inspect=await wb.inspect({kind:'table',range:'Summary!A5:D11',include:'values,formulas',tableMaxRows:8,tableMaxCols:4,maxChars:3500});await fs.writeFile(path.join(previews,'key_ranges.json'),JSON.stringify(inspect,null,2));
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:50},summary:'Formula error scan',maxChars:1500});await fs.writeFile(path.join(previews,'formula_scan.json'),JSON.stringify(errors,null,2));console.log('Formula scan',errors.ndjson);
const ranges={'Summary':'A1:D26','Controlled budgets':'A1:J23','Case families':'A1:I27','Real queues':'A1:F23','Methods and sources':'A1:B20'};
for(const [sheetName,range] of Object.entries(ranges)){if(process.argv.includes('--render-methods-only')&&sheetName!=='Methods and sources')continue;const render=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(previews,sheetName.replaceAll(' ','_')+'.png'),new Uint8Array(await render.arrayBuffer()));}
if(checks.some(c=>!c.passed))throw Error('Workbook calculation checks failed');
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(path.join(output,'MPLADS_AB_Results.xlsx'));
await fs.writeFile(path.join(previews,'verification.json'),JSON.stringify({checks,ranges},null,2)+'\n');
console.log(JSON.stringify({output:path.join(output,'MPLADS_AB_Results.xlsx'),checks}));
