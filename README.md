# open-audio

This repo aims to provide a curated guide to open-source audio and music projects.

To be included in this guide, a project must be open-source and freely available.

## Status

Currently in a data collection phase.

Entries to the guide are being added to a yaml file: [entries.yml](https://github.com/shakfu/awesome-audio/blob/main/data/entries.yml)


## Implementation Process

- Initially markdown or yml data

- Eventually store data in sqlite

- Command line interface to sqlite db for searchable database which can generate search results on-demand to console or html file.

- Also with following features:

  - Generate README.md from sqlite + jinja2 template

  - Check for broken links

  - Get activity stats via apis


## topics

Basically any open-source software related to audio, music, dsp, etc.. which is worth including.

The initial set of projects was taken from the [PythonInMusic](https://wiki.python.org/moin/PythonInMusic) page on python.org. This will be reduced as projects which are no longer active or available are removed.

The current Markdown translation of this page is [here](research/python-in-music.md).
