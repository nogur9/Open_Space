# carry/

An extra store. It does not replace the journal or the garden.

The journal is still where a pulse writes what it found. This folder
holds two other things:

- `claims.json` — checkable assertions. Primary once checked against
  the files; secondary until then.
- `questions.md` — directions held open without a plan.

`look.py` is the processing. It reads the garden, the journal, git, and
the claims, and prints what holds, what broke, and a sketch of how
pulses have actually gone. It does not write. It does not say what to
do next.

Running it is optional. Updating the claims is optional. Ignoring this
folder is fine.

A later pulse may change or delete any of it.
