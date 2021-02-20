import React, { useState } from "react";
import {
  dateToZString,
  dateToComponents,
  clampDate,
  componentsToDate,
  maxDateForMonth,
  isMonthAllowed,
  timestampType,
} from "./DateHandling";
import { Link, useHistory, useParams, useLocation } from "react-router-dom";
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
        history.push(props.baseURL + "?search=" + text, { lastSearch: text });
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
        type="text"
        placeholder="Search all messages..."
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
  const elementsAreIncomplete = (elements) => {
    return elements.some((e) => e === "");
  };
  const substitute = (value, index) => {
    const newTimeElements = [
      ...timeElements.slice(0, index),
      value,
      ...timeElements.slice(index + 1),
    ];
    return newTimeElements;
  };
  const substituteAndClamp = (value, index) => {
    return clampDate(
      componentsToDate(substitute(value, index)),
      dates[0],
      dates[1]
    );
  };
  const changeComp = (value, index) => {
    const newTimeElements = substitute(value, index);
    if (!elementsAreIncomplete(newTimeElements)) {
      // only validate input if there are no empty fields; if the user has backspaced
      // everything in a field, we cannot validate anything, and need to leave the
      // input alone
      const clampedTimeElements = dateToComponents(
        substituteAndClamp(value, index)
      );
      setTimeElements(clampedTimeElements);
    } else {
      setTimeElements(newTimeElements);
    }
  };
  const isSubstitutionInvalid = (value, index) => {
    return (
      componentsToDate(substitute(value, index)).getTime() !==
      substituteAndClamp(value, index).getTime()
    );
  };
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
      disabled={!isMonthAllowed(timeElements[0], i, dates[0], dates[1])}
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
        <div style={{ display: "flex" }}>
          <div className="timeField">
            <label>Year: </label>
            <input
              min={dates[0].getFullYear()}
              max={dates[1].getFullYear()}
              type="number"
              value={timeElements[0]}
              onChange={(e) => changeComp(e.target.value, 0)}
            />
          </div>
          <div className="timeField">
            <label>Month:</label>
            <select
              value={timeElements[1]}
              onChange={(e) => changeComp(parseInt(e.target.value), 1)}
            >
              {monthOptions}
            </select>
          </div>
          <div className="timeField">
            <label>Day:</label>
            <input
              type="number"
              min={1}
              max={maxDateForMonth(timeElements[0], timeElements[1])}
              value={timeElements[2]}
              onChange={(e) =>
                changeComp(e.target.value && parseInt(e.target.value), 2)
              }
            />
          </div>
          <div className="timeField">
            <label>Hour:</label>
            <input
              type="number"
              min={1}
              max={12}
              value={timeElements[3]}
              onChange={(e) =>
                changeComp(e.target.value && parseInt(e.target.value), 3)
              }
            />
          </div>
          <div className="timeField">
            <label>Minute:</label>
            <input
              min={1}
              max={59}
              type="number"
              value={timeElements[4]}
              onChange={(e) =>
                changeComp(e.target.value && parseInt(e.target.value), 4)
              }
            />
          </div>
          <div className="timeField">
            <label>&nbsp;</label>
            <select
              value={timeElements[5]}
              onChange={(e) => changeComp(e.target.value, 5)}
            >
              <option disabled={isSubstitutionInvalid("AM", 5)} value="AM">
                AM
              </option>
              <option disabled={isSubstitutionInvalid("PM", 5)} value="PM">
                PM
              </option>
            </select>
          </div>
        </div>
        {validationWarning && <p>{validationWarning}</p>}
        <div>
          <button
            onClick={() => {
              if (!elementsAreIncomplete(timeElements)) {
                history.push(
                  props.baseURL +
                    "?start=" +
                    dateToZString(componentsToDate(timeElements))
                );
              } else {
                setValidationWarning("date is incomplete");
              }
            }}
            style={{ marginRight: 5 }}
          >
            Zoom
          </button>
          <button onClick={props.close}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
