from finsight.deterministic_report import deterministic_insights

def record(name, eid, **values):
    return dict(title=name,evidence_id=eid,values=values)

def test_margin_and_concentration():
    text=deterministic_insights([record('Product: A','E001',gross_margin=.1,revenue_share=.7),record('Product: B','E002',gross_margin=.2,revenue_share=.3)])
    assert 'A had the lowest gross margin (10.00%)' in text
    assert 'A had the largest revenue share (70.00%)' in text

def test_country_drivers():
    text=deterministic_insights([record('Country: A','E001',revenue_change=-100,gross_profit_change=-2),record('Country: B','E002',revenue_change=-50,gross_profit_change=-10)])
    assert 'A had the largest negative revenue contribution' in text
    assert 'B had the largest gross profit decline' in text

def test_no_negative_driver():
    assert not deterministic_insights([record('Country: A','E001',revenue_change=100)])

def test_month_range():
    text=deterministic_insights([record('Financial Performance: 2014-01','E001',revenue=100),record('Financial Performance: 2014-02','E002',revenue=200)])
    assert '2014-01 (100.00) to 2014-02 (200.00)' in text
