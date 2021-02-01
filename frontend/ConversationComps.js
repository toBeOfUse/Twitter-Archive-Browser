import React, { useEffect, useState, useRef } from "react";
import { zStringToDate, zStringToDateTime } from "./DateHandling";
import { NicknameSetter } from "./UserComps";
import { Link, useHistory, useParams, useLocation } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";

function ConversationListing(props) {
  console.assert(props.schema == "Conversation");
  return (
    <div className="conversationListing">
      <img className="conversationImage" src={props.image_url} />
      <Link
        to={"/conversation/messages/" + props.id}
        className="conversationName"
      >
        {props.name}
      </Link>
      <span className="conversationDate">
        {`${zStringToDate(props.first_time)}`}
        <br />
        {`${zStringToDate(props.last_time)}`}
      </span>
      <Link to={"/conversation/info/" + props.id}>
        <img className="conversationInfoIcon" src="/assets/svg/info.svg" />
      </Link>
    </div>
  );
}

function NotesSetter(props) {
  const [notes, setNotes] = useState(props.notes);
  const [editing, setEditing] = useState(!props.notes);

  const editNotes = (event) => {
    setNotes(event.target.value);
  };

  const startEditing = () => {
    setEditing(true);
  };

  const saveNotes = () => {
    fetch("/api/conversation/notes?id=" + props.id, {
      method: "POST",
      headers: {
        "Content-Type": "text/plain",
      },
      body: notes,
    }).then(() => {
      props.changed(notes);
    });
  };

  return editing ? (
    <div style={{ width: "90%", textAlign: "center", margin: "10px 0 15px 0" }}>
      Set conversation notes:
      <textarea className="notesEntry" onChange={editNotes} value={notes} />
      <button onClick={saveNotes}>Save</button>
    </div>
  ) : (
    <p>
      Notes for this conversation: {props.notes + " "}
      <span className="smallButton" onClick={startEditing}>
        (edit)
      </span>
    </p>
  );
}

function SimpleNameUpdate(update) {
  const users = useSelector((state) => state.users);
  return (
    <p key={update.update_time}>
      {update.new_name + " (set by "}
      <Link to={"/user/info/" + update.initiator}>
        @{users[update.initiator]?.handle}
      </Link>
      {") "}
      on{" "}
      <Link
        to={
          "/conversation/messages/" +
          update.conversation +
          "?start=" +
          update.update_time
        }
      >
        {zStringToDateTime(update.update_time)}
      </Link>
    </p>
  );
}

function SimpleParticipantListing(participant) {
  return (
    <p key={participant.handle}>
      <Link to={"/user/info/" + participant.id}>
        {(participant.nickname ? participant.nickname + " - " : "") +
          participant.display_name +
          " (@" +
          participant.handle +
          ")"}
      </Link>
      {" | sent " +
        participant.messages_in_conversation.toLocaleString() +
        " messages | " +
        (participant.is_main_user
          ? "is You"
          : "in conversation from " +
            (zStringToDate(participant.join_time) || "before you") +
            " to " +
            (zStringToDate(participant.leave_time) || "now"))}
    </p>
  );
}

/* a unified one-way scrolly pane component would have: a url prop OR a function
propr that created a url from a page number; an onMoreStuffLoaded prop that would
take care of things like saving users and maybe return the actual items; a component
to render each loaded item */

function ScrollyPane(props) {
  const contentPane = useRef(null);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);

  const renderedItems = items.length ? (
    items.map((item) => (
      <props.ItemShape key={item.id} {...item}></props.ItemShape>
    ))
  ) : (
    <p>loading...</p>
  );

  const scrollCheck = () => {
    const el = contentPane.current;
    if (
      el &&
      (el.scrollHeight < el.parentElement.scrollHeight ||
        el.scrollTop + el.offsetHeight > el.scrollHeight - 30) &&
      page != -1 &&
      !loading
    ) {
      setLoading(true);

      fetch(props.url + page).then((r) =>
        r.json().then((j) => {
          const processedItems = props.processItems(j);
          setItems((oldItems) => oldItems.concat(processedItems));
          if (!processedItems.length) {
            setPage(-1);
          } else {
            setPage((prevPage) => (prevPage == -1 ? prevPage : prevPage + 1));
          }
          setLoading(false);
        })
      );
    }
  };

  useEffect(scrollCheck);

  return (
    <div
      className={props.className}
      id={props.id}
      onScroll={scrollCheck}
      ref={contentPane}
    >
      {renderedItems}
    </div>
  );
}

