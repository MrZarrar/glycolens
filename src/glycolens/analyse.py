from glycolens import basal, behaviour, corrections, meals
from glycolens.findings import Finding
from glycolens.model import Data
from glycolens.series import Series


def analyse(data: Data, windows) -> list[Finding]:
    series = Series(data.glucose)
    ms = meals.meals(data, series, windows)
    return [
        *meals.carb_ratio(ms),
        *meals.pre_bolus(ms),
        *corrections.isf(data, series, windows),
        *basal.basal(data, series, windows),
        *behaviour.exercise_low(data, series),
        *behaviour.site_age(data, series),
    ]
