#!/usr/bin/env node
'use strict';
/**
 * RTF-broncontrole, NIET de converter of publicatiestap.
 * Gebruik: node tools/rtf-broncontrole.cjs bestand.rtf [rapport.json]
 * Vereist: unrtf (Ubuntu/Debian: sudo apt-get install unrtf).
 * Wijzigt geen bestaande Bijbeltekst, kleuren, namen, wiki-ID's of main-branch.
 */
const fs=require('node:fs');
const cp=require('node:child_process');
const crypto=require('node:crypto');
const path=require('node:path');
const input=process.argv[2];
if(!input){console.error('Geef het pad naar het nieuwe .rtf-bestand.');process.exit(2)}
const destination=process.argv[3]||'tests/rtf-broncontrole.json';
const raw=fs.readFileSync(input);
const text=cp.execFileSync('unrtf',['--text',input],{encoding:'latin1',maxBuffer:32*1024*1024});
const metaPath=path.join(__dirname,'../data/meta.js');
const metaSrc=fs.readFileSync(metaPath,'utf8').trim();
if(!metaSrc.startsWith('SBW.gotMeta(')||!metaSrc.endsWith(');'))throw Error('Onbekend metadataformaat');
const meta=JSON.parse(metaSrc.slice(12,-2));
const books=meta.books.map(x=>x[0]);
const escapeRegex=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const names=books.slice().sort((a,b)=>b.length-a.length).map(escapeRegex).join('|');
const rx=new RegExp('^\\s*(?:\\|\\s*)?('+names+')\\s+(\\d{1,3}):(\\d{1,3})\\b');
const key=(book,ch,v)=>book+':'+Number(ch)+':'+Number(v);
const source=[];
for(let [i,line] of text.split(/\r?\n/).entries()){
  const m=rx.exec(line);if(m)source.push({key:key(m[1],m[2],m[3]),line:i+1,ref:line.trim().slice(0,150),book:m[1]});
}
const old=[];
for(let [i,ref] of meta.blk.entries()){
  const m=rx.exec(ref[2]);
  if(!m)throw Error('Ongeldige bestaande referentie '+JSON.stringify(ref));
  old.push({key:key(m[1],m[2],m[3]),id:i,ref:ref[2],book:m[1]});
}
let cursor=0,aligned=0;
const skipped=[];
for(const entry of old){
  let found=-1;
  // RTF bevat ook ingevoegde verwijzingen en commentaar: geen blinde 1-op-1 koppeling.
  for(let k=cursor;k<Math.min(cursor+70,source.length);k++){
    if(source[k].key===entry.key){found=k;break}
  }
  if(found<0){skipped.push({id:entry.id,ref:entry.ref});continue}
  cursor=found+1;aligned++;
}
const countByBook=Object.fromEntries(books.map(b=>[b,source.filter(x=>x.book===b).length]));
const report={
  source_file:path.basename(input),
  source_sha256:crypto.createHash('sha256').update(raw).digest('hex'),
  source_bytes:raw.length,
  detected_books:books.filter(b=>countByBook[b]>0).length,
  source_reference_candidates:source.length,
  existing_books:meta.books.length,
  existing_blocks:meta.blk.length,
  existing_entity_ids:meta.ents.length,
  sequentially_aligned_references:aligned,
  unaligned_references:skipped.length,
  examples_needing_review:skipped.slice(0,40),
  headers_per_book:countByBook,
  status:'BRONCONTROLE; tekst, kleuren en identiteitsnummers niet gewijzigd',
  safe_to_publish:false
};
fs.mkdirSync(path.dirname(destination),{recursive:true});
fs.writeFileSync(destination,JSON.stringify(report,null,2)+'\n','utf8');
console.log('Boeken',report.detected_books+'/'+books.length,
'· bestaande blokken',old.length,'· gekoppelde referenties',aligned,
'· controlepunten',skipped.length,'· rapport',destination);
if(report.detected_books!==66||skipped.length)process.exitCode=2;
