"""Isolated annual reporting; never feed annual records to monthly engines."""
import pandas as pd
import numpy as np
from decimal import Decimal, ROUND_HALF_UP
import plotly.graph_objects as go


def annual_actuals(frame):
    required = {'Fiscal year','Period type','Revenue','COGS','Currency'}
    if not required.issubset(frame.columns) or frame.empty or frame['Fiscal year'].duplicated().any():
        raise ValueError('Unique classified annual records required.')
    if not frame['Period type'].isin(['Actual','Forecast']).all() or not frame['Currency'].eq('USD').all():
        raise ValueError('Confirm period classification and USD units.')
    if not np.isfinite(frame[['Revenue','COGS']].to_numpy(dtype=float)).all() or (frame[['Revenue','COGS']] < 0).any().any():
        raise ValueError('Invalid annual financial values.')
    actual = frame.loc[frame['Period type'].eq('Actual')]
    if actual.empty:
        raise ValueError('At least one actual period is required.')
    return annual_growth(actual)


def annual_growth(periods):
    actual = periods.sort_values('Fiscal year').copy()
    actual['Gross profit'] = actual['Revenue'] - actual['COGS']
    actual['Gross margin'] = actual['Gross profit'].div(actual['Revenue'].replace(0,np.nan))
    prior = actual['Revenue'].shift().replace(0,np.nan)
    actual['Revenue YoY'] = (actual['Revenue'].div(prior)-1).where(actual['Fiscal year'].diff().eq(1))
    for metric in ['COGS','Gross profit']:
        prior = actual[metric].shift()
        actual[metric+' YoY'] = (actual[metric].div(prior.where(prior > 0))-1).where(actual['Fiscal year'].diff().eq(1))
    return actual


def annual_state(frame, name, sheet, identity):
    if frame['Period type'].eq('Unclassified').all():
        periods = annual_growth(frame)
    elif frame['Currency'].eq('USD').all():
        periods = annual_actuals(frame)
    else:
        periods = annual_growth(frame.loc[frame['Period type'].eq('Actual')])
    return {'annual_data': frame.copy(), 'financial_data': periods, 'validated_data': periods,
            'file_name': name, 'sheet_name': sheet, 'dataset_id': identity, 'scenario_demo_source': False}


