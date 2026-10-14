// Smart-dialog-only routing. No native schema, global cache or sampler changes.
export function createImageParticipation(images,saved={}){
 let files=[...images];const selections=new Map();
 for(const row of saved.rows||[])if(files.includes(row.filename)&&Array.isArray(row.segments))selections.set(row.filename,[...row.segments]);
 return {
  sync(next){files=[...next];for(const key of selections.keys())if(!files.includes(key))selections.delete(key);},
  replace(old,file){if(selections.has(old)){selections.set(file,selections.get(old));selections.delete(old);}files=files.map(x=>x===old?file:x);},
  get(slot){const v=selections.get(files[slot]);return v?[...v]:null;},
  set(slot,value){if(!files[slot])throw Error('图片槽位无效');if(value===null)selections.delete(files[slot]);else{if(!Array.isArray(value)||value.some(n=>!Number.isInteger(n)||n<1||n>12))throw Error('参与段号无效');selections.set(files[slot],[...new Set(value)].sort((a,b)=>a-b));}},
  snapshot(){return {rows:files.map(filename=>({filename,segments:selections.has(filename)?[...selections.get(filename)]:null}))};},
  plan(count){
   if(!Number.isInteger(count)||count<2||count>12)throw Error('续写生成段数须为2–12');
   if(new Set(files).size!==files.length)throw Error('逐图分段暂不接受重复文件，请移除重复图片');
   for(const vals of selections.values())if(vals.some(n=>n>count))throw Error('参与段号超过生成段数，请重新选择');
   return Array.from({length:count},(_,i)=>{const slots=files.map((_,j)=>j+1).filter(j=>!selections.has(files[j-1])||selections.get(files[j-1]).includes(i+1));return {segment:i+1,slots,images:slots.map(j=>files[j-1])};});
  }
 };
}
export function participationBrief(plan){
 return '\n\n【续写逐图参与契约：以下为实际图片输入限制】\n'+plan.map(p=>`第${p.segment}段：仅可使用${p.slots.length?p.slots.map(n=>`@图片${n} / <Picture ${n}>`).join('、'):'无图片（只承接已有运动上下文）'}。`).join('\n')+'\n图片编号在你返回的文本中仍按本次上传槽位固定，不自行压缩或重编号。每段只声明、引用该段参与的图片；不参与图片连“仅供下一段”等解释也不得写入本段。不得将未参与图片特有的终点构图、发丝/姿势等状态提前转写到本段。全局只写共有连续性，不写任何Picture引用或限定某段的视觉事件。可联合规划全组，但各段执行指令须严格按上述范围。软件写入时会同步处理该段实际素材及Picture编号。';
}
export function routeParticipatingSegments(plan,global,segments){
 if(segments.length!==plan.length)throw Error('返回段数与提交时的图片分配不一致');
 return plan.map((p,i)=>{
  const text=[global?`全局提示词：\n${global}`:'',String(segments[i])].filter(Boolean).join('\n\n');
  const remapped=text.replace(/(?:<\s*Picture\s*(\d+)\s*>|\bPicture\s*(\d+)\b|@?图片\s*(\d+))/gi,(match,a,b,c)=>{
   const source=Number(a||b||c),local=p.slots.indexOf(source)+1;
   if(!local)throw Error(`第${i+1}段引用了未参与的图片${source}，已拒绝写入，请检查返回内容或重新生成提示词`);
   return a?`<Picture ${local}>`:b?`Picture ${local}`:`${match.startsWith('@')?'@':''}图片${local}`;
  });
  return {images:[...p.images],prompt:remapped,sourceSlots:[...p.slots]};
 });
}
export function imageParticipationControl(state,slot,count,onChange){
 const host=document.createElement('details');host.dataset.imageParticipation=String(slot);host.style.cssText='color:#edfffc;font-size:11px;min-width:0;border:1px solid #31575d;border-radius:5px;padding:4px;background:#081b1e';
 const summary=document.createElement('summary');summary.style.cssText='cursor:pointer;overflow-wrap:anywhere';host.append(summary);
 const paint=()=>{const v=state.get(slot);summary.textContent=v===null?'全部段':v.length?`第${v.join('、')}段`:'不参与';};
 const row=(label,checked,fn)=>{const l=document.createElement('label');l.style.cssText='display:flex;gap:4px;align-items:center;margin-top:5px;cursor:pointer';const c=document.createElement('input');c.type='checkbox';c.checked=checked;c.style.cssText='width:13px;height:13px;margin:0;accent-color:#70cfc1';c.onchange=()=>{fn(c.checked);onChange();};l.append(c,document.createTextNode(label));host.append(l);};
 const value=state.get(slot);row('全部段',value===null,on=>state.set(slot,on?null:[]));
 for(let i=1;i<=count;i++)row(`第${i}段`,value===null||value.includes(i),on=>{const current=state.get(slot)??Array.from({length:count},(_,j)=>j+1);state.set(slot,on?[...current,i]:current.filter(n=>n!==i));});
 paint();host.addEventListener('pointerdown',e=>e.stopPropagation());return host;
}
