import pandas as pd
import pytest
from finsight.scenario import run_scenario

@pytest.fixture
def data():
    return pd.DataFrame({'revenue':[100.,200.], 'cogs':[80.,220.], 'date':pd.to_datetime(['2014-01-01','2013-01-01'])})

@pytest.mark.parametrize('suffix',['across all reporting periods','for all reporting periods','over all reporting periods'])
def test_all_periods(data,suffix):
    q='What happens if revenue increases by 10% and COGS decreases by 5%'
    assert run_scenario(q+' '+suffix+'?',data)==run_scenario(q+'?',data)

def test_selected_scope(data):
    assert run_scenario('What if revenue increases by 10% across all reporting periods?',data.iloc[:1])['records']==1

@pytest.mark.parametrize('suffix',['in 2014 across all reporting periods','across all reporting periods and taxes fall'])
def test_reject_ambiguous_scope(data,suffix):
    with pytest.raises(ValueError):
        run_scenario('What if revenue increases by 10% '+suffix+'?',data)
