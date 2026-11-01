/* Unit helpers derived from the objective-selection (what the values represent). */

const UNIT_BY_TYPE = {
  cost:     'GHS',
  profit:   'GHS',
  revenue:  'GHS',
  time:     'hrs',
  distance: 'km',
  other:    '',
}

/** Return the unit symbol for a value type, or '' when none applies. */
export function unitFor(objective) {
  const vt = objective?.value_type
  if (vt === 'other') return objective?.other_description || ''
  return UNIT_BY_TYPE[vt] || ''
}

/** Wrap a formatted number with its unit (currency prefix, others as suffix). */
export function withUnit(formattedNumber, unit) {
  if (!unit) return formattedNumber
  if (unit === 'GHS') return `GHS ${formattedNumber}`
  return `${formattedNumber} ${unit}`
}

/** Convenience: format a number and append its unit. */
export function fmtUnit(value, unit) {
  const num = Number(value)
  const text = num.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })
  return withUnit(text, unit)
}
