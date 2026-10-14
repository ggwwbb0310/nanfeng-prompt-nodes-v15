// First built-in skin: the existing V15 appearance, not a recoloring pass.
export const XIAOQING=Object.freeze({id:'xiaoqing',name:'小青',order:0,version:1,node:{color:'#031a19',bgcolor:'#020d0d',boxcolor:'#54d9ce'},renderer:'v15-original'});
export function mountXiaoqing(main,node,root,doc=document){
 main.replaceChildren();
 const card=doc.createElement('section');card.style.cssText='width:min(420px,100%);border:1px solid #54d9ce;background:#020d0d;border-radius:8px;padding:14px;box-sizing:border-box';card.dataset.skinId=XIAOQING.id;
 const thumb=doc.createElement('div');thumb.setAttribute('aria-label','小青：当前节点缩略预览');thumb.style.cssText='width:100%;position:relative;overflow:hidden;pointer-events:none;background:#020d0d;border:1px solid #244944;box-sizing:border-box';
 const title=doc.createElement('div');title.textContent='南风 H3 V15';title.style.cssText='padding:5px 8px;font-size:10px;color:#eafffb;background:#031a19';thumb.append(title);
 // A local inert clone previews actual controls/artwork without adding handlers,
 // requests, media players, duplicated IDs, or modifying the real node.
 const clone=root.cloneNode(true);clone.inert=true;clone.setAttribute('aria-hidden','true');
 for(const el of [clone,...clone.querySelectorAll('*')]){el.removeAttribute('id');el.removeAttribute('name');if(el.matches('input,textarea')){el.value='';el.textContent='';el.removeAttribute('value');}if(el.matches('video,audio,iframe,source')){el.removeAttribute('src');el.removeAttribute('autoplay');}if(el.matches('img')){el.removeAttribute('src');el.removeAttribute('srcset');}}
 const stage=doc.createElement('div');stage.style.cssText='position:relative;overflow:hidden';stage.append(clone);thumb.append(stage);
 const width=root.offsetWidth||2380,height=root.offsetHeight||1180;
 clone.style.setProperty('width',width+'px','important');clone.style.setProperty('height',height+'px','important');clone.style.setProperty('min-width',width+'px','important');clone.style.transformOrigin='top left';
 const heading=doc.createElement('h3');heading.textContent='小青';heading.style.cssText='margin:14px 0 6px;color:#eafffb';
 const note=doc.createElement('p');note.textContent='原始皮肤 · 当前控件、底图与节点配色';note.style.cssText='color:#b5d4ce;font-size:13px';
 const button=doc.createElement('button');button.type='button';button.textContent='当前使用';button.style.cssText='background:#071b1a;color:#eafffb;border:1px solid #54d9ce;padding:8px 18px;cursor:pointer';
 button.onclick=()=>{node.properties||={};node.properties.nanfeng_v15_skin_id=XIAOQING.id;node.graph?.change?.();};
 card.append(thumb,heading,note,button);main.append(card);
 const fit=()=>{const w=stage.clientWidth||390;stage.style.height=(height*w/width)+'px';clone.style.transform=`scale(${w/width})`;};
 requestAnimationFrame(fit);
 return {fit,skin:XIAOQING};
}