def compact_money(value):
    sign = '-' if value < 0 else ''
    magnitude = abs(value)
    for scale, suffix in [(1e12,'T'),(1e9,'B'),(1e6,'M'),(1e3,'K')]:
        if magnitude >= scale:
            rounded = (Decimal(str(magnitude))/Decimal(str(scale))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            return f'{sign}${rounded:,.2f}{suffix}'
    return f'{sign}${magnitude:,.2f}'


def money_axis(fig, values):
    magnitude = float(np.max(np.abs(values)))
    for scale, suffix in [(1e12,'T'),(1e9,'B'),(1e6,'M'),(1e3,'K')]:
        if magnitude >= scale:
            fig.update_yaxes(tickprefix='$', tickformat='~s')
            # Plotly SI uses G for billions; explicit ticks retain financial notation.
            step = scale * max(1, int(np.ceil(magnitude / scale / 5)))
            ticks = np.arange(np.floor(min(0,float(np.min(values)))/step)*step, magnitude+step, step)
            fig.update_yaxes(tickmode='array', tickvals=ticks.tolist(), ticktext=[f'${v/scale:g}{suffix}' if v else '$0' for v in ticks])
            break


def annual_variance(actual, year):
    current = actual.loc[actual['Fiscal year'].eq(year)].iloc[0]
    previous = actual.loc[actual['Fiscal year'].eq(year-1)]
    if previous.empty:
        return None
    prior = previous.iloc[0]
    return {k: float(current[k]-prior[k]) for k in ['Revenue','COGS','Gross profit','Gross margin']}


def annual_cagr(actual, metric):
    first, last = actual.iloc[0], actual.iloc[-1]
    years = int(last['Fiscal year']-first['Fiscal year'])
    return (last[metric]/first[metric])**(1/years)-1 if years>0 and first[metric]>0 and last[metric]>=0 else np.nan


def growth_figure(actual):
    fig = go.Figure()
    for k,color in [('Revenue','#426E9B'),('COGS','#64748B'),('Gross profit','#16967A')]:
        fig.add_scatter(x=actual['Fiscal year'].astype(str).tolist(), y=actual[k+' YoY'].tolist(), name=k, mode='lines+markers', line=dict(color=color), connectgaps=False, hovertemplate='%{x}: %{y:.2%}<extra></extra>')
    fig.update_yaxes(tickformat='.2%', title='Year-over-year growth')
    fig.update_xaxes(type='category',tickangle=0)
    fig.update_layout(height=320,legend=dict(orientation='h',y=-.2))
    return fig


def annual_figures(actual):
    years = actual['Fiscal year'].astype(str).tolist()
    usd = 'Currency' not in actual or actual['Currency'].eq('USD').all()
    bars = go.Figure()
    for metric, color in [('Revenue','#426E9B'),('COGS','#64748B'),('Gross profit','#16967A')]:
        bars.add_bar(x=years, y=actual[metric].tolist(), name=metric, marker_color=color,
                     hovertemplate='%{x}<br>'+metric+(': $' if usd else ': ')+'%{y:,.2f}<extra></extra>')
    bars.update_layout(barmode='group', yaxis=dict(title='USD' if usd else 'Source units', tickformat=',.0f',
                                                  tickprefix='$' if usd else ''))
    if usd:
        money_axis(bars, actual[['Revenue','COGS','Gross profit']].to_numpy())
    margin = go.Figure(go.Scatter(x=years, y=actual['Gross margin'].tolist(), mode='lines+markers',
        line=dict(color='#16967A',width=3), marker=dict(size=8), connectgaps=False,
        hovertemplate='FY%{x}<br>Gross margin: %{y:.2%}<extra></extra>'))
    margin.update_yaxes(tickformat='.1%', title='Gross margin', dtick=0.001 if actual['Gross margin'].max()-actual['Gross margin'].min() < .01 else None)
    for fig in (bars, margin):
        fig.update_xaxes(type='category', categoryorder='array', categoryarray=years, tickangle=0, title=None)
        fig.update_layout(height=320, margin=dict(l=12,r=12,t=15,b=12),
                          paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                          legend=dict(orientation='h',y=-0.2))
    return bars, margin


def render_annual(st, page, state):
    actual = state['validated_data']
    unclassified = actual['Period type'].eq('Unclassified').all()
    usd = actual['Currency'].eq('USD').all()
    units = 'USD' if usd else 'source units'
    periods_label = 'Annual workbook periods' if unclassified else 'Annual actuals'
    st.title(page if page != 'Overview' else 'Financial overview')
    st.caption(f"{periods_label} · {len(actual)} fiscal years · {state['file_name']} | {state['sheet_name']} · {units}")
    if unclassified:
        st.info('Fiscal years are shown as entered because actuals and forecasts are not fully identified.')
    year = st.selectbox('Fiscal year', actual['Fiscal year'].tolist(), index=len(actual)-1, key='annual_year_'+state['dataset_id']+'_'+page)
    row = actual.loc[actual['Fiscal year'].eq(year)].iloc[0]
    def money(x): return f'${x:,.0f}' if usd else f'{x:,.2f}'
    def amount(x): return compact_money(x) if usd else money(x)
    def pct(x): return 'N/A' if pd.isna(x) else f'{x:.2%}'
    def metrics(r):
        for col, key in zip(st.columns(4), ['Revenue','COGS','Gross profit','Gross margin']):
            col.metric(key, pct(r[key]) if key == 'Gross margin' else amount(r[key]))
    variance = annual_variance(actual, year)
    if page == 'Overview':
        metrics(row)
        st.caption(f'FY{year} revenue growth: {pct(row["Revenue YoY"])}')
        bars, margin = annual_figures(actual)
        st.subheader('Annual financial performance'); st.plotly_chart(bars, width='stretch')
        st.subheader('Executive highlights')
        if variance is None:
            st.info('No consecutive prior fiscal year for comparison.')
        else:
            st.write(f'Revenue change: {amount(variance["Revenue"])}; gross profit change: {amount(variance["Gross profit"])}.')
            st.write(f'Gross margin change: {variance["Gross margin"]*100:+.2f} percentage points.' if pd.notna(variance['Gross margin']) else 'Gross margin comparison unavailable.')
            if pd.notna(row['Revenue YoY']) and pd.notna(row['COGS YoY']) and row['COGS YoY'] > row['Revenue YoY']:
                st.write('COGS growth exceeded revenue growth in the selected fiscal year.')
    elif page == 'Financial Analysis':
        st.caption('Growth metrics cover the displayed fiscal years. Variance uses the selected year.')
        first,last = actual.iloc[0],actual.iloc[-1]
        cols = st.columns(4)
        cols[0].metric('Revenue CAGR',pct(annual_cagr(actual,'Revenue')))
        cols[1].metric('Total revenue growth',pct(last['Revenue']/first['Revenue']-1) if first['Revenue']>0 and len(actual)>1 else 'N/A')
        cols[2].metric('Gross profit CAGR',pct(annual_cagr(actual,'Gross profit')))
        cols[3].metric('Peak gross margin',pct(actual['Gross margin'].max()))
        st.subheader('Year-over-year growth'); st.plotly_chart(growth_figure(actual),width='stretch')
        _,margin = annual_figures(actual)
        st.subheader('Annual gross margin'); st.plotly_chart(margin,width='stretch')
        st.subheader(f'FY{year} variance analysis')
        if variance is None: st.info('No consecutive prior fiscal year for comparison.')
        else:
            st.dataframe(pd.DataFrame([{'Metric':k,'Change':f'{v*100:+.2f} pp' if k=='Gross margin' and pd.notna(v) else ('N/A' if pd.isna(v) else amount(v)), 'YoY':pct(row[k+' YoY']) if k!='Gross margin' else 'N/A'} for k,v in variance.items()]),hide_index=True)
        table=actual[['Fiscal year','Revenue','COGS','Gross profit','Gross margin','Revenue YoY','COGS YoY','Gross profit YoY']].copy()
        for k in ['Gross margin','Revenue YoY','COGS YoY','Gross profit YoY']: table[k]=table[k].map(pct)
        st.dataframe(table, hide_index=True, column_config={k:st.column_config.NumberColumn(format='dollar') for k in ['Revenue','COGS','Gross profit']} if usd else None)
    elif page == 'Scenario Modeling':
        st.caption('Hypothetical changes to the selected fiscal year.')
        rev = st.slider('Revenue change (%)', -100,100,0); cost = st.slider('COGS change (%)',-100,100,0)
        r = row['Revenue']*(1+rev/100); c = row['COGS']*(1+cost/100)
        metrics({'Revenue':r,'COGS':c,'Gross profit':r-c,'Gross margin':(r-c)/r if r else np.nan})
    elif page == 'Financial Reports':
        metrics(row)
        report = f"# Annual financial report — FY{year}\n\nSource: {state['file_name']} | {state['sheet_name']}\n\nPeriod classification: {row['Period type']}\n\nMonetary units: {units}\n\n" + '\n'.join(f'- {k}: {money(row[k])}' for k in ['Revenue','COGS','Gross profit']) + f'\n- Gross margin: {pct(row["Gross margin"])}\n- Revenue YoY: {pct(row["Revenue YoY"])}\n'
        st.markdown(report); st.download_button('Download annual report',report,file_name='annual_report.md')
    elif page == 'Anomaly Detection':
        st.info('Annual growth comparisons only; insufficient basis for automated monthly anomaly detection.')
        st.dataframe(actual[['Fiscal year','Revenue YoY']],hide_index=True,column_config={'Revenue YoY':st.column_config.NumberColumn(format='percent')})
    elif page == 'Performance Drivers':
        st.info('Product, segment and country dimensions are unavailable. This is an accounting contribution bridge, not a causal analysis.')
        if variance is None: st.info('No consecutive prior fiscal year for comparison.')
        else:
            st.subheader(f'FY{year} gross profit change')
            st.dataframe(pd.DataFrame({'Contribution':['Revenue change','COGS change (inverse)','Net gross profit change'],units:[variance['Revenue'],-variance['COGS'],variance['Gross profit']]}),hide_index=True,column_config={units:st.column_config.NumberColumn(format='dollar')} if usd else None)
    else:
        st.info('Conversational Copilot is not yet enabled for annual statements. No AI request was sent.')
    with st.expander('Source evidence'):
        st.dataframe(state['annual_data'],hide_index=True)
