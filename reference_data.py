"""Versioned role-aware reference data. Names are hints, never identity proof."""
import json
from pathlib import Path
DATA = json.loads((Path(__file__).parent / 'reference/people.json').read_text())
KNOWN_JUDGES = dict(DATA['legacy_judges'])
PROSECUTOR_SURNAMES = {p['surname'].casefold() for p in DATA['magistrates'] if p['role'] in {'pm','vpo','procuratore'}}
for name in PROSECUTOR_SURNAMES:
    KNOWN_JUDGES.pop(name, None)
for person in DATA['magistrates']:
    if person['role'] not in {'pm','vpo','procuratore'}:
        KNOWN_JUDGES[person['surname'].casefold()] = person['surname']
KNOWN_JUDGES.update(DATA['canonical_surname_aliases'])
JUDGE_TYPO_MAP = dict(DATA['legacy_judge_typos'])
KNOWN_LAWYERS = set(DATA['legacy_lawyers'])
for name in DATA['colleague_names_from_studio']:
    KNOWN_LAWYERS.add(name.casefold())
    KNOWN_LAWYERS.add(name.split()[-1].casefold())
