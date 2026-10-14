export function installCanvasSelectionGuard(doc,win,getCanvas){
 let active=false;
 const reset=()=>{active=false;doc.documentElement.classList.remove('nfh15-v15-canvas-selecting');};
 const down=e=>{if(e.button!==0||!e.ctrlKey||e.target!==getCanvas())return;active=true;doc.documentElement.classList.add('nfh15-v15-canvas-selecting');};
 const move=e=>{if(active&&!(e.buttons&1))reset();};
 doc.addEventListener('pointerdown',down,true);doc.addEventListener('pointermove',move,true);
 win.addEventListener('pointerup',reset,true);win.addEventListener('pointercancel',reset,true);win.addEventListener('blur',reset);
 const visibility=()=>{if(doc.hidden)reset();};doc.addEventListener('visibilitychange',visibility);
 return ()=>{reset();doc.removeEventListener('pointerdown',down,true);doc.removeEventListener('pointermove',move,true);win.removeEventListener('pointerup',reset,true);win.removeEventListener('pointercancel',reset,true);win.removeEventListener('blur',reset);doc.removeEventListener('visibilitychange',visibility);};
}
