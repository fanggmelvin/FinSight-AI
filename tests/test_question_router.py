import pytest
from finsight.question_router import route_question

MONTHS=['2013-12','2014-01','2014-09','2014-10','2014-11','2013-11']
@pytest.mark.parametrize('question,mode,dimension,previous,current',[
('Why did revenue decline in November 2014?','revenue_investigation','product','2014-10','2014-11'),
('Which products drove the October 2014 revenue increase?','revenue_investigation','product','2014-09','2014-10'),
('Compare October and November 2014 revenue by country','revenue_investigation','country','2014-10','2014-11'),
('Compare revenue by segment in 2014-10 and 2014-11','revenue_investigation','segment','2014-10','2014-11'),
('Why did sales fall in January 2014?','revenue_investigation','product','2013-12','2014-01'),
('How profitable is the company?','summary',None,None,None),
('What are our biggest financial risks?','summary',None,None,None),
('Why did revenue decline in November?','clarify',None,None,None),
('Why did revenue decline in June 2014?','clarify',None,None,None),
('Compare revenue by product and country in November 2014','multi_investigation','all','2014-10','2014-11'),
('Compare annual revenue growth in November 2014','clarify',None,None,None),
('Why did revenue fall?','clarify',None,None,None),
('Compare revenue in September, October and November 2014','clarify',None,None,None),
('Compare revenue in November 2014 and November 2013','revenue_investigation','product','2013-11','2014-11'),
])
def test_routes(question,mode,dimension,previous,current):
    result=route_question(question,MONTHS)
    assert result['mode']==mode
    if dimension:
        assert (result['dimension'],result['previous_month'],result['current_month'])==(dimension,previous,current)
