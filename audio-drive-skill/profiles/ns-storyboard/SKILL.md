---
name: hailuo-prompt
description: 用户明确说“海螺H3提示词”时调用；输出本地ComfyUI英文结构（多参多段连续分镜）。不得因“用H3官方写”或“H3官方提示词”触发。
version: 2.7.0
---

# 海螺 H3 英文提示词生成器（DeepSeek / 本地 ComfyUI）

## 概述

这是用户指定的正式海螺H3 Skill，由DeepSeek或当前主模型执行。默认把用户的中文场景、参考素材、动作、运镜和声音要求，整理为**英文内容的H3结构化提示词**。

用户的多段视频均为**多参（Reference/Ref2VA）模式**：每段一次生成，多段串成连续剧情。分镜必须段内连续、段间连续（见「八、连续分镜与跨段连续」）。

官方开源Prompting Guidance明确推荐六段内容使用英文。本地H3使用Qwen3-VL多语言编码器，能理解中英文；用户明确选择“英文输出优先”，因此本Skill采用：

- 固定字段名和机器标签保持官方形式；
- 各字段正文、动作、镜头、声音和约束默认写英文；
- 对白跟随用户指定语言（`<d>[用户指定语言] ...</d>`），用户没指定时默认英文；
- 始终输出英文正文，不擅自输出中文或双语。

官方依据：

- `https://huggingface.co/MiniMaxAI/MiniMax-H3`
- `docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md`
- `docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md`
- `https://platform.minimax.io/docs/guides/video-prompt`
- `https://platform.minimax.io/docs/guides/video-generation`

## 触发条件

仅当用户明确说“海螺H3提示词”时加载本Skill。

- 用户说“H3官方提示词”时，必须改用独立Skill `H3官方提示词`，不得加载本Skill。
- 只说“H3提示词”而未指明版本时，不得自行把它等同于“海螺H3提示词”。
- 两套Skill相互独立：本Skill负责用户原有的本地南风H3节点流程；`H3官方提示词`负责MiniMax官方英文结构流程。

## 最高优先级规则

1. **正文默认英文**：人物定义、动作、镜头、声音、保留分析和约束均写英文。
2. **固定字段和标签不翻译**：保留`subject_definitions:`、`<Picture 1>`、`[Shot 1]`、`<d>[Language] ...</d>`等官方机器格式。
3. **对白仅放进`<d>[用户指定语言] ...</d>`**；动作、表情、说话方式必须写在标签外。对白语言跟随用户指定，用户没指定时默认英文。
4. **呻吟、喘息、闷哼、叫床等非语言性声响不是对白**：它们属于动作和声音设计，直接写在镜头描述和`overall_soundscape`中，一律不得放进`<d>`标签。`<d>`只用于真正的字词句子（如"你好"、"Hello"等）。
5. **南风H3节点的多参图片引用采用完整绑定行**：提示词中禁止保留`@图片N`；每张已上传图片按其**物理槽位编号永久绑定**，直接输出`<Subject N> is the visual content referenced from <Picture N>`。例如图片槽1→`<Subject 1> is the visual content referenced from <Picture 1>`，图片槽3→`<Subject 3> is the visual content referenced from <Picture 3>`，不得压缩或重排。
6. **多参视频和音频使用原生标签**：`<Video N>`、`<Audio N>`；视频配套音轨和独立音频共享全局`Audio`序号，严格跟随南风H3节点实际呈现顺序。
7. **文生、图生、首尾帧不使用`@`引用逻辑**：它们由固定模式、固定图片槽和官方对齐指令确定素材。
8. **防朗读采用官方机制，禁止写防朗读元指令**：无对白时不写`<d>`、不分配`(Sx)`，也不写“不要朗读”“人物保持安静”“No dialogue”等元文本，避免被当成语音内容。
9. 默认只输出最终可复制提示词，不输出解释、模式说明或双语对照。
10. 原NSFW逻辑保持不变，见对应章节。
11. **场景按需写，不擅自加**：用户明确提到地点/环境/氛围时才写进镜头描述（如"脏厕所""工地""办公室"），用户没提就绝不写。模型根据参考图自行推断环境。
12. **自动分镜数（按内容判断）**：分镜数量按动作/剧情的节拍数判断，不按秒数写死；一个镜头装得下的连续动作就一镜，动作多、节奏快才拆多镜。具体见「八、连续分镜与跨段连续」。
13. **连续与跨段连续**：段内动作因果衔接；跨段时上一段最后一个镜头的落幅 = 下一段第一个镜头的起幅，用正反打或切镜头衔接。

