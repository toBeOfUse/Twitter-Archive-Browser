import React, { useEffect, useState, useRef } from "react";
import { zStringToDate, zStringToDateTime } from "./DateHandling";
import { NicknameSetter, addToUserStore } from "./UserComps";
import { NavLink, useParams } from "react-router-dom";

function ConversationListing(props) {
  console.assert(props.schema == "Conversation");
  return (
    <div className="conversationListing">
      <img className="conversationImage" src={props.image_url} />
      <NavLink
        to={"/conversation/messages/" + props.id}
        className="conversationName"
      >
        {props.name}
      </NavLink>
      <span className="conversationDate">
        {`${zStringToDate(props.first_time)}`}
        <br />
        {`${zStringToDate(props.last_time)}`}
      </span>
      <NavLink to={"/conversation/info/" + props.id}>
        <img className="conversationInfoIcon" src="/assets/svg/info.svg" />
      </NavLink>
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

function ConversationMetaList(props) {
  const [renderingNames, setRenderingNames] = useState(true);
  const [participants, setParticipants] = useState([]);
  const [updates, setUpdates] = useState([]);
  const [users, setUsers] = useState({});

  const [oldestFirst, setOldestFirst] = useState(true);

  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const listPane = useRef(null);

  const checkUpdates = () => {
    const el = listPane.current;
    if (
      el &&
      (el.scrollHeight < el.parentElement.scrollHeight ||
        el.scrollTop + el.offsetHeight > el.scrollHeight - 30) &&
      page != -1 &&
      !loading
    ) {
      setLoading(true);
      let url;
      if (renderingNames) {
        url =
          "/api/conversation/names?" +
          `conversation=${props.id}` +
          `&first=${oldestFirst ? "oldest" : "newest"}&page=${page}`;
      } else {
        url = `/api/users?conversation=${props.id}&page=${page}`;
      }
      fetch(url).then((r) =>
        r.json().then((j) => {
          if (renderingNames) {
            if (j.results.length) {
              setUpdates((prevUpdates) => prevUpdates.concat(j.results));
              setUsers(addToUserStore(users, j.users));
            } else {
              setPage(-1);
            }
          } else {
            if (j.results.length) {
              setParticipants((prevPart) => prevPart.concat(j.results));
            } else {
              setPage(-1);
            }
          }
          setLoading(false);
        })
      );
      setPage((prevPage) => (prevPage == -1 ? prevPage : prevPage + 1));
    }
  };

  useEffect(checkUpdates);

  const reset = () => {
    setUpdates([]);
    setParticipants([]);
    setPage(1);
  };

  const changeOldestFirst = (newValue) => {
    if (oldestFirst != newValue) {
      setOldestFirst(newValue);
      reset();
    }
  };

  const changeRenderingNames = (newValue) => {
    if (renderingNames != newValue) {
      setRenderingNames(newValue);
      reset();
    }
  };

  let renderedList;
  if (renderingNames && updates.length) {
    renderedList = updates.map((update) => (
      <p key={update.update_time}>
        {update.new_name +
          ` (set by @${users[update.initiator]?.handle} ` +
          `on ${zStringToDateTime(update.update_time)})`}
      </p>
    ));
  } else if (!renderingNames && participants.length) {
    renderedList = participants.map((participant) => (
      <p key={participant.handle}>
        <NavLink to={"/user/info/" + participant.id}>
          {(participant.nickname ? participant.nickname + " - " : "") +
            participant.display_name +
            " (@" +
            participant.handle +
            ")"}
        </NavLink>
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
    ));
  } else {
    renderedList = <p>loading...</p>;
  }

  return (
    <>
      <span>
        <span
          onClick={() => changeRenderingNames(true)}
          className="smallButton"
          style={{ color: !renderingNames ? "blue" : "black" }}
        >
          {renderingNames
            ? "Currently Viewing Name Updates"
            : "Switch to Name Updates"}
        </span>
        {" | "}
        <span
          onClick={() => changeRenderingNames(false)}
          className="smallButton"
          style={{ color: renderingNames ? "blue" : "black" }}
        >
          {!renderingNames
            ? "Currently Viewing Participants"
            : "Switch to Participants"}
        </span>
      </span>
      <div onScroll={checkUpdates} ref={listPane} className="metaInfoContainer">
        {renderingNames ? (
          <>
            <span
              className="smallButton"
              style={{ color: oldestFirst ? "blue" : "black" }}
              onClick={() => changeOldestFirst(false)}
            >
              {oldestFirst ? "View Newest" : "Currently Viewing Newest"}
            </span>
            {` | `}
            <span
              className="smallButton"
              style={{ color: !oldestFirst ? "blue" : "black" }}
              onClick={() => changeOldestFirst(true)}
            >
              {!oldestFirst ? "View Oldest" : "Currently Viewing Oldest"}
            </span>
          </>
        ) : null}
        {renderedList}
      </div>
    </>
  );
}

function ConversationInfo() {
  const { id } = useParams();
  const [info, setInfo] = useState(null);

  if (!info) {
    fetch("/api/conversation?id=" + id).then((r) =>
      r.json().then((result) => setInfo(result))
    );
  }

  const acceptChange = () => {
    setInfo(null);
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
          <NavLink to={"/conversation/messages/" + info.id}>
            View Messages
          </NavLink>
          <br className="noMobile" />
          <span className="onlyMobile"> | </span>
          <span>Share Conversation</span>
        </span>
      </div>
      <h3>
        {(info.type == "group"
          ? '"' + info.name + '"'
          : "Conversation with " + info.name) +
          ` | ${zStringToDate(info.first_time)} - ` +
          `${zStringToDate(info.last_time)}`}
      </h3>
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
        {info.type == "group" ? (
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
        ) : (
          <>
            <div className="verticalLine" />
            <NavLink to={"/user/info/" + info.other_person.id}>
              View User
            </NavLink>
          </>
        )}
      </div>
      {info.type == "group" ? null : (
        <NicknameSetter changed={acceptChange} {...info.other_person} />
      )}
      <NotesSetter changed={acceptChange} notes={info.notes} id={info.id} />
      {info.type == "group" ? <ConversationMetaList id={info.id} /> : null}
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
  const typesString = Object.keys(types)
    .filter((v) => types[v])
    .join("-");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);

  const [conversations, setConversations] = useState([]);

  const listPane = useRef(null);

  const resetButton = () => {
    setPage(1);
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

  const checkConversations = () => {
    const el = listPane.current;
    if (
      el &&
      (el.scrollHeight < el.parentElement.scrollHeight ||
        el.scrollTop + el.offsetHeight > el.scrollHeight - 30) &&
      page != -1 &&
      !loading
    ) {
      setLoading(true);
      const url = `/api/conversations?first=${order}&types=${typesString}&page=${page}`;
      fetch(url).then((r) =>
        r.json().then((j) => {
          if (j.results.length) {
            setConversations((prevConversations) =>
              prevConversations.concat(j.results)
            );
          } else {
            setPage(-1);
          }
          setLoading(false);
        })
      );
      setPage((prevPage) => (prevPage == -1 ? prevPage : prevPage + 1));
    }
  };

  useEffect(checkConversations);

  return (
    <>
      <div id="conversationHeader">
        <div style={{ display: "flex", alignItems: "center" }}>
          <h1 style={{ marginRight: 10 }}>Conversations</h1>
          <NavLink to="/stats">(stats)</NavLink>
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
      <div id="conversationList" onScroll={checkConversations} ref={listPane}>
        {conversations.map((v) => (
          <ConversationListing key={v.id} {...v}></ConversationListing>
        ))}
      </div>
      <div style={{ width: "100%", height: 30, display: "flex" }}>
        <button style={{ whiteSpace: "nowrap" }}>Go to date...</button>
        <input
          style={{ width: "100%" }}
          type="text"
          placeholder="Search all messages..."
        />
        <button>Search</button>
      </div>
    </>
  );
}

export { ConversationList, ConversationInfo };
