import yaml

with open("data/entries.yml") as f:
    entries = yaml.load(f, Loader=yaml.CLoader)

# print(data)

entries = [e for e in entries if e['name']]

sorted_entries = sorted(entries, key=lambda x: x['name'])

# for entry in sorted_entries:
#     print(entry['name'])

with open('/tmp/_sorted_entries.yml', 'w') as f:
    yaml.dump(sorted_entries, stream=f, sort_keys=False, indent=2)

with open("/tmp/_sorted_entries.yml") as f:
    entries = yaml.load(f, Loader=yaml.CLoader)

with open('data/entries_sorted.yml', 'w+') as f:
    for entry in entries:
        f.write(yaml.dump([entry], sort_keys=False, indent=2))
        f.write("\n")

print("sorted", len(entries), "entries")
