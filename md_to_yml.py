import os
import re
import yaml


PATTERN = r'^\* \[(\w+)\]\((.+)\) - (.*)'


with open('python-in-music.md') as f:
    lines = f.readlines()

p = re.compile(PATTERN)


res = []

for line in lines:
    d = {}
    m = p.match(line)
    if m:
        d['name'] = m.group(1).lower()
        d['url'] = m.group(2)
        d['desc'] = m.group(3)
        d['category'] = ''
        d['keywords'] = ''
        res.append(d)

with open('out.yml','w') as f:
    f.write(yaml.dump(res, sort_keys=False))


