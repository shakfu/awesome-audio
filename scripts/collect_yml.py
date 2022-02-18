import yaml

with open("research/python-in-music.yml", "r") as f:
    pim = yaml.safe_load(f.read())

with open("data/entries.yml", "r") as f:
    entries = [d for d in yaml.safe_load(f.read()) if d['name']] 

