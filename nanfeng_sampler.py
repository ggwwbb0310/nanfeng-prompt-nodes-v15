import math
FIELDS={
 '南风ER_solver_type':(['ER-SDE','Reverse-time SDE','ODE'],{'default':'ER-SDE'}),
 '南风ER_max_stage':('INT',{'default':3,'min':1,'max':3}),
 '南风ER_eta':('FLOAT',{'default':1.,'min':0.,'max':10.,'step':0.01}),
 '南风ER_s_noise':('FLOAT',{'default':1.,'min':0.,'max':100.,'step':0.01}),
}
def settings(kw):
 d={key.removeprefix('南风ER_'):kw.get(key,opts['default']) for key,(_,opts) in FIELDS.items()}
 if d['solver_type'] not in FIELDS['南风ER_solver_type'][0]:raise ValueError('南风采样器：未知求解方式')
 if type(d['max_stage']) is not int or not 1<=d['max_stage']<=3:raise ValueError('南风采样器：max_stage须为1–3')
 for k,limit in [('eta',10),('s_noise',100)]:
  if type(d[k]) not in (int,float) or not math.isfinite(d[k]) or not 0<=d[k]<=limit:raise ValueError('南风采样器：'+k+'超出范围')
 return d
def sampler_node(g,name,kw):
 if name!='南风采样器':return g.node('KSamplerSelect',sampler_name=name)
 return g.node('SamplerER_SDE',**settings(kw))
