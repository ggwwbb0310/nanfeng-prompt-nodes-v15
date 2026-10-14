// V15-only optional skins: paint properties only, no dimensions or execution changes.
const asset=n=>new URL('./assets/menghui/'+n,import.meta.url).href;
const THEMES={
 'menghui-light':{name:'回梦游仙 · 浅色',bg:asset('light.webp'),paper:'#eee7d8',surface:'rgba(247,242,230,.86)',field:'#f6f0e3',ink:'#302e26',muted:'#77705f',line:'#b7ad97',red:'#943d31',brush:asset('brush-ink.png'),node:{color:'#dfd5bf',bgcolor:'#ece4d2',boxcolor:'#943d31'}},
 'menghui-dark':{name:'回梦游仙 · 深色',bg:asset('dark.webp'),paper:'#171715',surface:'rgba(25,25,23,.86)',field:'#20201d',ink:'#e5ddcd',muted:'#b5ad9c',line:'#656052',red:'#b4634b',brush:asset('brush-dark.png'),node:{color:'#24231f',bgcolor:'#151513',boxcolor:'#b4634b'}}
};
const ID='nanfeng-v15-menghui-style';
function installCSS(){if(document.getElementById(ID))return;const s=document.createElement('style');s.id=ID;s.textContent=`
[data-nf15-skin]{color:var(--mh-ink)!important;-webkit-text-fill-color:var(--mh-ink)!important;background-color:var(--mh-paper)!important;border-color:var(--mh-line)!important;box-shadow:none!important;backdrop-filter:none!important}
.nfh3[data-nf15-skin]{background-image:var(--mh-bg)!important;background-size:cover!important;background-position:center bottom!important}
[data-nf15-skin] *:not(img):not(video):not(canvas){color:var(--mh-ink)!important;-webkit-text-fill-color:var(--mh-ink)!important;border-color:var(--mh-line)!important;box-shadow:none!important;text-shadow:none!important;backdrop-filter:none!important;-webkit-backdrop-filter:none!important;accent-color:var(--mh-red)!important}
[data-nf15-skin] :is(section,details,summary,textarea,select,input,[class*=section],[class*=advanced],[class*=head],[class*=settings],[class*=card],[class*=drop],[class*=select-list],[class*=select-option],[class*=select-search],[class*=smart-panel],[class*=config-panel]){background-image:none!important;background-color:var(--mh-surface)!important}
[data-nf15-skin] :is(input,textarea,select,[class*=custom-select]){background:var(--mh-field)!important}
[data-nf15-skin] :is(label,small,[class*=note],[class*=hint],[class*=status]){color:var(--mh-muted)!important;-webkit-text-fill-color:var(--mh-muted)!important}
[data-nf15-skin] ::placeholder{color:var(--mh-muted)!important;-webkit-text-fill-color:var(--mh-muted)!important}
[data-nf15-skin] button{background-color:transparent!important;background-image:var(--mh-brush)!important;background-size:100% 100%!important;background-repeat:no-repeat!important;border-color:transparent!important;border-radius:0!important;color:#f4ecdd!important;-webkit-text-fill-color:#f4ecdd!important}
[data-nf15-skin] button *{color:inherit!important;-webkit-text-fill-color:inherit!important;background-color:transparent!important}
[data-nf15-skin] :is(button.active,button.on,button[aria-pressed=true],.nfh15-smart-storyboard,.nfh15-batch-run,.nfh15-batch-current,.nfh15-batch-shots){background-image:var(--mh-red-brush)!important}
[data-nf15-skin] button:hover:not(:disabled){filter:brightness(1.13)}
[data-nf15-skin] button:disabled{opacity:.42!important}
[data-nf15-skin] :is(input,select,textarea,button):focus-visible{outline:1px solid var(--mh-red)!important;outline-offset:1px}
[data-nf15-skin] ::-webkit-scrollbar-thumb{background:var(--mh-line)!important;box-shadow:none!important}
[data-nf15-skin] ::-webkit-scrollbar-track{background:var(--mh-paper)!important}
[data-nf15-skin] input[type=range]::-webkit-slider-thumb{background:var(--mh-red)!important;box-shadow:none!important;border-color:var(--mh-paper)!important}
[data-nf15-skin] .nfh15-v9-preview-stage{position:relative;background:var(--mh-paper)!important}
[data-menghui-placeholder]{position:absolute;inset:14px;pointer-events:none;overflow:hidden;border:1px solid var(--mh-line);background-image:var(--mh-bg);background-size:cover;background-position:center}
[data-menghui-placeholder]::before{content:'';position:absolute;inset:10px;border:1px solid var(--mh-line);opacity:.4}
[data-nf15-skin] [data-menghui-placeholder] .mh-poem{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:8px;color:var(--mh-poem)!important;-webkit-text-fill-color:var(--mh-poem)!important;text-align:center}
[data-nf15-skin] .mh-poem *{color:inherit!important;-webkit-text-fill-color:inherit!important;background:transparent!important}
.mh-poem strong{font:30px KaiTi,STKaiti,SimSun,serif;letter-spacing:5px}.mh-poem span{font:17px KaiTi,STKaiti,SimSun,serif;letter-spacing:4px}
[data-nf15-skin] .mh-poem em{font:12px KaiTi,serif;letter-spacing:2px;padding:4px;border:1px solid var(--mh-red)!important;color:var(--mh-red)!important;-webkit-text-fill-color:var(--mh-red)!important;transform:rotate(-3deg)}
.mh-preview-hidden{visibility:hidden!important}
[data-nf15-skin] .nfh15-audio-drive-exclude{background:var(--mh-surface)!important}
[data-nf15-skin] canvas.nfh15-audio-drive-waveform{background:var(--mh-paper)!important;border-color:var(--mh-line)!important}
/* Skin-only paint layer: sizes, positioning and media pixels are untouched. */
[data-nf15-skin] :is(div,span,output,fieldset,legend,header,footer,main,nav,aside){background-image:none!important;background-color:transparent!important}
[data-nf15-skin] :is([class*=prompt],[class*=storyboard-bar],[class*=storyboard-tabs],[class*=storyboard-actions],[class*=v9-column]){background-image:none!important;background-color:transparent!important}
[data-nf15-skin] :is([class*=smart-panel],[class*=audio-drive-dialog],[class*=audio-drive-panel],[class*=select-menu],[class*=v9-menu]){background:var(--mh-paper)!important}
[data-nf15-skin] :is(textarea,input,select,[class*=select-button],.nfh15-prompt textarea){background:var(--mh-field)!important;color:var(--mh-ink)!important;-webkit-text-fill-color:var(--mh-ink)!important;caret-color:var(--mh-red)!important}
[data-nf15-skin] :is(textarea,input,select):focus{background:var(--mh-field)!important;border-color:var(--mh-red)!important;box-shadow:none!important}
[data-nf15-skin] :is([class*=title],b,strong){background-image:none!important;background-clip:border-box!important;-webkit-background-clip:border-box!important}
[data-nf15-skin] :is([class*=switch-track],[class*=switch-thumb]){background:var(--mh-line)!important;border-color:var(--mh-muted)!important}
[data-nf15-skin] :is(.on,.active,[aria-pressed=true]) [class*=switch-track]{background:var(--mh-red)!important}
[data-nf15-skin] :is(button.active,button.on,button.enabled,button.paused,button[aria-pressed=true],button[data-smart-run],button[data-config-save],.nfh15-smart-storyboard,.nfh15-batch-run,.nfh15-batch-current,.nfh15-batch-shots){background-image:var(--mh-red-brush)!important}
[data-nf15-skin] button:not(.nfh15-select-button):not(.nfh15-select-option):hover:not(:disabled),[data-nf15-skin] button:not(.nfh15-select-button):not(.nfh15-select-option):active:not(:disabled){background-color:transparent!important;border-color:transparent!important;color:#f4ecdd!important;-webkit-text-fill-color:#f4ecdd!important;box-shadow:none!important}
[data-nf15-skin] button:not(.nfh15-select-button):not(.nfh15-select-option):not(.active):not(.on):not(.enabled):not([data-smart-run]):hover{background-image:var(--mh-brush)!important}
[data-nf15-skin] [class*=select-option]:hover,[data-nf15-skin] [class*=select-option].active{background:var(--mh-line)!important;color:var(--mh-ink)!important}
[data-nf15-skin] *::before,[data-nf15-skin] *::after{color:inherit!important;-webkit-text-fill-color:inherit!important;border-color:var(--mh-line)!important;box-shadow:none!important}
[data-nf15-skin],[data-nf15-skin] *{scrollbar-color:var(--mh-line) var(--mh-paper)!important}
[data-nf15-skin]::-webkit-scrollbar,[data-nf15-skin] ::-webkit-scrollbar{background:var(--mh-paper)!important}
[data-nf15-skin]::-webkit-scrollbar-thumb,[data-nf15-skin] ::-webkit-scrollbar-thumb{background:var(--mh-line)!important;background-image:none!important;border-color:var(--mh-paper)!important;box-shadow:none!important}
[data-nf15-skin]::-webkit-scrollbar-track,[data-nf15-skin] ::-webkit-scrollbar-track,[data-nf15-skin] ::-webkit-scrollbar-corner{background:var(--mh-paper)!important;background-image:none!important}
[data-nf15-skin]::-webkit-scrollbar-thumb:hover,[data-nf15-skin] ::-webkit-scrollbar-thumb:hover{background:var(--mh-muted)!important}
[data-nf15-skin] :is(button[data-config-clear],[data-smart-delete],[class*=delete]){color:#f4ecdd!important;-webkit-text-fill-color:#f4ecdd!important;background-image:var(--mh-red-brush)!important}
[data-nf15-skin] [data-menghui-placeholder]{background-image:var(--mh-bg)!important;background-color:var(--mh-paper)!important}
[data-nf15-skin] .mh-poem{background:transparent!important}
[data-nf15-skin] .mh-poem em{color:var(--mh-red)!important;-webkit-text-fill-color:var(--mh-red)!important}

/* Explicit on-button foreground beats generic descendant ink colors. */
[data-nf15-skin] button:not(img):not(video):not(canvas),
[data-nf15-skin] button:not(img):not(video):not(canvas) *{color:#f4ecdd!important;-webkit-text-fill-color:#f4ecdd!important}
[data-nf15-skin] button.nfh15-storyboard-action.batch:not(img):not(video):not(canvas){background-image:var(--mh-red-brush)!important}
[data-nf15-skin] button:not(img):not(video):not(canvas):disabled{opacity:1!important;background-image:none!important;background-color:#55534c!important;color:#e2dbce!important;-webkit-text-fill-color:#e2dbce!important;border-color:#817b6d!important}
[data-nf15-skin] button:not(img):not(video):not(canvas):disabled *{color:#e2dbce!important;-webkit-text-fill-color:#e2dbce!important;opacity:1!important}
[data-nf15-skin] button .nfh15-batch-icon:not(img):not(video):not(canvas){background:none!important;background-color:transparent!important;border-color:transparent!important;color:#fff4df!important;-webkit-text-fill-color:#fff4df!important}

/* Parameter selectors are reading surfaces, NOT brush action buttons. */
[data-nf15-skin] button.nfh15-select-button:not(img):not(video):not(canvas),
[data-nf15-skin] button.nfh15-select-button:not(img):not(video):not(canvas) *,
[data-nf15-skin] button.nfh15-select-option:not(img):not(video):not(canvas),
[data-nf15-skin] button.nfh15-select-option:not(img):not(video):not(canvas) *{color:var(--mh-ink)!important;-webkit-text-fill-color:var(--mh-ink)!important}
[data-nf15-skin] button.nfh15-select-button:not(img):not(video):not(canvas),
[data-nf15-skin] button.nfh15-select-option:not(img):not(video):not(canvas){background:var(--mh-field)!important;border-color:var(--mh-line)!important;opacity:1!important}
[data-nf15-skin] button.nfh15-select-button:not(img):not(video):not(canvas):hover{border-color:var(--mh-red)!important}
[data-nf15-skin] button.nfh15-select-option:not(img):not(video):not(canvas):is(:hover,.selected,.keyboard){background:var(--mh-red)!important;color:#fff6e8!important;-webkit-text-fill-color:#fff6e8!important}
[data-nf15-skin] button.nfh15-select-option:not(img):not(video):not(canvas):is(:hover,.selected,.keyboard) *{color:#fff6e8!important;-webkit-text-fill-color:#fff6e8!important}
[data-nf15-skin] button.nfh15-select-button:not(img):not(video):not(canvas):disabled,
[data-nf15-skin] button.nfh15-select-button:not(img):not(video):not(canvas):disabled *{color:var(--mh-muted)!important;-webkit-text-fill-color:var(--mh-muted)!important}

/* Every action has a paired surface; generic prompt-container rules cannot erase brush fills. */
[data-nf15-skin] button:not(.nfh15-select-button):not(.nfh15-select-option):not(:disabled){background-color:transparent!important;background-image:var(--mh-brush)!important;background-size:100% 100%!important;background-repeat:no-repeat!important;color:#f4ecdd!important;-webkit-text-fill-color:#f4ecdd!important}
[data-nf15-skin] button:not(.nfh15-select-button):not(.nfh15-select-option):not(:disabled) *{color:#f4ecdd!important;-webkit-text-fill-color:#f4ecdd!important}
[data-nf15-skin] button:not(.nfh15-select-button):not(.nfh15-select-option):not(:disabled):is(.active,.on,.enabled,.paused,[aria-pressed=true],[data-smart-run],[data-config-save],.nfh15-smart-storyboard,.batch){background-image:var(--mh-red-brush)!important}
[data-nf15-skin] button:not(.nfh15-select-button):not(.nfh15-select-option):not(:disabled):hover{background-image:var(--mh-brush)!important;color:#fff6e8!important;-webkit-text-fill-color:#fff6e8!important;transform:none!important}
[data-nf15-skin] button:not(.nfh15-select-button):not(.nfh15-select-option):not(:disabled):is(.active,.on,.enabled,.paused,[aria-pressed=true],[data-smart-run],[data-config-save],.nfh15-smart-storyboard,.batch):hover{background-image:var(--mh-red-brush)!important}

/* Native popup options have their own UA/legacy palette; style independently. */
[data-nf15-skin="menghui-light"] select{color-scheme:light!important}
[data-nf15-skin="menghui-dark"] select{color-scheme:dark!important}
[data-nf15-skin] select :is(option,optgroup){background:var(--mh-field)!important;color:var(--mh-ink)!important;-webkit-text-fill-color:var(--mh-ink)!important;text-shadow:none!important}
[data-nf15-skin] select option:is(:checked,:hover,:focus){background:var(--mh-red)!important;color:#fff6e8!important;-webkit-text-fill-color:#fff6e8!important}
[data-nf15-skin] select option:disabled{background:var(--mh-field)!important;color:var(--mh-muted)!important;-webkit-text-fill-color:var(--mh-muted)!important}
`;s.textContent=s.textContent.replaceAll('[data-nf15-skin]','[data-nf15-skin][data-nf15-skin][data-nf15-skin][data-nf15-skin][data-nf15-skin]');document.head.append(s);}
function paint(el,id){const t=THEMES[id];if(!t){el.removeAttribute('data-nf15-skin');for(const n of ['paper','surface','field','ink','muted','line','red','bg','brush','red-brush','poem'])el.style.removeProperty('--mh-'+n);return;}
 el.dataset.nf15Skin=id;for(const n of ['paper','surface','field','ink','muted','line','red'])el.style.setProperty('--mh-'+n,t[n]);el.style.setProperty('--mh-bg',`url("${t.bg}")`);el.style.setProperty('--mh-brush',`url("${t.brush}")`);el.style.setProperty('--mh-red-brush',`url("${asset('brush-red.png')}")`);el.style.setProperty('--mh-poem',id==='menghui-dark'?'#ddd2bb':'#454335');}
