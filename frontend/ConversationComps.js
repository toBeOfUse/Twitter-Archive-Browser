import React, { useState, useRef } from "react";
import { zToLocaleDate, zToLocaleDateTime } from "./DateHandling";
import { NicknameSetter } from "./UserComps";
import { Link, useParams, useLocation, useHistory } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import ScrollyPane from "./ScrollyPane";
import SearchBar from "./SearchBar";

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
        {`${zToLocaleDate(props.first_time)}`}
        <br />
        {`${zToLocaleDate(props.last_time)}`}
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
  const dispatch = useDispatch();

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
      dispatch({
        type: "conversations/updateNotes",
        payload: [props.id, notes],
      });
      setEditing(false);
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
      </Link>{" "}
      on{" "}
      <Link
        to={
          "/conversation/messages/" +
          update.conversation +
          "?start=" +
          update.update_time
        }
      >
        {zToLocaleDateTime(update.update_time)}
      </Link>
      {")"}
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
            (zToLocaleDate(participant.join_time) || "before you") +
            " to " +
            (zToLocaleDate(participant.leave_time) || "now"))}
    </p>
  );
}

function ConversationInfo() {
  const { id } = useParams();
  const info = useSelector((state) => state.conversations[id]);

  const dispatch = useDispatch();

  if (!info) {
    fetch("/api/conversation?id=" + id).then((r) =>
      r.json().then((result) =>
        dispatch({
          type: "conversations/addConversations",
          payload: [result],
        })
      )
    );
  } else {
    document.title = info.name + " - Conversation Info";
  }

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

  const processMetaInfo = (metaInfo) => {
    // this function is passed to ScrollyPane as a prop; it processes a response to
    // the metaInfoURL created above and returns the objects that ScrollyPane needs
    // to render
    if (metaInfo.users?.length) {
      dispatch({ type: "users/addUsers", payload: metaInfo.users });
    }
    return metaInfo.results;
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
          {zToLocaleDate(info.first_time)} - {zToLocaleDate(info.last_time)}
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
      {info.type != "group" && <NicknameSetter {...info.other_person} />}
      <NotesSetter notes={info.notes} id={info.id} />
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
                <label style={{ marginRight: 10 }}>
                  <input
                    type="radio"
                    checked={metaInfoOrder == "oldest"}
                    style={{ marginRight: 5 }}
                    onChange={(e) =>
                      e.target.checked && setMetaInfoOrder("oldest")
                    }
                  />
                  Oldest first
                </label>
                <label>
                  <input
                    type="radio"
                    onChange={(e) =>
                      e.target.checked && setMetaInfoOrder("newest")
                    }
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
            style={{ margin: "10px 0", padding: "0 5px" }}
          />
        </>
      )}
      <SearchBar
        baseURL={"/conversation/messages/" + info.id}
        timeSpan={[info.first_time, info.last_time]}
      />
    </>
  );
}

function ConversationList() {
  const location = useLocation();
  const history = useHistory();
  const savedState = useSelector((state) => state.pageState[location.key]);
  const dispatch = useDispatch();
  const globalStats = useSelector((state) => state.stats);

  const [order, setOrder] = useState(
    savedState?.conversationOrder ||
      localStorage.getItem("conversationOrder") ||
      "oldest"
  );
  const [types, setTypes] = useState(
    savedState?.conversationTypes ||
      JSON.parse(localStorage.getItem("conversationTypes")) || {
        group: true,
        individual: true,
      }
  );

  const historyListenerCleanup = useRef(null);
  if (historyListenerCleanup.current) {
    historyListenerCleanup.current();
  }
  const saveState = (_newLocation, action) => {
    {
      if (action == "PUSH" || action == "POP") {
        console.log("CC: saving state to", location.key);
        dispatch({
          type: "pageState/save",
          payload: {
            [location.key]: {
              conversationTypes: types,
              conversationOrder: order,
            },
          },
        });
      }
      historyListenerCleanup.current();
    }
  };
  historyListenerCleanup.current = history.listen(saveState);

  const changeOrder = (event) => {
    setOrder(event.target.value);
    localStorage.setItem("conversationOrder", event.target.value);
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

  const timeSpan = globalStats && [
    globalStats.earliest_message,
    globalStats.latest_message,
  ];

  const processPaneHistoryState = (items, scrollPos, page) => {
    // we will store the conversation ids in the pageState history so that we can
    // reload them from the store below when this page is navigated back to; this
    // will make sure name changes and such take effect
    const itemIDs = items.map((v) => v.id);
    return { itemIDs, scrollPos, page };
  };

  const conversationStore = useSelector((state) => state.conversations);
  const restorePaneHistoryState = (state) => {
    const items = state.itemIDs.map((v) => conversationStore[v]);
    return [items, state.scrollPos, state.page];
  };

  return (
    <>
      <div id="conversationListHeader">
        <div style={{ display: "flex", alignItems: "center" }}>
          <h1>Conversations</h1>
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
        saveHistoryState="conversationsScrollPane"
        processHistoryState={processPaneHistoryState}
        restoreHistoryState={restorePaneHistoryState}
        currentKey={url}
      />
      <SearchBar timeSpan={timeSpan} baseURL="/messages" />
    </>
  );
}

export { ConversationList, ConversationInfo };
