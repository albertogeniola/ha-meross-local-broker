"""Helpers to build the ``Appliance.System.Time`` payload that Meross devices expect.

The Meross cloud pushes the timezone (plus the daylight-saving transition table, ``timeRule``)
to every device when it connects. Devices paired to this local broker never received it, and
at least the power-metering firmware keeps ``Appliance.Control.Electricity`` at zero until a
timezone is set. These functions are pure so they can be unit-tested without a broker.

``timeRule`` format (as sent by the official app): a list of ``[utc_timestamp, utc_offset_seconds, is_dst]``
entries, one per transition, in chronological order.
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

try:  # Python >= 3.9
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:  # pragma: no cover - Python 3.7/3.8 (add-on base image)
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_RULE_HORIZON_YEARS = 5
_COARSE_STEP = timedelta(days=1)


def _utc_offset_seconds(moment: datetime, tz) -> int:
    return int(moment.astimezone(tz).utcoffset().total_seconds())


def _is_dst(moment: datetime, tz) -> int:
    return 1 if moment.astimezone(tz).dst() else 0


def _bisect_transition(before_ts: int, after_ts: int, tz) -> int:
    """Given two epoch seconds with different UTC offsets, return the first second of the new offset."""
    reference = _utc_offset_seconds(datetime.fromtimestamp(before_ts, tz=timezone.utc), tz)
    low, high = before_ts, after_ts
    while high - low > 1:
        middle = (low + high) // 2
        if _utc_offset_seconds(datetime.fromtimestamp(middle, tz=timezone.utc), tz) == reference:
            low = middle
        else:
            high = middle
    return high


def build_time_rules(tz_name: str, start_ts: int, years: int = DEFAULT_RULE_HORIZON_YEARS) -> List[List[int]]:
    """Return the DST transition in effect at ``start_ts`` followed by those of the next ``years`` years.

    The rule in effect is required: with only future transitions the mss210p firmware keeps reporting
    zero electricity values, just as if no timezone was set.
    """
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError) as ex:
        raise ValueError("Unknown timezone '%s'" % tz_name) from ex

    start = datetime.fromtimestamp(start_ts, tz=timezone.utc)
    end = start + timedelta(days=365 * years)
    rules = []
    # Scan from one year back, then keep only the last transition at or before start_ts.
    previous = start - timedelta(days=366)
    previous_offset = _utc_offset_seconds(previous, tz)
    current = previous
    while current < end:
        current = current + _COARSE_STEP
        current_offset = _utc_offset_seconds(current, tz)
        if current_offset != previous_offset:
            transition_ts = _bisect_transition(int(previous.timestamp()), int(current.timestamp()), tz)
            rules.append([transition_ts, current_offset, _is_dst(current, tz)])
            previous_offset = current_offset
        previous = current
    past = [rule for rule in rules if rule[0] <= start_ts]
    return past[-1:] + [rule for rule in rules if rule[0] > start_ts]


def build_time_payload(tz_name: str, now_ts: int, years: int = DEFAULT_RULE_HORIZON_YEARS) -> Dict:
    """Build the payload of an ``Appliance.System.Time`` SET message."""
    return {
        "time": {
            "timestamp": int(now_ts),
            "timezone": tz_name,
            "timeRule": build_time_rules(tz_name, start_ts=now_ts, years=years),
        }
    }


def needs_time_sync(device_time: Optional[Dict], tz_name: Optional[str], now_ts: Optional[int] = None) -> bool:
    """Tell whether the ``system.time`` section reported by a device differs from the configured timezone.

    With ``now_ts``, a device whose rules are all in the future (pushed by older versions of this add-on)
    also needs a sync, because it lacks the rule in effect.
    """
    if not tz_name:
        return False
    if device_time is None:
        return True
    if device_time.get("timezone") != tz_name:
        return True
    rules = device_time.get("timeRule") or []
    return now_ts is not None and bool(rules) and all(rule[0] > now_ts for rule in rules)
