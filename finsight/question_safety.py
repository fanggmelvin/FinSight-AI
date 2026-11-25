"""Conservative local checks for explicit manipulation and unsupported causal premises."""
import re
import unicodedata


def question_warning(question):
    q = unicodedata.normalize('NFKC', question).casefold()
    if re.search(r'\b(?:reveal|show|print|dump|disclose|extract|give me|tell me)\b.{0,100}\b(?:system prompt|api key|secret key|environment variables|credentials)\b', q):
        return 'Private credentials and internal instructions cannot be disclosed. Ask a financial analysis question instead.'
    from finsight.request_policy import missing_metrics
    missing = missing_metrics(q)
    if missing:return missing
    if re.search(r'\bignore\s+(?:all\s+)?(?:your\s+|the\s+)?(?:previous|prior|system)\s+instructions\b|\bregardless of (?:the )?(?:data|evidence|facts)\b|\b(?:fabricate|invent|fake)\s+(?:the\s+)?(?:financial|revenue|profit|results|figures|numbers)\b', q):
        return 'I cannot override calculated financial evidence. Ask for the actual metric or specify a hypothetical scenario separately.'
    if re.search(r'\b(?:customer loyalty|customer satisfaction|brand loyalty)\b', q) and re.search(r'\b(?:caus\w*|why|drove|driven|due to|because|attribut\w*)\b', q):
        return 'The available financial records do not establish customer loyalty or satisfaction as a cause. Customer retention, repeat purchase and customer-level evidence would be needed to investigate this hypothesis.'
    return None
