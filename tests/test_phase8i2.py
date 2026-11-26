import pandas as pd
import pytest
from finsight.workbook_ingestion import discover_sheet
from finsight.statement_normalization import normalize_annual

def candidate():
    return discover_sheet('Income', pd.DataFrame([['(in $ millions)',None,None],['Fiscal Year',2019,2020],['Revenue',100,0],['COGS',70,10]]))

def test_scale():
    f=normalize_annual(candidate(),'USD millions',2019)
    assert f.Revenue.tolist()==[100000000,0]
    assert f['Gross profit'].tolist()==[30000000,-10000000]

def test_classification():
    assert normalize_annual(candidate(),'USD dollars',2019)['Period type'].tolist()==['Actual','Forecast']

def test_unknown():
    assert normalize_annual(candidate(),'USD dollars')['Period type'].tolist()==['Unclassified']*2

def test_zero_margin():
    assert pd.isna(normalize_annual(candidate(),'USD dollars')['Gross margin'].iloc[1])

def test_provenance():
    f=normalize_annual(candidate(),'USD thousands')
    assert f['Source Revenue'].tolist()==[100,0] and f['Source worksheet'].tolist()==['Income']*2
    assert f['Revenue cell'].iloc[0]=='row 3, column 2'

def test_invalid_units():
    with pytest.raises(ValueError): normalize_annual(candidate(),'unknown')

def test_invalid_cutoff():
    with pytest.raises(ValueError): normalize_annual(candidate(),'USD dollars',2018)
