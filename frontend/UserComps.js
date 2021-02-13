import React, { useState } from "react";
import { useDispatch } from "react-redux";
import { NavLink, Link, useParams } from "react-router-dom";
import { zToLocaleDateTime } from "./DateHandling";
import ScrollyPane from "./ScrollyPane";
import SearchBar from "./SearchBar";

function NicknameSetter(userInfo) {
  const [nickname, setNickname] = useState(userInfo.nickname);
  const [editing, setEditing] = useState(!userInfo.nickname);
  const dispatch = useDispatch();

  const changeNickname = (event) => {
    setNickname(event.target.value);
  };

  const saveNickname = () => {
    dispatch({
      type: "users/updateNickname",
      payload: [userInfo.id, nickname],
    });
    fetch("/api/user/nickname?id=" + userInfo.id, {
      method: "POST",
      headers: {
        "Content-Type": "text/plain",
      },
      body: nickname,
    }).then((r) =>
      r.json().then((j) => {
        userInfo.changed && userInfo.changed();
        for (const conversation of j.results) {
          dispatch({
            type: "conversations/invalidateConversation",
            payload: conversation,
          });
        }
      })
    );
  };

  const startEditing = () => setEditing(true);

  return (
    <>
      {editing ? (
        <div className="rowToColumn" style={{ margin: "1em 0" }}>
          <label>Set @{userInfo.handle}'s nickname:</label>
          <div style={{ display: "inline" }}>
            <input
              style={{ marginLeft: 5 }}
              value={nickname}
              onChange={changeNickname}
              type="text"
            />
            <button onClick={saveNickname}>Save</button>
          </div>
        </div>
      ) : (
        <p>
          User's nickname: "{userInfo.nickname}".
          <span className="smallButton" onClick={startEditing}>
            (edit)
          </span>
        </p>
      )}
    </>
  );
}

// simple component used to show each conversation that a user is in; used by the
// ScrollyPane in UserInfo. could probably be in conversation comps
function SimpleConversationListing(conversation) {
  return (
    <NavLink
      style={{ display: "flex", alignItems: "center" }}
      key={conversation.id}
      to={"/conversation/info/" + conversation.id}
    >
      <img
        style={{ height: 30, borderRadius: "50%", marginRight: 10 }}
        src={conversation.image_url}
      />
      {conversation.name}
    </NavLink>
  );
}

function UserInfo() {
  const { id } = useParams();
  // note: the user info cannot be taken from the redux store bc that only stores
  // ArchivedUserSummary objects, not full ArchivedUser objects that we need to
  // render this component
  const [info, setInfo] = useState(null);

  if (!info) {
    fetch("/api/user?id=" + id).then((r) =>
      r.json().then((result) => setInfo(result))
    );
  } else {
    document.title = (info.nickname || "@" + info.handle) + " - User Info";
  }

  const metaInfoURL = `/api/conversations/withuser?id=${id}&page=`;
  const processMetaInfo = (response) => response.results;

  const acceptChange = () => {
    // when a user's notes or nickname are changed, we set the user object to null so
    // that it will be reloaded. this probably could be optimized
    setInfo(null);
  };

  return info ? (
    <>
      <div className="centeredFlexHeading threeItemHeading rowToColumn">
        <h1>User Info</h1>
        <div className="userModule">
          <img className="infoPageImage" src={info.avatar_url} />
          <h3 style={{ textAlign: "center" }}>
            {info.display_name}
            <br />
            {`(@${info.handle})`}
          </h3>
        </div>
        <span className="infoPageLinks">
          <Link to={"/user/messages/" + info.id}>View their sent messages</Link>
          {info.loaded_full_data && (
            <>
              <br className="noMobile" />
              <span className="onlyMobile"> | </span>
              <a href={"http://twitter.com/" + info.handle} target="_blank">
                See them on Twitter
              </a>
            </>
          )}
        </span>
      </div>
      <NicknameSetter changed={acceptChange} {...info} />
      <div className="statsRow">
        <div className="statsContainer">
          <p>Messages Sent</p>
          <h3>{info.number_of_messages.toLocaleString()}</h3>
        </div>
        {info.number_of_messages > 0 && (
          <>
            <div className="verticalLine" />
            <div className="statsContainer">
              <p>First Seen</p>
              <h3>{zToLocaleDateTime(info.first_appearance)}</h3>
            </div>
            <div className="verticalLine" />
            <div className="statsContainer">
              <p>Last Seen</p>
              <h3>{zToLocaleDateTime(info.last_appearance)}</h3>
            </div>
          </>
        )}
      </div>
      <h3>In conversations:</h3>
      <ScrollyPane
        url={metaInfoURL}
        processItems={processMetaInfo}
        ItemShape={SimpleConversationListing}
        className="metaInfoContainer"
        style={{ margin: "10px 0" }}
      />
      <SearchBar
        baseURL={"/user/messages/" + info.id}
        timeSpan={[info.first_appearance, info.last_appearance]}
      />
    </>
  ) : (
    <p>loading...</p>
  );
}

export { NicknameSetter, UserInfo };