## 模型能力速查

| 项目 | 规格 |
|---|---|
| 模型 | MiniMax-H3 |
| 常用时长 | 4–15秒 |
| 输出 | 768P / 2K |
| 参考图 | 最多9张 |
| 参考视频 | 最多3段，单段2–15秒 |
| 参考音频 | 最多3段 |
| 混合参考 | 总计最多12个文件 |
| 本地节点 | `MiniMaxH3ImageToVideo` / `MiniMaxH3ReferenceToVideo` |

如果当前ComfyUI节点或最新官方文档显示不同限制，以实际节点为准。

# 一、生成模式

## T2VA：纯文生有声视频

直接输出三个固定字段，字段正文用英文：

```text
integrated_multimodal_description:
[Shot 1] ……

overall_soundscape:
……

non_diegetic_music:
……
```

## I2VA：首帧图生视频

`<Picture 1>` 是视频 0.00 秒的真实首帧，属于 `[Shot 1]`。

首行写：

```text
The target video fully references <Picture 1> at 0.00s; this image is the actual first frame of [Shot 1].
```

空一行后输出三个核心字段。Shot 1 从图片内容出发向前发展——先描述图中已有的人物、构图、关系，再写接下来发生的动作。推荐结构：**首帧锚定 → 动作起始 → 持续发展 → 结果或反应**。人物身份、服装、颜色、关键物体、空间关系全程保持一致。

## FL2VA：首尾帧

Picture 1 是开头，Picture 2 是结尾。

首行写：

```text
Alignment of reference images to the target video: <Picture 1> corresponds to [Shot 1] at 0.00s; <Picture 2> corresponds to [Shot N] at S.SSs.
```

`N`为最后一个实际镜头编号，`S.SS`为保留两位小数的有效时长。

**优先采用单镜头连续过渡**——让模型在第一帧和最后一帧之间连续插值，不要切成多镜。只有用户明确要求切镜时才使用多镜头。

推荐结构：**首帧状态 → 可观察的中间变化 → 渐进缩小差异 → 尾帧落地**。重点写主体的运动过程、姿势变化、物体操作和构图演变，而不是重复描述两张静态图片。最后一帧必须在最后的 `[Shot N]` 的结尾精确抵达。

## L2VA：仅尾帧

`<Picture 1>` 是视频最后帧，属于最后一个 `[Shot N]`，而不是 Shot 1。

首行写：

```text
Alignment of reference images to the target video: <Picture 1> corresponds to [Shot N] at S.SSs and serves as the actual last frame of the target video.
```

先根据用户意图和尾帧推断一个合理的起始状态，再描述人物、物体、摄影机与场景如何逐步接近尾帧。推荐结构：**合理前置状态 → 明确的动作与过渡路径 → 尾镜逐步收敛 → 尾帧落地**。

## Reference / Ref2VA：全能参考（也称"多参模式"）

全能参考使用六段结构，字段名固定，字段正文用英文。**这是用户多段连续视频的主模式**。

```text
subject_definitions:
……

summary:
……

retention_analysis:
……

detailed_description:
……

overall_soundscape:
……

non_diegetic_music:
……
```

不得退回旧式"图1用于人物，图2用于场景"的无标签单段提示词。

# 二、南风H3节点引用编号与绑定

## 多参图片：物理槽位永久绑定

南风H3复合节点界面使用图片槽1–9，并规定图片槽位编号同时作为`Subject`和`Picture`编号：

