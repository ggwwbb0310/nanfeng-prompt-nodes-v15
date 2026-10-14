import json, logging
from pathlib import Path
SCHEMA=json.loads(Path(__file__).with_name('dlss_schema.json').read_text(encoding='utf8'))
IDS={'image':'NvidiaDLSSImageUpscale','video':'NvidiaDLSSVideoUpscale','fg':'NvidiaDLSSFrameInterpolation'}
def fields(mode):
 return {k:v for section in SCHEMA[mode].values() for k,v in section.items() if k not in ('image','video')}
def schema_fields():
 out={'DLSS超分模式':(['关闭','图像批次超分','视频超分'],{'default':'关闭'}),'启用DLSS补帧':('BOOLEAN',{'default':False})}
 for mode in ('video','fg'):
  for k,(typ,opts) in fields(mode).items():
   opts=opts.copy()
   if typ=='COMBO':typ=opts.pop('options');opts.pop('multiselect',None)
   out[f'DLSS_{mode}_{k}']=(typ,opts)
 return out
class NanFengV15DLSSOutput:
 @classmethod
 def INPUT_TYPES(cls):return {'required':{'images':('IMAGE',),'audio':('AUDIO',),**schema_fields()}}
 RETURN_TYPES=('IMAGE','AUDIO','FLOAT','VIDEO','STRING')
 FUNCTION='run';CATEGORY='南风/V15/internal'
 def run(self,images,audio,**kw):
  import nodes
  from comfy_extras.nodes_video import CreateVideo
  reports={};mode=kw.get('DLSS超分模式','关闭');fg=kw.get('启用DLSS补帧',False)
  def execute(which,payload):
   cls=nodes.NODE_CLASS_MAPPINGS.get(IDS[which])
   if cls is None:raise ValueError('DLSS插件未加载，请重启ComfyUI。')
   prefix='fg' if which=='fg' else 'video'
   args={k:kw.get(f'DLSS_{prefix}_{k}',v[1].get('default')) for k,v in fields(which).items()}
   result=cls.execute(**payload,**args).result
   report=json.loads(result[1]);reports[which]=report
   if report.get('nr_native_fallback'):logging.warning('[V15 DLSS] NVIDIA reports native fallback; neural upscaling is NOT active.')
   return result[0]
  if mode=='图像批次超分':images=execute('image',{'image':images})
  video=CreateVideo.execute(images,24.,audio,bit_depth=8,color_space='sRGB').result[0]
  if mode=='视频超分':video=execute('video',{'video':video})
  if fg:video=execute('fg',{'video':video})
  fps=24.
  if mode=='视频超分' or fg:
   parts=video.get_components();images=parts.images;fps=float(parts.frame_rate)
   # Restore original waveform, avoiding cumulative AAC padding across stages.
   from fractions import Fraction
   from comfy_api.latest import InputImpl, Types
   video=InputImpl.VideoFromComponents(Types.VideoComponents(images=images,audio=audio,frame_rate=parts.frame_rate),bit_depth=video.get_bit_depth(),color_space=video.get_color_space())
  report=json.dumps(reports,ensure_ascii=False)
  return {'result':(images,audio,fps,video,report),'ui':{'text':[report]}}
