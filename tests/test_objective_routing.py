import pytest
from finsight.question_router import route_question

@pytest.mark.parametrize('question,dimension,metric,ascending,objective',[
 ('Which products should I prioritize to maximize gross profit, and why?', 'product','gross_profit',False,'profitability'),
 ('Which countries have the lowest gross profit?', 'country','gross_profit',True,'profitability'),
 ('How should I diversify my customer segments while maintaining profitability?', 'segment','gross_margin',False,'diversification'),
 ('Which products have the highest revenue?', 'product','revenue',False,'revenue'),
 ('Which products have the weakest gross margins?', 'product','gross_margin',True,'profitability'),
])
def test_objective_route(question,dimension,metric,ascending,objective):
    route=route_question(question,['2014-10','2014-11'])
    assert (route['mode'],route['dimension'],route['metric'],route['ascending'],route['objective']) == ('ranking',dimension,metric,ascending,objective)