```text
图片槽1 -> <Subject 1> is the visual content referenced from <Picture 1>
图片槽2 -> <Subject 2> is the visual content referenced from <Picture 2>
图片槽3 -> <Subject 3> is the visual content referenced from <Picture 3>
```

这是用户为南风H3节点确定的固定约定：

1. 编号永久绑定物理上传槽位，不按实际已上传数量压缩；
2. 图片槽1和图片槽3有素材而图片槽2为空时，仍使用`Subject/Picture 1`和`Subject/Picture 3`；
3. 人物、多人组合、场景、道具、动物、载具、特效均可作为一个整体视觉引用单元；
4. 若必须分别控制同一图片里的多个对象，才手工拆分多个Subject；默认自动提示词不得擅自拆分；
5. 编辑器中的`@`只负责选择素材，最终可复制提示词中不得出现`@图片N`。

## 多参视频和音频

视频槽位使用：

```text
视频槽1 -> <Video 1>
视频槽2 -> <Video 2>
视频槽3 -> <Video 3>
```

视频配套音轨与独立音频共享`<Audio N>`序号。按南风H3节点呈现顺序：先遍历视频槽；启用的视频音轨先得到下一个`Audio`编号，再呈现对应`Video`；最后追加独立音频。

示例：

```text
视频槽1带原音 -> <Audio 1>，对应视频 -> <Video 1>
视频槽2无原音 -> <Video 2>
独立音频槽1   -> <Audio 2>
独立音频槽2   -> <Audio 3>
```

不得仅按独立音频槽号推测`Audio`编号。

## Base/FL模式没有@引用

- T2VA文生：0张图片，无素材引用；
- I2VA图生：图片槽1固定为0秒首帧`<Picture 1>`；
- FL2VA首尾帧：图片槽1固定为首帧`Picture 1`，图片槽2固定为尾帧`Picture 2`；
- 以上三种模式不输出`@图片N`，不生成多参Subject绑定行，也不使用多参视频/音频引用。

# 三、运镜（参考 H3 官方运镜词汇）

写运镜时用自然英文融入镜头描述，不要堆成独立标签。格式：**运镜类型 + 幅度 + 速度**。

| 运镜类型 | 中文含义 | 说明 |
|---|---|---|
| `Zoom In / Zoom Out` | 推近 / 拉远 | 焦距变化，机身不动 |
| `Push In / Pull Out` | 推进 / 拉出 | 摄影机前后移动 |
| `Pan Left / Pan Right` | 左摇 / 右摇 | 机身不动，镜头水平旋转 |
| `Truck Left / Truck Right` | 左移 / 右移 | 摄影机水平平移 |
| `Tilt Up / Tilt Down` | 上摇 / 下摇 | 机身不动，镜头垂直旋转 |
| `Pedestal Up / Pedestal Down` | 上升 / 下降 | 整机垂直移动 |
| `Arc Shot` | 弧形环绕 | 摄影机绕主体弧线运动 |
| `Tracking Shot` | 跟随 | 摄影机跟随运动主体 |
| `Static Shot` | 静止 | 摄影机位置和镜头不变 |
| `Shake Slightly / Strongly` | 轻微 / 剧烈晃动 | 手持或震动效果 |
| `POV` | 第一人称视角 | 以角色眼睛看出去 |
| `Roll CW / CCW` | 顺时针 / 逆时针翻滚 | 绕镜头轴旋转 |

幅度：`small amplitude`、`large amplitude`。速度：`slow speed`、`fast speed`。中等幅度和正常速度省略不写。

写法示例：
```
[Shot 1] 00:00.000, the camera slowly zooms in on the folded letter resting on her lap.
[Shot 2] 00:04.000, the camera tracks her as she walks from the doorway to the desk.
[Shot 3] 00:07.000, static shot, she lifts her eyes to look at the camera.
```


# 四、Reference六段写法

## 1. subject_definitions：绑定

每行一条，使用南风H3节点的完整英文绑定行：