function ConversationInfo() {
  const { id } = useParams();
  const [info, setInfo] = useState(null);

  const dispatch = useDispatch();

  if (!info) {
    fetch("/api/conversation?id=" + id).then((r) =>
      r.json().then((result) => setInfo(result))
    );
  }

  const acceptChange = () => {
    setInfo(null);
  };

  const [metaInfoShown, setMetaInfoShown] = useState("names");
  // only applies to name updates
  const [metaInfoOrder, setMetaInfoOrder] = useState("oldest");
  const showingNames = metaInfoShown == "names";
  const showingParticipants = metaInfoShown == "participants";
  console.assert(
    showingNames || showingParticipants,
    "invalid value for metaInfoShown in ConversationInfo"
  );

  const metaInfoURL = showingNames
    ? `/api/conversation/names?conversation=${id}&first=${metaInfoOrder}&page=`
    : `/api/users?conversation=${id}&page=`;

  const processMetaInfo = (info) => {
    if (info.users?.length) {
      dispatch({ type: "users/addUsers", payload: info.users });
    }
    return info.results;
  };

  return !info ? (
    <p>loading...</p>
  ) : (
    <>
      <div className="centeredFlexHeading rowToColumn">
        <div className="centeredFlexHeading">
          <img className="infoPageImage" src={info.image_url} />
          <h1>Conversation Info</h1>
        </div>
        <span className="infoPageLinks">
          <Link to={"/conversation/messages/" + info.id}>View Messages</Link>
          <br className="noMobile" />
          <span className="onlyMobile"> | </span>
          <span>Share Conversation</span>
        </span>
      </div>

      {info.type == "group" ? (
        <h3>{'"' + info.name + '"'}</h3>
      ) : (
        <h3>
          Conversation with{" "}
          <Link to={"/user/info/" + info.other_person.id}>{info.name}</Link>
          {" | "}
          {zStringToDate(info.first_time)} - {zStringToDate(info.last_time)}
        </h3>
      )}
      <div className="statsRow">
        <div className="statsContainer">
          <p>Number of Messages</p>
          <h3>{info.number_of_messages.toLocaleString()}</h3>
        </div>
        <div className="verticalLine" />
        <div className="statsContainer">
          <p>Messages from you</p>
          <h3>{info.messages_from_you.toLocaleString()}</h3>
        </div>
        {info.type == "group" && (
          <>
            <div className="verticalLine" />
            <div className="statsContainer">
              <p>Number of name changes</p>
              <h3>{info.num_name_updates.toLocaleString()}</h3>
            </div>
            <div className="verticalLine" />
            <div className="statsContainer">
              <p>Number of participants</p>
              <h3>{info.num_participants.toLocaleString()}</h3>
            </div>
          </>
        )}
      </div>
      {info.type != "group" && (
        <NicknameSetter changed={acceptChange} {...info.other_person} />
      )}
      <NotesSetter changed={acceptChange} notes={info.notes} id={info.id} />
      {info.type == "group" && (
        <>
          <span>
            <span
              onClick={() => setMetaInfoShown("names")}
              className="smallButton"
              style={{ color: showingParticipants ? "blue" : "black" }}
            >
              {showingNames
                ? "Currently Viewing Name Updates"
                : "Switch to Name Updates"}
            </span>
            {" | "}
            <span
              onClick={() => setMetaInfoShown("participants")}
              className="smallButton"
              style={{ color: showingNames ? "blue" : "black" }}
            >
              {showingParticipants
                ? "Currently Viewing Participants"
                : "Switch to Participants"}
            </span>
          </span>
          {showingNames && (
            <>
              <br />
              <span>
                <label
                  style={{ marginRight: 10 }}
                >
                  <input
                    type="radio"
                    checked={metaInfoOrder == "oldest"}
                    style={{ marginRight: 5 }}
                    onClick={() => setMetaInfoOrder("oldest")}
                  />
                  Oldest first
                </label>
                <label>
                  <input
                    type="radio"
                    onClick={() => setMetaInfoOrder("newest")}
                    checked={metaInfoOrder == "newest"}
                    style={{ marginRight: 5 }}
                  />
                  Newest first
                </label>
              </span>
            </>
          )}
          <ScrollyPane
            className="metaInfoContainer"
            key={metaInfoURL}
            url={metaInfoURL}
            ItemShape={
              showingNames ? SimpleNameUpdate : SimpleParticipantListing
            }
            processItems={processMetaInfo}
          />
        </>
      )}
    </>
  );
}

