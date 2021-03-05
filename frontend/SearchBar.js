import React, { useState } from "react";
import {
  dateToZString,
  dateToComponents,
  componentsToDate,
  timestampType,
  maxDateForMonth,
} from "./DateHandling";
import { Link, useHistory, useLocation } from "react-router-dom";
import LoadingSpinner from "./LoadingSpinner";
import PropTypes from "prop-types";

SearchBar.propTypes = {
  baseURL: PropTypes.string.isRequired,
  // when this is true, the search field and time travel button are disabled and the
  // only thing available is the home button
  noSearch: PropTypes.bool,
  // this is passed down to the Time Travel modal and defines the earliest and latest
  // dates that one can currently time travel to
  timeSpan: PropTypes.arrayOf(timestampType),
  // because finding the default time involves finding the middle message in a long
  // list of messages, it is not done until it needs to be done (when this prop is
  // called)
  getDefaultTime: PropTypes.func,
  placeholder: PropTypes.string.isRequired,
};

export default function SearchBar(props) {
  const history = useHistory();
  const location = useLocation();
  const alreadyHome =
    location.pathname == "/" || location.pathname == "/conversations";
  const [text, setText] = useState(location.state?.lastSearch || "");
  const receiveText = (event) => setText(event.target.value);
  const [timeTraveling, setTimeTraveling] = useState(false);
  const actOnSearch = (event) => {
    if (event.type == "click" || event.key == "Enter") {
      if (!props.noSearch && text.trim()) {
        history.push(props.baseURL + "?search=" + encodeURIComponent(text), {
          lastSearch: text,
        });
      }
    }
  };
  return (
    <div className="searchBar">
      <button
        className="homeButton"
        disabled={alreadyHome}
        onClick={() => history.push("/")}
      >
        🏠
      </button>
      <button
        disabled={props.noSearch}
        onClick={() => !props.noSearch && setTimeTraveling(true)}
        style={{ whiteSpace: "nowrap" }}
      >
        Go to date...
      </button>
      <input
        disabled={props.noSearch}
        value={text}
        onInput={receiveText}
        onKeyDown={actOnSearch}
        style={{ width: "100%" }}
        type="search"
        placeholder={props.placeholder}
      />
      <button disabled={props.noSearch} onClick={actOnSearch}>
        Search
      </button>
      {timeTraveling &&
        (props.timeSpan && props.timeSpan[0] && props.timeSpan[1] ? (
          <TimeTravelModal
            close={() => setTimeTraveling(false)}
            baseURL={props.baseURL}
            timeSpan={props.timeSpan}
            start={props.getDefaultTime && props.getDefaultTime()}
          />
        ) : (
          <div
            className="modalBackdrop"
            onClick={() => setTimeTraveling(false)}
          >
            <div className="centeredModal">
              <LoadingSpinner />
            </div>
          </div>
        ))}
    </div>
  );
}

TimeTravelModal.propTypes = {
  timeSpan: PropTypes.arrayOf(timestampType).isRequired,
  start: timestampType,
  close: PropTypes.func.isRequired,
  baseURL: PropTypes.string.isRequired,
};