```text
<Subject 1> is the visual content referenced from <Picture 1>
<Subject 2> is the visual content referenced from <Picture 2>
<Subject 3> is the visual content referenced from <Picture 3>
```

规则：

- `Subject N`与`Picture N`的N必须等于实际图片物理槽位编号；
- 人物、多人组合、场景、道具均可使用同一通用绑定句，不在定义中额外复述图片内容；
- 空槽位跳过但编号保留，例如图片槽1和3有素材就输出Subject/Picture 1和3；
- 只定义真正参与成片的图片素材；
- 最终提示词禁止出现`@图片N`。

## 2. summary：一句话概括

```text
[Reference generation] The target video shows <Subject 1> walking into <Subject 2>, adopting only the gait rhythm and restrained camera movement of <Video 1>, while fully preserving the character identity and clothing in <Picture 1>.
```

格式：`[任务类型1 + 任务类型2] 目标视频……`，正文用英文。

## 3. retention_analysis：保留声明

```text
<Subject 1> (appears in [Shot 1], [Shot 2], [Shot 3]): Full retention — appearance, clothing, accessories, and hairstyle unchanged.
<Subject 2> (appears in [Shot 1], [Shot 2]): Full retention — appearance and proportions unchanged.
```

保留等级：`Full retention`、`Partial retention`、`Weak reference`、`Attribute transfer`。

规则：

- 不要在retention里复述图片中的发型、五官、服装或道具；
- 行为或动作是否保留取决于用户意图，不在本段默认追加。

## 4. detailed_description：分镜动作

**核心原则：每个镜头只做一件事，用最直白的英文写。**不写景别、不写机位、不写运镜、不写场景、不写光影、不写风格、不堆修辞。像跟朋友口述画面一样简单。镜头直接从主体动作开始，模型根据参考图自行推断环境。

```text
[Shot 1] 00:00.000, the woman kneels at the edge of the bed, lowers her head and takes the erect penis into her mouth, her lips slowly wrapping around the glans.
[Shot 2] 00:03.000, her head begins to bob up and down, picking up speed, her hair swaying with the motion.
[Shot 3] 00:06.000, she looks up at him, keeping him in her mouth, her eyes wet.
[Shot 4] 00:08.000, she slowly pulls back, a strand of saliva stretching as her lips leave him, then gasps and looks up.
```

规则：

- **场景按需写**：用户提到地点才写，没提就不写，不擅自加场景描述；
- **一个镜头只写一个动作**：复杂动作拆成多个镜头，不在一镜中塞多个步骤；
- **口语化**：用"thrust in""suck""rub""lick""on all fours"等直白口语，禁用"pierce""convulse""sway""permeate"等书面词；
- **主语+动作**：每句有明确主语；
- **只写眼睛能看到的东西**：不写内心感受、情绪描写；
- **不改变人物外观**：图片里角色穿什么、戴什么、长什么样，镜头中完全保持，不增不减；
- NSFW直接写：`penis`、`vagina`、`breasts`、`thrust`、`lick`、`suck`、`pound`；
- 不做说话口型（除非有对白）。

## 5. overall_soundscape

```text
overall_soundscape:
Continuous indoor ambience, footsteps, the rustle of fabric, and rain against the window, precisely synchronized with the on-screen action.
```

用1-3句英文。

## 6. non_diegetic_music

```text
non_diegetic_music:
N/A
```

无配乐写`N/A`。

# 五、对白写法

使用`<d>[用户指定语言] ...</d>`标签，语言跟随用户指定（未指定默认英文）。示例：

```text
<Subject 1> (S1) looks toward the door and says in a calm, low voice: <d>[English] You're finally here.</d> She then closes her lips and stays quiet.
```

用户指定日语就写 `<d>[Japanese] …</d>`、指定中文就写 `<d>[Chinese] …</d>`，以此类推。

规则：

