// Per-node lifecycle identity; never inherited through copied workflow JSON.
export function makeOwnerGuard(node){
 const version=node.__nfh3V15Epoch||0;
 return ()=>!node.__nfh3V15Disposed&&(node.__nfh3V15Epoch||0)===version;
}
export function batchIds(node){return new Set([...(node.properties?.nfh3V15OwnedBatchIds||[]),node.properties?.nfh3PendingBatchId].filter(x=>typeof x==='string'));}
export function rememberBatch(node,id){node.properties||={};node.properties.nfh3V15OwnedBatchIds=[...batchIds(node),id].filter((x,i,a)=>a.indexOf(x)===i).slice(-128);node.properties.nfh3PendingBatchId=id;node.graph?.change?.();}
export function ownedBatches(node,rows){const ids=batchIds(node);return rows.filter(row=>ids.has(row.id)&&String(row.node_id)===String(node.id));}
export function ownsActiveNode(app,node){const graph=node.graph;return !!graph&&app.graph===graph&&(graph.getNodeById?.(node.id)===node||(graph._nodes||graph.nodes||[]).includes(node));}
// GraphToPrompt extra workflow metadata is copied, never written into live properties.
export function stampOwner(node,serialized){serialized.properties||={};serialized.properties.__nfh3_v15_execution_owner=node.__nfh3V15RuntimeOwner;}
export function installOwnedPreviewRouting(app,api){
 let generation=0,activeOwnerByNode=new Map();
 const recover=async(promptId)=>{
  const serial=++generation;activeOwnerByNode=new Map();
  try{const response=await api.fetchApi('/queue');const queue=await response.json();if(serial!==generation)return;
   const running=queue.queue_running||[];
   const entry=promptId?[...running,...(queue.queue_pending||[])].find(x=>x[1]===promptId):running[0];
   const workflow=entry?.[3]?.extra_pnginfo?.workflow;
   for(const n of workflow?.nodes||[]){if(n.type==='NanFengH3MultiReferenceGeneratorV15'&&n.properties?.__nfh3_v15_execution_owner)activeOwnerByNode.set(String(n.id),{owner:n.properties.__nfh3_v15_execution_owner,workflowId:workflow.id,scope:workflow.extra?.nanfeng_storyboard_scope});}
  }catch{}
 };
 api.addEventListener('execution_start',e=>recover(e.detail?.prompt_id));
 api.addEventListener('reconnecting',()=>{++generation;activeOwnerByNode=new Map();});
 api.addEventListener('reconnected',()=>recover());
 // A refreshed page missed execution_start. Rebind only to the running queue entry.
 void recover();
 return (node,data)=>{
  const record=activeOwnerByNode.get(String(data?.node_id??''));
  if(!record||node.__nfh3V15Disposed||!node.__nfh3V15RuntimeOwner||!ownsActiveNode(app,node))return false;
  const graph=node.graph;
  if(record.workflowId&&graph.id&&record.workflowId!==graph.id)return false;
  if(record.scope&&graph.extra?.nanfeng_storyboard_scope&&record.scope!==graph.extra.nanfeng_storyboard_scope)return false;
  if(record.owner===node.__nfh3V15RuntimeOwner)return true;
  // Never reconnect by node ID alone, nor copy the old runtime owner into the live node.
  return !!record.workflowId&&!!record.scope&&record.workflowId===graph.id&&record.scope===graph.extra?.nanfeng_storyboard_scope;
 };
}
