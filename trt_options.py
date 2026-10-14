import os
import folder_paths

def decoder_options():
    result=[]
    for root in folder_paths.get_folder_paths('vae'):
        for base, _, files in os.walk(root):
            for name in files:
                if name.endswith('.engine') and 'decoder' in name.lower():
                    result.append(os.path.relpath(os.path.join(base,name),root))
    return ['None']+sorted(set(result))

def encoder_options():
    result=[]
    for root in folder_paths.get_folder_paths('vae'):
        for base, _, files in os.walk(root):
            for name in files:
                if name.endswith('.engine') and 'encoder' in name.lower():
                    result.append(os.path.relpath(os.path.join(base,name),root))
    return ['None']+sorted(set(result))

def validate_encoder(name):
    if name not in encoder_options() or name=='None':
        raise ValueError('请先选择本机编译的TRT视频encoder.engine。')

def validate_decoder(name):
    import nodes
    if 'MiniMaxH3TRTVAELoader' not in nodes.NODE_CLASS_MAPPINGS:
        raise ValueError('TRT VAE插件未加载，请检查安装并重启。')
    if name not in decoder_options() or name=='None':
        raise ValueError('请先选择本机编译的TRT视频decoder.engine。')
