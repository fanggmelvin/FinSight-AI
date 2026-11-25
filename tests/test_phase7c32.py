import pandas as pd
from finsight.request_policy import named_analysis
from finsight.commentary_grounding import ranking_rows, action_diagnostic

def data():
    return pd.DataFrame(dict(segment=['Government','Small Business','Enterprise'], revenue=[44.,36.,20.], cogs=[30.,32.,22.], date=pd.to_datetime(['2014-01-01']*3)))

def test_named_share():
    assert '80.00%' in named_analysis('What percentage of our revenue comes from Government and Small Business combined?',data())

def test_named_focus():
    result=named_analysis('How can we improve Enterprise profitability?',data())
    assert '-10.00%' in result and 'Government' not in result

def test_generic_not_intercepted():
    assert named_analysis('Which products should we prioritize to improve profitability?',data()) is None

def test_revenue_ranking_no_undefined_action():
    assert ranking_rows([],dict(mode='ranking',metric='revenue',dimension='product'))==[]
    assert action_diagnostic('Review COGS',dict(metric='revenue'))
