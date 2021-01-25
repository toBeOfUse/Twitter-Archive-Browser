function zStringToDate(zString) {
  if (!isNaN(Date.parse(zString))) {
    return new Date(zString).toLocaleDateString();
  } else {
    return null;
  }
}

function zStringToDateTime(zString) {
  if (!isNaN(Date.parse(zString))) {
    return new Date(zString).toLocaleString();
  } else {
    return null;
  }
}

function zStringDiffMinutes(zString1, zString2) {
  return Math.abs(Date.parse(zString1) - Date.parse(zString2)) / 1000 / 60;
}

export { zStringToDate, zStringToDateTime, zStringDiffMinutes };
