import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.join(project, 'outputs/01a06d6b-9b94-7a61-b28b-6f9116f20942');
const snapshot = JSON.parse(await fs.readFile(path.join(project,'pipeline_research/artifacts/snapshot.json'),'utf8'));
const metrics = JSON.parse(await fs.readFile(path.join(project,'validation_research/metrics.json'),'utf8'));
const wb = Workbook.create();
const summary = wb.worksheets.add('Summary');
const orders = {
  Work_Features: ['work_id','review_priority_score','review_priority_band','state','work_description','sanction_amount','sanction_date'],
  MP_Features: ['mp_name','mp_state','mp_constituency','mp_visible_work_count','mp_visible_sanction_total'],
  IDA_Features: ['ida_authority','state','ida_district','ida_visible_work_count','ida_visible_sanction_total'],
  Calamity_Features: ['mp_name','calamity_name','consent_date','consent_amount'],
  Duplicate_Candidates: ['work_id_a','work_id_b','evidence_strength','similarity','description_a','description_b'],
  Feature_Dictionary: ['table','field','dtype','definition','availability_and_caution'],
};
const cols = {};
const letter = i => {let result='';for(i++;i;i=Math.floor((i-1)/26))result=String.fromCharCode(65+(i-1)%26)+result;return result;};
const safe = value => typeof value === 'string' && /^[=+@]/.test(value) ? "'"+value : value;
for (const [name, table] of Object.entries(snapshot.tables)) {
  const sheet = wb.worksheets.add(name);
  const first = (orders[name]||[]).filter(k=>table.columns.includes(k));
  const columns = [...first,...table.columns.filter(k=>!first.includes(k))];
  cols[name]=columns;
  const indices=columns.map(k=>table.columns.indexOf(k));
  const rows=table.rows.map(row=>indices.map((idx,j)=>{
    const v=row[idx];
    return typeof v==='string' && /_date$/.test(columns[j]) && /^\d{4}-\d{2}-\d{2}$/.test(v) ? new Date(v+'T00:00:00Z') : safe(v);
  }));
  sheet.getRangeByIndexes(0,0,1,columns.length).values=[columns];
  for(let start=0;start<rows.length;start+=1000) sheet.getRangeByIndexes(start+1,0,Math.min(1000,rows.length-start),columns.length).values=rows.slice(start,start+1000);
  const used=sheet.getRangeByIndexes(0,0,rows.length+1,columns.length);
  used.format.font={name:'Arial',size:10};
  used.format.columnWidth=26;
  used.format.rowHeight=66;
  used.format.verticalAlignment='top';
  used.format.wrapText=true;
  sheet.getRangeByIndexes(0,0,1,columns.length).format={fill:'#EEEEEE',font:{name:'Arial',size:10,bold:true},rowHeight:70,wrapText:true};
  columns.forEach((key,j)=>{
    const column=sheet.getRangeByIndexes(1,j,rows.length,1);
    if(rows.some(row=>row[j] instanceof Date))column.setNumberFormat('yyyy-mm-dd');
    else if(/amount|allocated_limit|sanction_total|consent_total|median_amount/.test(key))column.setNumberFormat('#,##0.00');
    else if(/_share$|similarity$/.test(key))column.setNumberFormat('0.0%');
    else if(/ratio|robust_z|percentile|score$/.test(key))column.setNumberFormat('0.00');
    if(/description|definition|caution/.test(key))column.format.columnWidth=72;
    else if(/mp_name$|ida_authority$|calamity_name$/.test(key))column.format.columnWidth=40;
    else if(/_id$|priority_score|evidence_strength|similarity$/.test(key))column.format.columnWidth=21;
  });
  const tableStyle=sheet.tables.add(`A1:${letter(columns.length-1)}${rows.length+1}`,true,name+'Table');
  tableStyle.style='TableStyleLight1';
  sheet.getRangeByIndexes(0,0,1,columns.length).format.font={name:'Arial',size:10,bold:true,color:'#111111'};
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);
  console.log(name+': '+rows.length+' rows, '+columns.length+' fields');
}
const ref=(table,key)=>`'${table}'!${letter(cols[table].indexOf(key))}2:${letter(cols[table].indexOf(key))}${snapshot.tables[table].rows.length+1}`;
summary.getRange('A1:C3').values=[['MPLADS connected dataset',null,null],['PS 26102; core-2026-09-06-v1; snapshot proxy 2026-09-01',null,null],['Measure','Value','Interpretation']];
summary.getRange('A4:C17').values=[
  ['Works',null,'Unique supplied sanctioned works'],['Visible sanctions (INR)',null,'Sanction value; not expenditure'],['Reported works total (INR)',snapshot.meta.reportedWorksTotal,'Raw export grand total; source range L10003'],['Visible value coverage',null,'Selected extract, not representative national coverage'],
  ['MP profiles',null,'Allocation master; one missing amount retained'],['Allocated limit total (INR)',null,'Period is not supplied'],['Authorities',null,'Derived from supplied works'],['Calamity consents',null,'MP context; no work-level funding link'],['Consent total (INR)',null,'Separate from sanctions'],['Candidate pairs',null,'Text candidates, not confirmed duplicate assets'],
  ['High priority',null,'Current core rules; not fraud labels'],['Medium priority',null,'Current core rules; not fraud labels'],['Low priority',null,'Current core rules; not fraud labels'],['Routine priority',null,'No guarantee that unflagged works are issue-free'],
];
summary.getRange('B4').formulas=[[`=COUNTA(${ref('Work_Features','work_id')})`]];
summary.getRange('B5').formulas=[[`=ROUND(SUM(${ref('Work_Features','sanction_amount')}),2)`]];
summary.getRange('B7').formulas=[['=B5/B6']];
for(const [cell,table,key,fn] of [['B8','MP_Features','mp_name','COUNTA'],['B9','MP_Features','mp_allocated_limit','SUM'],['B10','IDA_Features','ida_authority','COUNTA'],['B11','Calamity_Features','mp_name','COUNTA'],['B12','Calamity_Features','consent_amount','SUM'],['B13','Duplicate_Candidates','work_id_a','COUNTA']])summary.getRange(cell).formulas=[[fn==='SUM'?`=ROUND(SUM(${ref(table,key)}),2)`:`=${fn}(${ref(table,key)})`]];
['High','Medium','Low','Routine'].forEach((band,i)=>summary.getRange(`B${i+14}`).formulas=[[`=COUNTIF(${ref('Work_Features','review_priority_band')},"${band}")`]]);
summary.getRange('A19:C23').values=[['Use and limitations',null,null],['Features and scores are a frozen pipeline export. Rebuild after data changes; Excel edits do not retrain detectors.',null,null],['This version supersedes the earlier exploratory workbook for application use. Earlier files are preserved.',null,null],['Missing payments, estimates, progress histories and audit labels prevent fraud accuracy, cost-overrun and utilization claims.',null,null],['Join works to MP/IDA many-to-one. Keep consent and candidate-pair tables separate to avoid multiplying amounts.',null,null]];
summary.getRange('A1:C23').format.font={name:'Arial',size:11};
summary.getRange('A1').format.font={name:'Arial',size:15,bold:true};
summary.getRange('A3:C3').format={fill:'#EEEEEE',font:{bold:true}};
summary.getRange('A4:A17').format.columnWidth=32;
summary.getRange('B4:B17').format.columnWidth=27;
summary.getRange('C4:C17').format.columnWidth=85;
summary.getRange('A3:C17').format.rowHeight=29;
summary.getRange('B4:B17').setNumberFormat('#,##0');
for(const cell of ['B5','B6','B9','B12'])summary.getRange(cell).setNumberFormat('#,##0.00');
summary.getRange('B7').setNumberFormat('0.00%');
summary.getRange('A19:C23').format.rowHeight=27;
summary.getRange('A19').format.font={bold:true};
const method=wb.worksheets.add('Rules and sources');
const methodRows=[['Code / source','Points / value','Definition','Caution / source URL'],...snapshot.rules.map(r=>[r.code,r.weight,r.definition,r.caution]),...Object.values(snapshot.meta.sourceFiles).map(r=>[r.file,null,'Raw source SHA-256',r.sha256]),['Guidelines 2023',null,'Receipt-based timing; trust limits and conditional eligibility','https://www.mplads.gov.in/MPLADS/UploadedFiles/MPLADSGuidelinesApril2023.pdf'],['Lok Sabha reply 18 Dec 2024',null,'Updated outside-jurisdiction provision; rule versioning required','https://sansad.in/getFile/loksabhaquestions/annex/183/AS338_TsKdbP.pdf?source=pqals'],['MoSPI annual report',null,'Scheme and eSAKSHI monitoring context','https://mospi.gov.in/sites/default/files/publication_reports/AnnualReport_2023-24.pdf'],['Missing evidence',null,'Recommendation-to-sanction is a proxy; no IDA receipt/MCC periods','Do not interpret high amounts as overpricing or candidate pairs as confirmed duplicates.'],['Availability',null,'Historical aggregates exclude the current sanction date','Full-snapshot peers, pairs, entity totals and Isolation Forest ranks must be recomputed within training folds for prediction.']];
method.getRange(`A1:D${methodRows.length}`).values=methodRows;
const ab=wb.worksheets.add('AB validation');
const abRows=[['Offline controlled benchmark',null,null,null,null,null],['Budget','A recovery','B recovery','B minus A','95% lower','95% upper'],...metrics.synthetic_benchmark.budgets.map(r=>[r.review_fraction,r.a.recovery,r.b.recovery,r.recovery_difference_b_minus_a,...r.paired_bootstrap_95_interval_difference]),['Interpretation',null,null,null,null,null],['1,200 held-out rows; 400 scenario assignments; 800 unchanged records. Background is not verified negative.',null,null,null,null,null],['A: delay/aging. B: A plus historical peer cost and duplicate evidence. Neither is a fraud classifier.',null,null,null,null,null],['20% budget: 37.25% vs 52.75% recovery; +15.5 percentage points (paired interval +12.0 to +18.25).',null,null,null,null,null],['B trades away delay/aging coverage for cost/duplicate coverage. Results do not establish real fraud precision.',null,null,null,null,null],['Not a live randomized trial. Pilot must use blinded independent review at equal capacity.',null,null,null,null,null],['Training works',metrics.split.train_rows,'Held-out works',metrics.split.test_rows,'Cutoff',metrics.split.cutoff_inclusive]];
ab.getRange(`A1:F${abRows.length}`).values=abRows;
ab.getRange('A3:F6').setNumberFormat('0.0%');
for(const sheet of [method,ab]){
  const used=sheet.getUsedRange();used.format.font={name:'Arial',size:10};used.format.rowHeight=65;used.format.verticalAlignment='top';
  used.format.columnWidth=25;
  if(sheet===method){used.format.wrapText=true;sheet.getRange(`A1:A${methodRows.length}`).format.columnWidth=38;sheet.getRange(`C1:D${methodRows.length}`).format.columnWidth=74;sheet.freezePanes.freezeRows(1);}
}
ab.getRange('A2:F2').format={fill:'#EEEEEE',font:{bold:true}};
method.getRange('A1:D1').format={fill:'#EEEEEE',font:{bold:true}};
console.log((await wb.inspect({kind:'table',range:'Summary!A3:C17',include:'values,formulas',tableMaxRows:15,tableMaxCols:3,maxChars:4500})).ndjson);
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},maxChars:1500})).ndjson);
await fs.mkdir(output,{recursive:true});
for(const sheetName of ['Summary',...Object.keys(snapshot.tables),'Rules and sources','AB validation']){
  const sheet=wb.worksheets.getItem(sheetName);
  const range=sheet.name==='Summary'?'A1:C17':sheet.name==='AB validation'?'A1:F6':sheet.name==='Rules and sources'?'A1:D5':'A1:F5';
  const blob=await wb.render({sheetName:sheet.name,range,scale:1,format:'png'});
  await fs.writeFile(path.join(path.dirname(fileURLToPath(import.meta.url)),sheet.name.replaceAll(' ','_')+'.png'),new Uint8Array(await blob.arrayBuffer()));
}
const result=await SpreadsheetFile.exportXlsx(wb);
await result.save(path.join(output,'MPLADS_Final_Core_Dataset_2026-09-06.xlsx'));
console.log('Exported final core workbook.');
