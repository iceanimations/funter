import os
import re
import pymel.core as pc


__all__ = ['get_first_keyframe', 'getmax']


def get_first_keyframe(node, ignore_top_node=False):
    queue = list()
    if ignore_top_node:
        queue.extend(node.getChildren())
    else:
        queue.insert(0, node)
    while queue:
        node = queue.pop()
        keyframe = pc.keyframe(node, q=True)
        if keyframe:
            return keyframe[0]
        for child in node.getChildren():
            queue.insert(0, child)


def getmax(path):
    dirname, basename = os.path.split(path)
    match = re.match(r'(.*)\.(\d+|#+)\.rs', basename)
    _max = -1

    if match:
        basename = match.group(1)
        frames = match.group(2)
        new_re = r'\.'.join([basename, '(' + r'\d' * len(frames) + ')'])
    else:
        return _max

    for filename in os.listdir(dirname):
        match = re.match(new_re, filename)
        if match:
            num = int(match.group(1))
            if num > _max:
                _max = num

    return _max


