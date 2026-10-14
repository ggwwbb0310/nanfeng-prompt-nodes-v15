// One-way smart-dialog media draft. Timed Guide editing is not part of V15.
export function createSmartAssetDraft(assets){
 const clone=x=>JSON.parse(JSON.stringify(x));const state={assets:clone(assets)};
 return {
  values:kind=>[...(state.assets[kind]||[])],
  replace(slot,file){if(!state.assets.图片[slot])throw Error('图片槽位已失效');state.assets.图片[slot]=file;},
  add(file){if(state.assets.图片.length>=9)throw Error('最多9张图片');state.assets.图片.push(file);},
  remove(slot){state.assets.图片.splice(slot,1);},
  move(from,to){const vals=state.assets.图片;if(from===to||from<0||from>=vals.length||to<0||to>=9)return false;if(to<vals.length)[vals[from],vals[to]]=[vals[to],vals[from]];else vals.push(vals.splice(from,1)[0]);return true;},
  snapshot:()=>clone(state)
 };
}
