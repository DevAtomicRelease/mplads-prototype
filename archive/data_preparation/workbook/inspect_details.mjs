import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../..');
const data=JSON.parse(await fs.readFile(path.join(root,'data_preparation/local/release_2026-09-10_v2/review_data.json'),'utf8'));
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(root,'outputs/ps26102-all-cohorts-20260910/MPLADS_Data_Review.xlsx')));
const longest=data.dictionary.reduce((best,row,i)=>row.definition.length>data.dictionary[best].definition.length?i:best,0)+6;
const ranges=[
  ['Dictionary_longest','Feature dictionary',`A${longest}:E${longest+1}`],
  ['Review_amounts_and_reasons','Review sample','F5:I8'],
  ['MP_term_boundary','MP terms','A548:F552'],
  ['MP_financials','MP terms','G5:M8'],
  ['Limits_final','Limits and sources','A11:B21'],
];
for(const [filename,sheetName,range] of ranges){
  if(process.argv.includes('--financials-only')&&filename!=='MP_financials')continue;
  const blob=await wb.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(path.join(here,'previews',filename+'.png'),new Uint8Array(await blob.arrayBuffer()));
}
console.log(JSON.stringify({ranges}));
