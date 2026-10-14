// Exact legacy positional migration only. No retired-mode execution implementation.
const REMOVED_INDICES=[174,175,176,177,178,179,224,225];
const OLD_KEYS=['timelineV2','timelineV3','timelineV2Guides','timelineV3Guides','arbitraryFrames','arbitraryGuides','nfh3_audio_drive_silent_timeline_v2','nfh3_audio_drive_waveform_v3'];
export function migrateV15WorkflowInfo(info){
 const data=JSON.parse(JSON.stringify(info));const values=data.widgets_values;
 if(Array.isArray(values)&&values.length===227){
  if([174,177,224].some(i=>values[i]===true))throw Error('V15已删除任意帧、时间轴V2和波形V3。此旧工作流开启了已删除模式，请用V16打开，或重新建立普通V15分镜。');
  data.widgets_values=values.filter((_,i)=>!REMOVED_INDICES.includes(i));
 }
 const props=data.properties||{};
 if(props.nfh3_audio_drive_silent_timeline_v2||props.nfh3_audio_drive_waveform_v3||(props.nanfeng_storyboards||[]).some(s=>s.timelineV2||s.timelineV3||s.arbitraryFrames))throw Error('此V15工作流包含已移除模式的分镜，请用V16处理；不会自动转换执行。');
 const clean=o=>{if(!o||typeof o!=='object')return;for(const k of Object.keys(o)){if(OLD_KEYS.includes(k))delete o[k];else if(typeof o[k]==='object')clean(o[k]);}};clean(props);return data;
}
