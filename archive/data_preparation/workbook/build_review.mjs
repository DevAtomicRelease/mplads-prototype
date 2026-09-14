import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../..');
const input=path.join(root,'data_preparation/local/release_2026-09-10_v2');
const output=path.join(root,'outputs/ps26102-all-cohorts-20260910');
const previewDir=path.join(here,'previews');
await fs.mkdir(output,{recursive:true});await fs.mkdir(previewDir,{recursive:true});
const data=JSON.parse(await fs.readFile(path.join(input,'review_data.json'),'utf8'));
const wb=Workbook.create();
const checks=[];
const sheets={};
const safe=value=>typeof value==='string'&&/^\s*[=+@-]/.test(value)?"'"+value:value;
function sheet(name,title,note){
  const s=wb.worksheets.add(name);sheets[name]=s;s.showGridLines=false;
  s.getRange('A2').values=[[title]];s.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:'#202020'};
  if(note){s.getRange('A3').values=[[note]];s.getRange('A3').format.font={name:'Arial',size:10,color:'#555555'};}
  return s;
}
function table(s,rows,columns,start=5,widths=[]){
  const n=rows.length,c=columns.length;
  const header=columns.map(x=>x[1]);
  const values=rows.map(row=>columns.map(([key])=>{
    const v=row[key];
    return key.endsWith('_date')&&typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)?new Date(v+'T00:00:00Z'):safe(v??null);
  }));
  const range=s.getRangeByIndexes(start-1,0,n+1,c);range.values=[header,...values];
  range.format.font={name:'Arial',size:10,color:'#202020'};range.format.rowHeight=21;range.format.verticalAlignment='center';
  const head=s.getRangeByIndexes(start-1,0,1,c);head.format.fill='#E8E8E8';head.format.font={name:'Arial',size:10,bold:true,color:'#202020'};head.format.wrapText=true;head.format.rowHeight=32;head.format.horizontalAlignment='center';
  columns.forEach(([key],i)=>{
    s.getRangeByIndexes(start-1,i,n+1,1).format.columnWidth=widths[i]??22;
    if(key.endsWith('_inr'))s.getRangeByIndexes(start,i,n,1).setNumberFormat('#,##0.00');
    else if(key.endsWith('_date'))s.getRangeByIndexes(start,i,n,1).setNumberFormat('dd/mm/yy');
    else if(values.some(row=>typeof row[i]==='number'))s.getRangeByIndexes(start,i,n,1).setNumberFormat('#,##0');
  });
  const colLetter=n=>{let label='';while(n){n--;label=String.fromCharCode(65+n%26)+label;n=Math.floor(n/26);}return label;};
  const t=s.tables.add(`A${start}:${colLetter(c)}${start+n}`,true,s.name.replace(/[^A-Za-z]/g,'')+'Table'+start);t.showFilterButton=true;
  s.freezePanes.freezeRows(start);
  return {start,end:start+n,columns:c};
}

const overview=sheet('Overview','MPLADS dataset review','PS 26102. Assessment: 10 September 2026. Investigation screens are not confirmed fraud.');
table(overview,data.overview.map(([metric,value])=>({metric,value})),[['metric','Metric'],['value','Value']],5,[49,25]);
table(overview,data.signals,[['signal','Screen'],['works','Works'],['interpretation','Evidence needed']],19,[66,25,65]);
overview.freezePanes.unfreeze();
overview.getRange('A20:C29').format.wrapText=true;overview.getRange('A20:C29').format.autofitRows();
overview.getRange('A32').values=[['The complete tables are in the prepared CSV/SQLite package. Review sample contains only 1,000 selected works.']];
overview.getRange('A33').values=[['Cohort totals are below the file inventory on Source audit. Screens overlap and are not fraud labels.']];
overview.getRange('A32:C33').format.font={name:'Arial',size:10,color:'#555555'};

const mp=sheet('MP terms','MP-term summaries','All 1,023 supplied allocation records. Amounts are INR; terms are not merged by member name.');
table(mp,data.mp_terms,[['mp_name','Member'],['cohort','Cohort'],['allocation_state','Allocation state'],['tenure_start_date','Term start'],['tenure_end_date','Term end'],['allocated_inr','Allocation limit (INR)'],['work_count','Works'],['sanctioned_count','Sanctioned'],['completed_count','Completed'],['successful_payment_inr','Observed successful payments (INR)'],['pending_payment_inr','Pending requests (INR)'],['open_over_one_year_count','Open > 1 year'],['mp_key','MP term key']],5,[40,28,23,15,15,28,13,15,15,28,28,18,40]);mp.freezePanes.freezeColumns(1);
mp.getRangeByIndexes(5,0,data.mp_terms.length,1).format.wrapText=true;
mp.getRangeByIndexes(5,0,data.mp_terms.length,13).format.autofitRows();

const review=sheet('Review sample','Screened-work review sample','Top 1,000 by unweighted screen count, then sanction amount and key. Full population is in Work_Features.csv.');
table(review,data.review_sample,[['work_id','Work key'],['cohort','Cohort'],['mp_name','Member'],['state','State'],['activity_type','Activity'],['screening_signal_count','Screens'],['sanction_amount_inr','Sanction (INR)'],['successful_payment_inr','Observed successful payments (INR)'],['screening_reasons','Screen codes']],5,[24,28,40,23,70,14,25,28,100]);review.freezePanes.freezeColumns(1);
review.getRangeByIndexes(5,2,data.review_sample.length,1).format.wrapText=true;
review.getRangeByIndexes(5,4,data.review_sample.length,1).format.wrapText=true;
review.getRangeByIndexes(5,8,data.review_sample.length,1).format.wrapText=true;
review.getRangeByIndexes(5,0,data.review_sample.length,9).format.autofitRows();

