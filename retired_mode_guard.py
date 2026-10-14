"""Reject obsolete workflow inputs; contains no retired feature implementation."""
RETIRED_FIELDS = frozenset({
    '空5分钟时间轴V2模式', '空5分钟V2关键帧', '空5分钟V2当前分镜关键帧',
    '波形V3模式', '波形V3关键帧', '波形V3当前分镜关键帧', '任意帧模式', '任意帧关键帧',
    'timeline_v2', 'timeline_v3', 'timed_guides', 'arbitrary_guides',
})
def reject_retired_fields(payload):
    for key in RETIRED_FIELDS.intersection(payload):
        value = payload[key]
        if value not in (None, False, '', '[]', '{}', 0) and value != [] and value != {}:
            raise ValueError(f'V15精简版已移除此旧功能参数：{key}。请使用V16原功能，或新建V15分镜；不自动转换旧模式。')
