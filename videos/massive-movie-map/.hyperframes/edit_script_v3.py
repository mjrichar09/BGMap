"""One-off: apply the user's script changes (lines 3, 5, 8) and the 'read' respelling (line 2)."""
import pathlib

def sub(path, reps):
    p = pathlib.Path(path)
    s = p.read_text(encoding="utf-8")
    for a, b in reps:
        assert s.count(a) == 1, (path, a[:60])
        s = s.replace(a, b)
    p.write_text(s, encoding="utf-8")

OLD3 = "Nobody told it these were gangster films."
NEW3 = "No genre information was given to group these as mafia movies."
OLD5 = "Hollywood loves a sequel. In the 2010s,"
NEW5 = "What can we learn? Hollywood loves a sequel. In the 2010s,"
OLD8 = "It even finds movies nobody has made yet."
NEW8 = "Want something original? Find the spaces where nobody has made a movie yet."

sub("SCRIPT.md", [
    ("    An AI read every plot, and put similar stories side by side.", "    An AI red every plot, and put similar stories side by side."),
    (OLD3, NEW3), (OLD5, NEW5), (OLD8, NEW8),
])
sub("STORYBOARD.md", [
    (OLD3, NEW3), (OLD5, NEW5), (OLD8, NEW8),
    ('Scene 4 (6.16-8.9s): on "Nobody told it" the panel holds; on "gangster films" (7.62)',
     'Scene 4 (after "The Irishman"): on "No genre information" the panel holds; on "mafia movies"'),
    ('Scene 1 (0.0-1.62s): on "Hollywood loves a sequel"',
     'Scene 0 (on "What can we learn?"): the pile is empty; a single Courier question mark blinks on under the voice, then the first headline slams in on "Hollywood".\nScene 1 (on "Hollywood loves a sequel"):'),
    ('the eyebrow UNMADE MOVIE (red) types on top-left on "nobody has made yet".',
     'the eyebrow WANT SOMETHING ORIGINAL? (red) types on top-left with the question, then UNMADE MOVIE replaces it on "nobody has made a movie yet".'),
])
print("ok")
