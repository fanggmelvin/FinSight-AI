"""Local interactive controls backed by the existing scenario engine."""
import math
from finsight.scenario import run_scenario


def simulate_controls(df, revenue=0, cogs=0, proportional=False):
    for value in (revenue, cogs):
        if not math.isfinite(value) or not -100 <= value <= 50:
            raise ValueError('Adjustments must be between -100% and 50%.')
    effective = ((1 + revenue / 100) * (1 + cogs / 100) - 1) * 100 if proportional else cogs
    def clause(metric, value):
        return f'{metric} {"increases" if value >= 0 else "decreases"} by {abs(value):.10f}%'
    return run_scenario(clause('revenue', revenue) + ' and ' + clause('COGS', effective), df)


def target_controls(df, target):
    if not math.isfinite(target) or not 0 <= target < 100:
        raise ValueError('Target margin must be at least zero and below 100%.')
    return run_scenario(f'Target gross margin of {target:.10f}%', df)