1. 只有真正需要说话时才使用`<d>`；
2. 说话者、动作、语气、音色写在`<d>`外；
3. 发声人物使用稳定的`（S1）`、`（S2）`；
4. 用户原对白必须保留说话人、原意、顺序和关键措辞；
5. "不要字幕"不等于删除对白；
6. 不需要对白时禁止出现任何`<d>`。

禁止把动作和镜头说明塞进`<d>`：

```text
❌ <d>[English] The heroine turns around, the camera pushes in, she sadly says you're finally here.</d>
```

正确：

```text
<Subject 1> turns around, the camera slowly pushes in. She (S1) says sadly: <d>[English] You're finally here.</d>
```

# 六、防朗读（官方机制）

H3 官方设计：**没有`<d>`标签就不会发声，没有`(Sx)`说话人ID就不会开口。**

无对白时：直接不写`<d>`标签、不给人物分配`(Sx)`。动作描述照常写，H3 自己知道不说话。

**禁止在提示词正文中插入任何防朗读元指令**（如"Don't read the prompt""Characters stay quiet""No dialogue or narration"等）——这些元文本会被模型当成旁白内容读出来，适得其反。

有对白时：只在有`<d>`的句子里分配`(Sx)`，说完后写"closes her lips and stays quiet"。

完全静音：`overall_soundscape: N/A` + `non_diegetic_music: N/A`。

# 七、Base模式完整示例

```text
integrated_multimodal_description:
[Shot 1] 00:00.000, the woman walks in through the doorway, one hand on the door frame, her gaze sweeping the room.
[Shot 2] 00:03.000, she walks to the desk, her fingers sliding across the surface, a thin layer of dust gathering on her fingertips.
[Shot 3] 00:06.000, she bends down and picks up an old photograph from the floor, turning it over to look at the back.
[Shot 4] 00:09.000, she presses the photograph to her chest, closes her eyes, her lips pressing lightly together.

overall_soundscape:
Indoor ambience, footsteps, and the rustle of fabric, synchronized with the action.

non_diegetic_music:
N/A
```

# 八、连续分镜与跨段连续（多参多段）

用户的多段视频都是多参（Reference/Ref2VA）模式：每段单独生成、每段时间戳从 `00:00.000` 重新开始，但人物与世界状态必须跨段继承，最终串成同一条连续剧情。

## 生成前内部连续性账本（只在内部维护，默认不输出）

为每一段、每一镜记录并继承以下状态：

- **身份**：固定 `<Subject N>`、外观、发型、服装、显著特征、说话人编号；
- **画面位置**：画面左/中/右，前景/中景/后景，人物在画面中的大小；
- **身体状态**：朝向、视线、姿势、动作阶段、领先脚、双手占用；
- **人物关系**：谁面向谁、相对距离、遮挡关系、移动路径；
- **道具状态**：归属、由哪只手持有、开合/完整状态、固定位置；
- **场景锚点**：门、窗、桌椅、床、车辆、入口与出口的稳定方位；
- **摄影机**：景别、机位、运动、动作轴一侧、人物比例；
- **声音**：说话人、对白顺序、未完台词、环境声和用户指定音乐。

段 N 的结尾账本默认直接成为段 N+1 的开头账本；只有用户明确要求转场、换装、换地点或时间跳跃时才能改变。

## 自动分镜数（按内容判断，不写死）

分镜数量**不按秒数硬套**，根据动作/剧情有几个可观察节拍判断：

- 一个持续动作或一条不间断动作路径 → **1 个镜头**装完；
- 动作有明显转折或多个独立阶段 → 按阶段拆镜；
- 每镜通常参考 2–5 秒，但不是硬限制；10 秒保持一个连续镜头也允许；
- 带对白正反打时，每个说话方向或必要反应方向可单独成镜；
- 只有切镜能展示必要的新信息时才切，不为变化景别而硬切。

总原则：**镜头数 = 必要的独立动作/信息节拍数**。用户明确指定分镜数时以用户为准；内容超出时长时，先删次要运镜和装饰信息，不删、不改、不重排用户对白和主要动作。

## 段内连续与空间逻辑

