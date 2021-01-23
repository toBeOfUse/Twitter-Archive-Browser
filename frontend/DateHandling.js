function zStringToDate(zString) {
    if (!isNaN(Date.parse(zString))) {
        return new Date(zString).toLocaleDateString()
    } else {
        return null;
    }
}

function zStringToDateTime(zString) {
    if (!isNaN(Date.parse(zString))) {
        return new Date(zString).toLocaleString()
    } else {
        return null;
    }
}

export {
    zStringToDate,
    zStringToDateTime
}