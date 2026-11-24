from question_router import route_question
from deterministic_report import deterministic_insights
M=['2014-09','2014-10','2014-11']
def test_multi():
    r=route_question('Why did revenue decline in November 2014? Analyze product, country, and segment contributions.',M)
    assert (r['mode'],r['dimension'],r['previous_month'],r['current_month'])==('multi_investigation','all','2014-10','2014-11')
def test_concentration():
    assert route_question('Rank business segments by revenue concentration in 2014. Identify risks, evaluate segment profitability.',M)['metric']=='revenue_share'
def test_growth():
    assert route_question('Which products drove the revenue increase between September and October 2014?',M)['direction']=='growth'
def test_growth_insights():
    rows=[dict(title='Product: A',evidence_id='E001',values=dict(revenue_change=100,gross_profit_change=5,previous_revenue=100,current_revenue=200,previous_gross_profit=20,current_gross_profit=25)),dict(title='Product: B',evidence_id='E002',values=dict(revenue_change=-10,gross_profit_change=-2))]
    text=deterministic_insights(rows,'growth')
    assert 'largest positive revenue contribution' in text and 'largest negative revenue contribution' in text and '20.00% to 12.50%' in text

def test_combined():
    rows=[dict(title='Segment: A',evidence_id='E001',values=dict(revenue_share=.427)),dict(title='Segment: B',evidence_id='E002',values=dict(revenue_share=.3693))]
    assert '79.63%' in deterministic_insights(rows)
