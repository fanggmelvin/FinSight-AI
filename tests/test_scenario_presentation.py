import pandas as pd
from finsight.scenario_presentation import format_value, executive_summary, resolve_scenario_followup, sensitivity

def test_format():
    assert format_value(12345.6)=='12,345.60'
    assert format_value(4.29,True,True)=='+4.29 pp'
    assert format_value(None)=='N/A'

def test_followup():
    old={'scenario':{},'question':'What if revenue increases by 10% in 2014?'}
    old['scenario']={'cases':[]}
    assert resolve_scenario_followup('What if we increase it to 15% instead?',old)==('What if revenue increases by 15% in 2014?',None)

def test_ambiguous():
    assert resolve_scenario_followup('Change it to 15%',None)[1]
    assert resolve_scenario_followup('Change it to 15%',{'scenario':{'cases':[]},'question':'10% and 5%'})[1]

def test_summary():
    assert 'increases by 5.00' in executive_summary({'Gross profit':10,'Gross margin (%)':10},{'Gross profit':15,'Gross margin (%)':15})

def test_sensitivity():
    df=pd.DataFrame({'revenue':[100.],'cogs':[80.],'date':pd.to_datetime(['2014-01-01'])})
    rows=sensitivity('What if revenue increases by 10%?',df)
    assert len(rows)==8
    assert rows[0]['Gross profit']==20
    assert not sensitivity('Target gross margin of 20%',df)
