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
  // takes date apart into values that can fit into form fields
  return [
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
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
    components[2],
    (components[3] == 12 ? 0 : components[3]) +
      (components[5] == "PM" ? 12 : 0),
    components[4]
  );
}

function timestampType(props, propName, componentName) {
  // used as a prop type; validates timestamp strings
  if (props[propName] === undefined) {
    return;
  }
  if (props[propName].length != 24 || isNaN(Date.parse(props[propName]))) {
    return new Error(
      `incorrect ${propName} supplied to ${componentName}; not in timestamp form`
    );
  }
}

export {
  zToLocaleDate,
  zToLocaleDateTime,
  zStringDiffMinutes,
  dateToZString,
  dateToComponents,
  componentsToDate,
  maxDateForMonth,
  timestampType,
};
