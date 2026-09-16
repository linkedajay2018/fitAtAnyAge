"""Metric<->imperial conversion and display formatting for the numbers on
the Diet Plan page. content.py stores only metric values (kg, L) — that's
the single source of truth; imperial figures are derived here at render
time rather than duplicated as separate translatable strings in content.py.

The BMI calculator (tools.html/script.js) is handled separately: it's a
client-side calculator, so unit_system there just picks which set of
input fields to render server-side (see app.py's tools() route) — the
math itself runs in script.js using the standard imperial BMI formula
rather than converting inputs to metric first.
"""

from flask_babel import gettext as _

KG_PER_LB = 0.45359237
L_PER_FL_OZ = 0.0295735296


def _fmt(value):
    """Trim a trailing .0 without losing a real decimal (2.5 -> '2.5', 3.0 -> '3')."""
    return f"{value:g}"


def format_protein_target(low_kg_per_kg, high_kg_per_kg, unit_system):
    if unit_system == "imperial":
        low = low_kg_per_kg * KG_PER_LB
        high = high_kg_per_kg * KG_PER_LB
        return _("%(low)s–%(high)s g per lb of bodyweight", low=f"{low:.1f}", high=f"{high:.1f}")
    return _(
        "%(low)s–%(high)s g per kg of bodyweight",
        low=_fmt(low_kg_per_kg),
        high=_fmt(high_kg_per_kg),
    )


def format_hydration_target(low_l, high_l, unit_system, note=None):
    if unit_system == "imperial":
        low = round(low_l / L_PER_FL_OZ)
        high = round(high_l / L_PER_FL_OZ)
        base = _("%(low)s–%(high)s fl oz per day", low=low, high=high)
    else:
        base = _("%(low)s–%(high)s L per day", low=_fmt(low_l), high=_fmt(high_l))
    if note:
        return f"{base} {note}"
    return base


def kg_to_lb(kg):
    return kg / KG_PER_LB


def lb_to_kg(lb):
    return lb * KG_PER_LB


def format_weight(weight_kg, unit_system):
    """Display-only formatting for a stored (always-metric) weight — used
    by Exercise History. `weight_kg` may be None (weight wasn't logged for
    that entry, e.g. a bodyweight or cardio exercise)."""
    if weight_kg is None:
        return None
    if unit_system == "imperial":
        return _("%(weight)s lb", weight=_fmt(round(kg_to_lb(weight_kg), 1)))
    return _("%(weight)s kg", weight=_fmt(round(weight_kg, 1)))
