from finsight.answer_reliability import direct_answer, requested_count, complete_plan

def record(i,name,margin,profit,share):
    return dict(evidence_id=f'E{i:03}',title='Country: '+name,category='Country Performance',values=dict(gross_margin=margin,gross_profit=profit,revenue_share=share))

def test_weakest_first():
    rows=[record(1,'A',.2,20,.8),record(2,'B',.1,10,.2)]
    text=direct_answer(rows,dict(mode='ranking',dimension='country',metric='gross_margin',ascending=True))
    assert text.index('**B:**')<text.index('**A:**') and '10.00%' in text

def test_profit_order():
    rows=[record(1,'A',.2,20,.8),record(2,'B',.3,10,.2)]
    text=direct_answer(rows,dict(mode='ranking',dimension='country',metric='gross_profit'))
    assert text.index('**A:**')<text.index('**B:**') and '20.00' in text

def test_count_fallback():
    themes=[dict(title=str(i),facts=['fact'],actions=['test']) for i in range(3)]
    assert requested_count('What are the three most important strategic changes?')==3
    plan,diagnostic=complete_plan('one',themes,3)
    assert len(plan.split('\n\n'))==3 and diagnostic