function TimeTravelModal(props) {
  const history = useHistory();
  const dates = props.timeSpan.map((v) => {
    // discards data that we're not using in our components model, like seconds and
    // milliseconds
    return componentsToDate(dateToComponents(new Date(v)));
  });
  const [timeElements, setTimeElements] = useState(
    dateToComponents((props.start && new Date(props.start)) || dates[0])
  );
  const [validationWarning, setValidationWarning] = useState("");
  const elementsAreIncomplete = timeElements.some((e) => e === "");
  const [startYear, endYear] = dates.map((v) => v.getFullYear());
  const clampInt = (i, min, max) => {
    return Math.max(min, Math.min(parseInt(i), max));
  };
  const clampDate = (year, month, day) => {
    day = day || 1;
    if (year == startYear) {
      if (month <= dates[0].getMonth()) {
        month = dates[0].getMonth();
        if (day < dates[0].getDate()) {
          day = dates[0].getDate();
        }
      }
    }
    if (year == endYear) {
      if (month >= dates[1].getMonth()) {
        month = dates[1].getMonth();
        if (day >= dates[1].getDate()) {
          day = dates[1].getDate();
        }
      }
    }
    return [year, month, day];
  };
  const changeTimeElement = (value, index) => {
    const newTimeElements = [
      ...timeElements.slice(0, index),
      index == 5 || value === "" ? value : parseInt(value),
      ...timeElements.slice(index + 1),
    ];
    if (value && index < 3) {
      // auto-validate upon year and month changes, since they are chosen with select
      // inputs; the date is entered through typing so it is not validated until the
      // user is Finished.
      const [cY, cM] = clampDate(...newTimeElements.slice(0, 3));
      setTimeElements([cY, cM, ...newTimeElements.slice(2)]);
    } else {
      setTimeElements(newTimeElements);
    }
  };
  const isTimeValid = (value, min, max) =>
    value === "" || (parseInt(value) <= max && parseInt(value) >= min);
  const dayOptions = Array(maxDateForMonth(timeElements[0], timeElements[1]))
    .fill(0)
    .map((_v, i) => i + 1);
  const minDay = dayOptions.find(
    (v) => clampDate(timeElements[0], timeElements[1], v)[2] == v
  );
  dayOptions.reverse();
  const maxDay = dayOptions.find(
    (v) => clampDate(timeElements[0], timeElements[1], v)[2] == v
  );
  const validateDate = () => {
    const vDay = clampInt(timeElements[2], minDay, maxDay);
    setTimeElements([
      ...clampDate(...timeElements.slice(0, 2), vDay),
      ...timeElements.slice(3),
    ]);
  };
  const yearOptions = Array(endYear - startYear + 1)
    .fill(0)
    .map((_v, i) => {
      const y = i + startYear;
      return (
        <option key={y} value={y}>
          {y}
        </option>
      );
    });
  const monthOptions = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ].map((m, i) => (
    <option
      key={m}
      value={i}
      disabled={clampDate(timeElements[0], i, 1)[1] !== i}
    >
      {m}
    </option>
  ));
  return (
    <div className="modalBackdrop" onClick={props.close}>
      <div
        className="centeredModal"
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          width: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3>Go to:</h3>
        <span>
          <Link to={props.baseURL + "?start=" + props.timeSpan[0]}>
            The Beginning
          </Link>
          {" | "}
          <Link to={props.baseURL + "?start=" + props.timeSpan[1]}>
            The End
          </Link>
        </span>
        <p>Or enter a date and time below:</p>
        <div className="rowToColumn">
          <div className="dateSubsection">
            <div className="timeField">
              <label>Year: </label>
              <select
                value={timeElements[0]}
                onChange={(e) => changeTimeElement(e.target.value, 0)}
              >
                {yearOptions}
              </select>
            </div>
            <div className="timeField">
              <label>Month:</label>
              <select
                value={timeElements[1]}
                onChange={(e) => changeTimeElement(e.target.value, 1)}
              >
                {monthOptions}
              </select>
            </div>
            <div className="timeField">
              <label>Day:</label>
              <input
                type="number"
                min={minDay}
                max={maxDay}
                value={timeElements[2]}
                onChange={(e) => changeTimeElement(e.target.value, 2)}
                // the native onchange event will fire when the user clicks away from
                // the input field, signifying that they are done typing and their
                // input needs to be validated
                ref={(n) => n && (n.onchange = validateDate)}
              />
            </div>
          </div>
          <div className="dateSubsection">
            <div className="timeField">
              <label>Hour:</label>
              <input
                type="number"
                min={1}
                max={12}
                value={(timeElements[3] < 10 ? "0" : "") + timeElements[3]}
                onChange={(e) => {
                  isTimeValid(e.target.value, 1, 12) &&
                    changeTimeElement(e.target.value, 3);
                }}
              />
            </div>
            <div className="timeField">
              <label>Minute:</label>
              <input
                min={0}
                max={59}
                type="number"
                value={(timeElements[4] < 10 ? "0" : "") + timeElements[4]}
                onChange={(e) =>
                  isTimeValid(e.target.value, 0, 59) &&
                  changeTimeElement(e.target.value, 4)
                }
              />
            </div>
            <div className="timeField">
              <label>&nbsp;</label>
              <select
                value={timeElements[5]}
                onChange={(e) => changeTimeElement(e.target.value, 5)}
              >
                <option value="AM">AM</option>
                <option value="PM">PM</option>
              </select>
            </div>
          </div>
        </div>
        {validationWarning && (
          <span style={{ color: "darkred" }}>{validationWarning}</span>
        )}
        <div>
          <button
            onClick={() => {
              if (!elementsAreIncomplete) {
                history.push(
                  props.baseURL +
                    "?start=" +
                    dateToZString(componentsToDate(timeElements))
                );
              } else {
                setValidationWarning("Please don't leave empty boxes");
              }
            }}
            style={{ marginRight: 5 }}
          >
            Time Travel
          </button>
          <button onClick={props.close}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
