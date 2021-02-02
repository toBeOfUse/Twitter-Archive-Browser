function zToLocaleDate(zString) {
  if (!isNaN(Date.parse(zString))) {
    return new Date(zString).toLocaleDateString();
  } else {
    return null;
  }
}

function zToLocaleDateTime(zString) {
  if (!isNaN(Date.parse(zString))) {
    return new Date(zString).toLocaleString();
  } else {
    return null;
  }
}

function zStringDiffMinutes(zString1, zString2) {
  return Math.abs(Date.parse(zString1) - Date.parse(zString2)) / 1000 / 60;
}

function dateToZString(date) {
  return date.toISOString();
}

function dateToComponents(date) {
  return [
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
    // since hours are directly displayed numerically, we want to make that number
    // human-readable, by making it in [1, 12] and introducing an AM/PM component
    date.getHours() % 12 || 12,
    date.getMinutes(),
    date.getHours() >= 12 ? "PM" : "AM",
  ];
}

function maxDateForMonth(year, month) {
  return new Date(year, month + 1, 0).getDate();
}

function componentsToDate(components) {
  // reverse of the above function; uses the same components format
  return new Date(
    components[0],
    components[1],
    // clamp date values to those valid for the current month, since date values are
    // directly input by humans who will probably not expect overflow
    Math.min(components[2], maxDateForMonth(components[0], components[1])),
    (components[3] == 12 ? 0 : components[3]) +
      (components[5] == "PM" ? 12 : 0),
    components[4]
  );
}

function clampNumber(input, lowerBound, upperBound) {
  return Math.min(Math.max(lowerBound, input), upperBound);
}

function clampDate(input, lowerBound, upperBound) {
  return new Date(
    clampNumber(input.getTime(), lowerBound.getTime(), upperBound.getTime())
  );
}

function isMonthAllowed(year, month, lowerBoundDate, upperBoundDate) {
  if (year == lowerBoundDate.getFullYear()) {
    return month >= lowerBoundDate.getMonth();
  } else if (year == upperBoundDate.getFullYear()) {
    return month <= upperBoundDate.getMonth();
  } else {
    return true;
  }
}

export {
  zToLocaleDate,
  zToLocaleDateTime,
  zStringDiffMinutes,
  dateToZString,
  dateToComponents,
  componentsToDate,
  clampDate,
  maxDateForMonth,
  isMonthAllowed,
};
