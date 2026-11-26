import pandas as pd
from finsight.workbook_ingestion import discover_sheet

def test_annual_excludes_missing():
    raw=pd.DataFrame([['(in $ millions)',None,None],['Fiscal Year',2019,2020],['Net revenue',100,None],['Cost of goods sold',70,None]])
    c=discover_sheet('IncStat',raw)
    assert c.kind=='annual' and c.excluded==(2020,) and c.units=='USD millions'
    assert c.frame['Gross profit'].tolist()==[30]

def test_contents_rejected():
    assert discover_sheet('Contents',pd.DataFrame([['Contents','Page'],['Income statement',1]])) is None

def test_transaction():
    c=discover_sheet('Data',pd.DataFrame([['Date','Revenue','COGS'],['2024-01-01',100,70]]))
    assert c.kind=='transaction' and c.header_row==1

def test_trend_rejected():
    assert discover_sheet('IncStat (Trend)',pd.DataFrame([['Fiscal Year',2019],['Revenue',100],['COGS',70]])) is None

def test_duplicate_year_rejected():
    assert discover_sheet('Income',pd.DataFrame([['Fiscal Year',2019,2019],['Revenue',100,200],['COGS',70,80]])) is None
