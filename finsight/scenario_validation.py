"""Conservative lexical screening, not semantic fact verification."""
import re
import unicodedata

_NUMBER = re.compile(r'\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|trillion|half|quarter|double|triple|percent|percentage points?|basis points?|dollars?|euros?)\b', re.I)
# Percentages as a generic metric name remain permissible (e.g. gross margin percentage).
_NUMBER = re.compile(_NUMBER.pattern.replace('|percentage points?', ''), re.I)
_GUARANTEE = re.compile(r'\b(?:guarantee\w*|certainly|definitely|inevitably|risk[- ]free|will always|cannot fail|ensures?)\b', re.I)
_CAUSAL = re.compile(r'\b(?:driven by|due to|because of|reflect\w*|demonstrat\w*|prov\w*|attribut\w*|indicat\w*|suggest\w*)\b[^.!?;]{0,100}\b(?:pricing power|efficien\w*|customer loyalty|market share|productivity|supplier discounts?)\b', re.I)
_NET = re.compile(r'\bnet (?:income|profit)\b\s+(?:will|would|is projected to|increases?|improves?|rises?|falls?|decreases?)\b', re.I)

def rejection_reason(text):
    text = unicodedata.normalize('NFKC', text)
    if any(c.isnumeric() or unicodedata.category(c)=='Sc' for c in text) or re.search(r'[%<>]',text) or _NUMBER.search(text):
        return 'Numerical or monetary language'
    if _GUARANTEE.search(text): return 'Guarantee language'
    if _CAUSAL.search(text): return 'Potential unsupported causal claim'
    if _NET.search(text): return 'Potential unsupported net income claim'
    return None
