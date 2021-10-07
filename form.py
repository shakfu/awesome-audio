import npyscreen
import model

split = lambda s: sorted(i for i in s.splitlines() if i)

TAGS = split("""
chuck
csound
dsp
fm
granular
maxmsp
midi
pd
plugin
python
sequencer
supercollider
synth
""")

class EntryForm(npyscreen.Form):
    def afterEditing(self):
        self.parentApp.setNextForm(None)

    def create(self):
        self.name = self.add(npyscreen.TitleText, name='name')
        self.url = self.add(npyscreen.TitleText, name='url')
        self.summary = self.add(npyscreen.TitleText, name='summary')
        self.description = self.add(npyscreen.MultiLineEdit, name='description', 
            max_height=4)
        self.tags = self.add(npyscreen.TitleMultiSelect, scroll_exit=True,
            max_height=-2, name='tags', values = TAGS)

class MyApplication(npyscreen.NPSAppManaged):
    def onStart(self):
        self.addForm('MAIN', EntryForm, name='New Entry')

if __name__ == '__main__':
    TestApp = MyApplication().run()


