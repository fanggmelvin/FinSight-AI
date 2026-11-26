"""Normalize labeled annual amounts and preserve unidentified source units."""
import math
import pandas as pd

SCALES = {'USD dollars': 1, 'USD thousands': 1000, 'USD millions': 1000000, 'USD billions': 1000000000}
SOURCE_UNITS = "source units (unconfirmed)"


def normalize_annual(candidate, units, last_actual=None):
    if candidate.kind != 'annual' or units not in (*SCALES, SOURCE_UNITS):
        raise ValueError('Annual statement and recognized source units required.')
    frame = candidate.frame.copy()
    years = frame['Fiscal year']
    if frame.empty or years.duplicated().any():
        raise ValueError('Unique annual periods required.')
    if last_actual is not None and last_actual not in years.tolist():
        raise ValueError('Select an available fiscal year as the last actual period.')
    for metric in ('Revenue', 'COGS'):
        frame['Source ' + metric] = frame[metric]
        frame[metric] = frame[metric] * SCALES.get(units, 1)
        if not frame[metric].map(lambda x: math.isfinite(x) and x >= 0).all():
            raise ValueError('Invalid financial amount.')
    frame['Gross profit'] = frame['Revenue'] - frame['COGS']
    frame['Gross margin'] = frame['Gross profit'].div(frame['Revenue'].where(frame['Revenue'] != 0))
    frame['Period type'] = ['Unclassified' if last_actual is None else 'Actual' if y <= last_actual else 'Forecast' for y in years]
    frame['Source worksheet'] = candidate.sheet
    frame['Source units'] = units
    frame['Currency'] = 'USD' if units in SCALES else 'Unspecified'
    return frame.sort_values('Fiscal year').reset_index(drop=True)