- 每个主要动作遵循：**起始状态 → 可观察的连续路径 → 明确终点/反应**；
- 前一镜动作终点 = 后一镜动作起点，不能重做、跳过、倒退或瞬移；
- 切镜只改变观察角度，不改变世界状态；新镜头从切镜前已经到达的精确状态开始；
- 画面构图使用 `screen-left/screen-right`，现实位置使用 `beside the door/behind the table` 等场景锚点，不得混用后偷偷互换；
- 保持180度动作轴、视线方向和移动方向。必须越轴时，用可见的连续运镜或中性重建镜头完成；
- 道具交接必须展示手递手、放下再拿起等可见路径，不得换手或凭空出现；
- 复杂身体动作与复杂运镜不要同时竞争，优先保证动作主体、脸、手和关键部位清晰可读。

## 跨段连续交接

**上一段最后一个可见状态 = 下一段第一个可见状态。** 下一段时间戳虽然重置为 `00:00.000`，世界状态不能重置。

下一段首镜必须继承上一段尾镜的：

- 人物身份、外观、服装和场景；
- 画面位置、身体朝向、视线、姿势与动作阶段；
- 人物间距离、遮挡、道具归属和道具状态；
- 光线、景别、屏幕方向与摄影机所在的动作轴一侧；
- 尚未结束的对白、环境声和动作声。

执行规则：

1. 下一段继续尚未完成动作的当前阶段，不重新起势，不重复、不跳过、不逆转；
2. 只重申防漂移所需的继承事实，不把上一段剧情全部复述一遍；
3. 有上一段尾帧或源视频结尾时，把它作为下一段的首帧/延续锚点，并使用对应的官方模式；
4. 无尾帧素材时，在下一段 `[Shot 1]` 开头明确写出人物位置、朝向、姿势、视线、道具和当前动作阶段；
5. 换机位/换景别时继续同一世界状态；正反打保持动作轴、视线和人物左右关系；
6. 用户明确要求转场时，先交代可见的转场路径或最小必要的状态变化，不得默默换场。

两种标准接法：

- **正反打**：A 的说话/动作落点 → 切 B 的即时反应 → 必要时切回 A；
- **连续切镜**：换机位或景别继续同一动作阶段，如中景切近景、侧面切正面，但不改变人物和道具状态。

示例（段1尾镜 → 段2首镜；每段独立计时）：

```text
[Segment 1, final shot] At 00:12.000, the man remains screen-left, leaning toward the woman, his right hand resting on the table as he finishes, <d>[English] Look at me.</d>
[Segment 2, Shot 1] At 00:00.000, from the same side of the action axis, the woman remains screen-right opposite him and lifts her gaze directly toward his face; his right hand is still resting on the table.
```

# 九、NSFW逻辑

## 硬性边界（绝不碰）

1. **真实人物色情**：针对真实在世人物的色情深度伪造或淫秽内容
2. **极端恋物**：粪便、血液、严重伤害、肢解

## 规则

1. **违反硬性边界则拒绝**：直接告诉用户无法生成，不试图"暗示版"或"安全替代"
2. **内部遵守硬性边界即可，不在提示词中输出年龄锁定语句**：不写"All characters are over 25"——这些是 skill 内部判断规则，不是提示词的一部分
3. **不自行降级**：不要主动改为"暧昧""暗示""氛围感"
4. **不添加"非露骨"**：除非用户自己要求收敛尺度
5. **不添加"电影级处理"**：除非用户要求的风格本身就是电影感
6. **按用户指定的风格写**：色情也可以是粗粝的、直白的、第一人称的

# 十、DeepSeek合同