export function skinCanvasColors(node){const t=THEMES[node.properties?.nanfeng_v15_skin_id];return t?{background:t.paper,grid:t.line,wave:t.muted,marker:t.red,selected:t.ink,playhead:t.ink}:{background:'#031312',grid:'#174b47',wave:'#2ab9ae',marker:'#57e3d2',selected:'#d9fff9',playhead:'#ffffff'};}
export function applySkinChrome(node){const t=THEMES[node.properties?.nanfeng_v15_skin_id];if(!t)return false;Object.assign(node,t.node);return true;}
export function mountSkinController(node,root){installCSS();let disposed=false,current='',scheduled=false;const overlays=new Set();
 const preview=()=>{const stage=root.querySelector('.nfh15-v9-preview-stage');if(!stage)return;const actual=!!stage.querySelector('img,video,canvas');const art=stage.querySelector('[data-menghui-placeholder]');const enabled=!!THEMES[current];const empty=stage.querySelector('.nfh15-v9-preview-empty');empty?.classList.toggle('mh-preview-hidden',enabled&&!actual);
  if((!enabled||actual)&&art)art.remove();if(enabled&&!actual&&!art){const el=document.createElement('div');el.dataset.menghuiPlaceholder='';el.setAttribute('aria-hidden','true');el.innerHTML='<div class="mh-poem"><strong>山水有相 · 梦境无边</strong><span>一笔入江湖，一帧寄浮生</span><em>游仙</em></div>';stage.append(el);}};
 const restore=()=>{if(disposed)return;current=node.properties?.nanfeng_v15_skin_id||'xiaoqing';paint(root,current);for(const o of overlays){if(o.isConnected)paint(o,current);else overlays.delete(o);}if(!applySkinChrome(node))Object.assign(node,{color:'#031a19',bgcolor:'#020d0d',boxcolor:'#54d9ce'});preview();node.setDirtyCanvas?.(true,true);};
 const observer=new MutationObserver(()=>{if(scheduled||disposed)return;scheduled=true;queueMicrotask(()=>{scheduled=false;if(!disposed)preview()})});observer.observe(root,{childList:true,subtree:true});
 const controller={restore,select(id){if(id!=='xiaoqing'&&!THEMES[id])return;node.properties||={};node.properties.nanfeng_v15_skin_id=id;restore();node.graph?.change?.();},attach(el){overlays.add(el);paint(el,current);},dispose(){disposed=true;observer.disconnect();overlays.clear();}};
 node.__nf15SkinController=controller;for(const el of node.__nf15PendingSkinOverlays||[])overlays.add(el);delete node.__nf15PendingSkinOverlays;restore();return controller;
}
export function attachSkinOverlay(node,el){if(node.__nf15SkinController)node.__nf15SkinController.attach(el);else (node.__nf15PendingSkinOverlays||=new Set()).add(el);}
export function mountSkinCatalog(main,node,root){
 main.replaceChildren();const grid=document.createElement('div');grid.style.cssText='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px';
 for(const [id,name,desc,image] of [['xiaoqing','小青','原始界面 · 青墨配色',new URL('./assets/v11-new-character-bg-left.webp',import.meta.url).href],['menghui-light',THEMES['menghui-light'].name,'宣纸 / 飞白墨边 / 朱砂',THEMES['menghui-light'].bg],['menghui-dark',THEMES['menghui-dark'].name,'烟江孤舟 / 浓墨 / 暖灰白',THEMES['menghui-dark'].bg]]){
 const card=document.createElement('section');card.dataset.skinId=id;card.style.cssText='padding:12px;border:1px solid #777;background:#272721;color:#eee7d8';const img=document.createElement('img');img.src=image;img.alt=name;img.style.cssText='width:100%;aspect-ratio:1.6;object-fit:cover';const title=document.createElement('h3');title.textContent=name;title.style.cssText='font:19px KaiTi,serif;margin:14px 0 8px';const note=document.createElement('p');note.textContent=desc;note.style.cssText='font-size:12px;color:#bcb49f';const button=document.createElement('button');const selected=(node.properties?.nanfeng_v15_skin_id||'xiaoqing')===id;button.textContent=selected?'当前使用':'使用皮肤';button.style.cssText='margin-top:12px;padding:10px 16px;background:#843f31;color:#f5edda;border:1px solid #a16a55;cursor:pointer';button.onclick=()=>{node.__nf15SkinController.select(id);mountSkinCatalog(main,node,root)};card.append(img,title,note,button);grid.append(card);
 }main.append(grid);
}