const src=sheet('Source audit','Source audit','All original CSVs remain unchanged. Record ordinals count CSV records, not physical lines.');
table(src,data.sources,[['cohort','Cohort'],['kind','Source'],['source_rows','Original rows'],['accepted_rows','Accepted rows'],['quarantined_rows','Quarantined'],['column_count','Columns'],['source_file','Source file']],5,[29,23,19,19,19,13,58]);
table(src,data.cohorts,[['cohort','Cohort'],['work_count','Works'],['recommended_record_count','Recommended'],['sanctioned_count','Sanctioned'],['completed_count','Completed'],['successful_payment_inr','Observed successful payments (INR)'],['pending_payment_inr','Pending requests (INR)']],27,[29,23,19,19,19,28,58]);
src.freezePanes.freezeRows(5);
src.getRange('A31').values=[['Total']];
for(const c of ['B','C','D','E','F','G'])src.getRange(c+'31').formulas=[['=SUM('+c+'28:'+c+'30)']];
src.getRange('A31:G31').format.font={name:'Arial',size:10,bold:true};src.getRange('B31:E31').setNumberFormat('#,##0');src.getRange('F31:G31').setNumberFormat('#,##0.00');
src.getRange('A33').values=[['Source: supplied 18 CSV files. Exact input hashes and record references are in the complete source audit and dataset manifest.']];
src.getRange('A33:G33').format.font={name:'Arial',size:10,color:'#555555'};

const dict=sheet('Feature dictionary','Feature dictionary','Definitions cover the prepared tables. Snapshot outcomes are not safe inputs to earlier-time predictions.');
table(dict,data.dictionary,[['table','Table'],['field','Field'],['unit','Unit'],['definition','Definition'],['model_use','Model use']],5,[31,46,37,115,90]);dict.freezePanes.freezeColumns(2);
dict.getRangeByIndexes(5,0,data.dictionary.length,5).format.wrapText=true;
dict.getRangeByIndexes(5,0,data.dictionary.length,5).format.autofitRows();

const limits=sheet('Limits and sources','Limits and sources','Missing evidence is kept separate from suspicious behaviour.');
const limitRows=[...data.limits,{topic:'Zero observed payments',limitation:'A zero observed payment total is not proof of zero real expenditure. Coverage flags in the full dataset distinguish missing payment evidence.'}];
table(limits,limitRows,[['topic','Topic'],['limitation','Limit']],5,[29,150]);
limits.getRangeByIndexes(5,1,limitRows.length,1).format.wrapText=true;
limits.getRangeByIndexes(5,0,limitRows.length,2).format.rowHeight=42;
limits.getRange('A19:B21').values=[
  ['Monitoring definitions','MoSPI, 6 Aug 2025: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2153066&lang=2&reg=48'],
  ['Portal data definitions','MoSPI, 6 Mar 2026: https://www.pib.gov.in/PressReleasePage.aspx?PRID=2235932&lang=1&reg=3'],
  ['Numeric tolerance','Payment and completion over-sanction screens use > INR 1 difference. This is a screening choice, not a legal threshold.']
];limits.getRange('A19:B21').format.font={name:'Arial',size:10};limits.getRange('A19:B21').format.rowHeight=30;

wb.recalculate();
const expectedWorks=data.cohorts.reduce((s,r)=>s+r.work_count,0);
const original=src.getRange('B28').values[0][0];
src.getRange('B28').values=[[original+1]];
wb.recalculate();
checks.push({check:'Formula total updates after input change',passed:src.getRange('B31').values[0][0]===expectedWorks+1});
src.getRange('B28').values=[[original]];wb.recalculate();
checks.push({check:'Restored total matches complete dataset',passed:src.getRange('B31').values[0][0]===expectedWorks});
checks.push({check:'Sample does not replace complete work count',passed:data.review_sample.length===1000&&expectedWorks>data.review_sample.length});
const formulaScan=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:50},summary:'Final formula error scan',maxChars:3000});
await fs.writeFile(path.join(previewDir,'formula_scan.json'),JSON.stringify(formulaScan,null,2));
console.log('Formula scan',formulaScan.ndjson);
const ranges={'Overview':'A1:C29','MP terms':'A1:F12','Review sample':'A1:F10','Source audit':'A1:G12','Feature dictionary':'A1:D10','Limits and sources':'A1:B10'};
for(const [name,range] of Object.entries(ranges)){
  if(process.argv.includes('--render-changed')&&['Overview','Feature dictionary'].includes(name))continue;
  const preview=await wb.render({sheetName:name,range,scale:1,format:'png'});
  await fs.writeFile(path.join(previewDir,name.replaceAll(' ','_')+'.png'),new Uint8Array(await preview.arrayBuffer()));
}
const cohortPreview=await wb.render({sheetName:'Source audit',range:'A26:G31',scale:1,format:'png'});
await fs.writeFile(path.join(previewDir,'Cohort_totals.png'),new Uint8Array(await cohortPreview.arrayBuffer()));
if(checks.some(c=>!c.passed))throw new Error('Workbook calculation test failed');
const xlsx=await SpreadsheetFile.exportXlsx(wb);const finalPath=path.join(output,'MPLADS_Data_Review.xlsx');await xlsx.save(finalPath);
await fs.writeFile(path.join(input,'workbook_verification.json'),JSON.stringify({file:finalPath,sheets:Object.keys(sheets),checks,rendered_ranges:ranges},null,2)+'\n');
console.log(JSON.stringify({file:finalPath,sheets:Object.keys(sheets),checks}));
