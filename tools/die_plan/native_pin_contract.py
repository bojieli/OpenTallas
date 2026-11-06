"""Exact explicitly declared native pin metal, with its logical anchor retained."""
from decimal import Decimal, InvalidOperation


def _coordinate(value, dbu):
    if isinstance(value, bool):
        raise ValueError('boolean coordinate')
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError('nonfinite coordinate')
    if dbu is None:
        return number
    scaled = number * Decimal(str(dbu))
    integer = scaled.to_integral_value()
    # Numeric serialization noise only, far below one physical DBU.
    if abs(scaled-integer) > Decimal('0.000001'):
        raise ValueError('declared native geometry is off the database grid')
    return int(integer)


def _rect(box, dbu):
    if len(box) != 5 or not isinstance(box[0], str) or not box[0]:
        raise ValueError('invalid native rectangle')
    layer, *coords = box
    x0,y0,x1,y1 = [_coordinate(x, dbu) for x in coords]
    if x0 >= x1 or y0 >= y1:
        raise ValueError('empty native rectangle')
    return layer,x0,y0,x1,y1


def anchor_in_rect(pin, box, dbu=None):
    try:
        layer,x0,y0,x1,y1 = _rect(box, dbu)
        x,y = _coordinate(pin['x'], dbu),_coordinate(pin['y'], dbu)
        return layer == pin['layer'] and x0 <= x <= x1 and y0 <= y <= y1
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return False


def native_rects_match(pin, boxes, dbu=None):
    """Every exact layer/rectangle (including multiplicity), plus anchor containment.

    Names remain keyed by the audit's exact bus/bit-to-BTerm mapping. No centre
    tolerance or projected access point enters this explicit-shape path.
    """
    try:
        expected = pin['native_rects']
        if not expected or not any(anchor_in_rect(pin, r, dbu) for r in expected):
            return False
        return sorted(_rect(r, dbu) for r in expected) == sorted(_rect(r, dbu) for r in boxes)
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return False