function ConversationList() {
  const [order, setOrder] = useState(
    localStorage.getItem("conversationOrder") || "oldest"
  );
  const [types, setTypes] = useState(
    JSON.parse(localStorage.getItem("conversationTypes")) || {
      group: true,
      individual: true,
    }
  );

  const dispatch = useDispatch();

  const resetButton = () => {
    setConversations([]);
  };

  const changeOrder = (event) => {
    setOrder(event.target.value);
    localStorage.setItem("conversationOrder", event.target.value);
    resetButton();
  };

  const changeTypes = (event) => {
    setTypes((prevTypes) => {
      const newTypes = {
        ...prevTypes,
        ...{ [event.target.name]: event.target.checked },
      };
      localStorage.setItem("conversationTypes", JSON.stringify(newTypes));
      return newTypes;
    });
    resetButton();
  };

  const typesString = Object.keys(types)
    .filter((v) => types[v])
    .join("-");
  const url =
    `/api/conversations?` + `first=${order}&types=${typesString}&page=`;

  const processConversations = (j) => {
    dispatch({
      type: "conversations/addConversations",
      payload: j.results,
    });
    return j.results;
  };

  return (
    <>
      <div id="conversationHeader">
        <div style={{ display: "flex", alignItems: "center" }}>
          <h1 style={{ marginRight: 10 }}>Conversations</h1>
          <Link to="/stats" style={{ marginRight: 5 }}>
            (stats)
          </Link>
          <Link to="/messages">(view all messages)</Link>
        </div>
        <div>
          <span>Sort by:</span>
          <select
            id="conversationOrderSelect"
            value={order}
            onChange={changeOrder}
          >
            <option value="oldest">Oldest first</option>
            <option value="newest">Most recently active first</option>
            <option value="mostused">Most messages first</option>
            <option value="mostusedbyme">Most messages from me first</option>
          </select>
          <div className="checkboxGroup">
            <label>
              <input
                type="checkbox"
                name="group"
                checked={types.group}
                onChange={changeTypes}
              />
              Group
            </label>
            <label>
              <input
                type="checkbox"
                name="individual"
                checked={types.individual}
                onChange={changeTypes}
              />
              Individual
            </label>
          </div>
        </div>
      </div>
      <ScrollyPane
        key={url}
        url={url}
        id="conversationList"
        ItemShape={ConversationListing}
        processItems={processConversations}
      />
      <SearchBar baseURL="/messages" />
    </>
  );
}

function SearchBar(props) {
  const history = useHistory();
  const location = useLocation();
  const alreadyHome =
    location.pathname == "/" || location.pathname == "/conversations";
  const [text, setText] = useState("");
  const receiveText = (event) => setText(event.target.value);
  const [timeTraveling, setTimeTraveling] = useState(false);
  const timeBounds = [
    useSelector((state) => state.stats?.earliest_message),
    useSelector((state) => state.stats?.latest_message),
  ];
  const actOnSearch = (event) => {
    if (event.type == "click" || event.key == "Enter") {
      if (text.trim()) {
        history.push(props.baseURL + "?search=" + text);
      }
    }
  };
  return (
    <div className="searchBar">
      <button
        style={{ width: 30, padding: 0, flexShrink: 0 }}
        disabled={alreadyHome}
        onClick={() => history.push("/")}
      >
        🏠
      </button>
      <button
        onClick={() => setTimeTraveling(true)}
        style={{ whiteSpace: "nowrap" }}
      >
        Go to date...
      </button>
      <input
        value={text}
        onInput={receiveText}
        onKeyDown={actOnSearch}
        style={{ width: "100%" }}
        type="text"
        placeholder="Search all messages..."
      />
      <button onClick={actOnSearch}>Search</button>
      {timeTraveling && (
        <TimeTravelModal
          close={() => setTimeTraveling(false)}
          after={timeBounds[0] && new Date(timeBounds[0])}
          before={timeBounds[1] && new Date(timeBounds[1])}
        />
      )}
    </div>
  );
}

function TimeTravelModal(props) {
  // TODO: make things on different lines and stuff
  return (
    <div className="modalBackdrop" onClick={props.close}>
      <div
        className="centeredModal"
        style={{ display: "flex" }}
        onClick={(e) => e.stopPropagation()}
      >
        <label>Year: </label>
        <input
          type="number"
          min={props.after.getFullYear()}
          max={props.before.getFullYear()}
          defaultValue={props.after.getFullYear()}
        />

        <label>Month:</label>
        <input type="text" />

        <label>
          Day: <br />
        </label>
        <input type="number" />
      </div>
    </div>
  );
}

export { ConversationList, ConversationInfo, SearchBar };
