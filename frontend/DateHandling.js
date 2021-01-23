function zStringToDate(zString) {
    return new Date(zString).toLocaleDateString()
}

function zStringToDateTime(zString) {
    return new Date(zString).toLocaleString();
}

export {
    zStringToDate,
    zStringToDateTime
}