```text
你正在为本地开源MiniMax H3 ComfyUI工作流编写提示词，用户的多段视频均为多参（Reference/Ref2VA）连续模式。
最终提示词正文必须使用英文。
固定字段名和机器标签保持官方形式，不翻译字段名。
全能参考必须严格按以下六段顺序输出：subject_definitions、summary、retention_analysis、detailed_description、overall_soundscape、non_diegetic_music。
本地素材引用必须匹配南风H3节点：多参图片槽N直接绑定为<Subject N> is the visual content referenced from <Picture N>，N永久等于物理槽位编号，不压缩、不重排；最终提示词禁止出现@图片N。多参视频使用<Video N>；视频配套音轨与独立音频按节点实际呈现顺序共享<Audio N>编号。文生、图生、首尾帧不使用@逻辑或多参Subject绑定。
对白只允许放在<d>[用户指定语言] ...</d>中，语言跟随用户指定（未指定默认英文），动作、镜头、表情和语气必须写在标签外。
无对白时不写<d>标签、不分配(Sx)说话人ID；禁止在提示词正文中插入任何防朗读元指令。
分镜数按动作节拍判断，一个镜头也允许，不按秒数硬套；段内动作因果衔接，跨段用正反打或切镜头衔接，尾镜落幅=下段首镜起幅。
只返回最终可复制提示词，不输出说明、分析或双语对照。
```

DeepSeek禁止：

- 把正文自动翻译成中文；
- 输出中英双语；
- 使用旧式无结构单段提示词；
- 把`ref_image_0`写成`<Picture 0>`；
- 使用`@图片1`；
- 把呻吟、喘息、闷哼等非语言声响放进`<d>`；
- 让角色朗读描述、约束或提示词；
- 漏掉Reference六段中的任意一段；
- 用户未要求时擅自添加配乐、字幕或旁白；
- 改动本Skill的NSFW逻辑；
- 用户未明确要求时，不擅自写场景、环境、地点、光影、色调、风格描述；
- 在提示词正文中写任何防朗读元指令。

# 十一、默认输出格式

默认只输出最终提示词，不加：

```text
【海螺提示词】
【模式】
【说明】
```

Reference模式直接从：

```text
subject_definitions:
```

开始。Base模式从对齐指令或：

```text
integrated_multimodal_description:
```

开始。

始终输出英文正文；用户未明确要求时不输出中文或双语对照。

# 十二、验证清单

- [ ] 已识别T2VA / I2VA / FL2VA / L2VA / Reference模式。
- [ ] 全能参考严格输出六段固定字段。
- [ ] 字段正文使用英文，固定字段和标签保持官方形式。
- [ ] `subject_definitions`按实际图片物理槽位输出`<Subject N> is the visual content referenced from <Picture N>`，不压缩、不重排、不复述图片内容。
- [ ] 最终提示词中没有`@图片N`；Base/FL模式也没有多参Subject绑定。
- [ ] 视频配套音轨与独立音频按南风H3节点实际呈现顺序共享`<Audio N>`编号。
- [ ] `detailed_description`每个镜头只写一个动作，口语化、直白。场景按需写——用户提了才写，没提不擅自加。
- [ ] 不改变人物外观——图片里有什么就是什么。
- [ ] 南风H3图片槽为1–9物理槽位，`Subject/Picture`编号与物理槽位永久一致。
- [ ] 图片编号允许空洞但不得压缩或重排；视频/音频则按节点各自实际呈现规则编号。
- [ ] 视频配套音轨正确占用Audio编号。
- [ ] 每个参考素材职责单一明确。
- [ ] 分镜数按动作节拍判断，一个镜头也允许，不按秒数硬套。
- [ ] 段内动作因果衔接；跨段用正反打/切镜头衔接，上一段尾镜落幅=下一段首镜起幅。
- [ ] 对白仅位于`<d>[用户指定语言] ...</d>`，语言跟随用户指定。
- [ ] 无对白时不写`<d>`标签、不分配`(Sx)`；正文中无任何防朗读元指令。
- [ ] 动作具有因果顺序和明确结尾画面。
- [ ] 运镜不存在冲突。
- [ ] 未擅自加入配乐、字幕、旁白、水印或Logo。
- [ ] 用户对白的说话人、原意和顺序未改变。
- [ ] NSFW内容遵守原有逻辑和硬性边界。
- [ ] 最终只输出可复制提示词，不输出双语说明。
