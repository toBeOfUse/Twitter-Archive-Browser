import React, { useState, useRef, useEffect } from "react";
import { NavLink, Link, useParams } from "react-router-dom";
import { zStringToDateTime } from "./DateHandling";

function NicknameSetter(userInfo) {
  const [nickname, setNickname] = useState(userInfo.nickname);
  const [editing, setEditing] = useState(!userInfo.nickname);

  const changeNickname = (event) => {
    setNickname(event.target.value);
  };

  const saveNickname = () => {
    fetch("/api/user/nickname?id=" + userInfo.id, {
      method: "POST",
      headers: {
        "Content-Type": "text/plain",
      },
      body: nickname,
    }).then(() => {
      userInfo.changed(nickname);
    });
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

function UserInfo() {
  const { id } = useParams();
  const [info, setInfo] = useState(null);

  const [conversations, setConversations] = useState([]);
  const [page, setPage] = useState(1);
  const [loadingConvos, setLoadingConvos] = useState(false);
  const listPane = useRef(null);

  if (!info) {
    fetch("/api/user?id=" + id).then((r) =>
      r.json().then((result) => setInfo(result))
    );
  }

  const checkUpdates = () => {
    const el = listPane.current;
    if (
      info &&
      (el.scrollHeight < el.parentElement.scrollHeight ||
        el.scrollTop + el.offsetHeight > el.scrollHeight - 30) &&
      page != -1 &&
      !loadingConvos
    ) {
      setLoadingConvos(true);
      const url = `/api/conversations/withuser?id=${id}&page=${page}`;
      fetch(url).then((r) =>
        r.json().then((j) => {
          if (j.results.length) {
            setConversations((prevConvs) => prevConvs.concat(j.results));
          } else {
            setPage(-1);
          }
          setLoadingConvos(false);
        })
      );
      setPage((prevPage) => (prevPage == -1 ? prevPage : prevPage + 1));
    }
  };

  useEffect(checkUpdates);

  const acceptChange = () => {
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
              <h3>{zStringToDateTime(info.first_appearance)}</h3>
            </div>
            <div className="verticalLine" />
            <div className="statsContainer">
              <p>Last Seen</p>
              <h3>{zStringToDateTime(info.last_appearance)}</h3>
            </div>
          </>
        )}
      </div>
      <h3>In conversations:</h3>
      <div
        style={{ height: 250 }}
        className="metaInfoContainer"
        ref={listPane}
        onScroll={checkUpdates}
      >
        {conversations.map((v) => (
          <NavLink
            style={{ display: "flex", alignItems: "center" }}
            key={v.id}
            to={"/conversation/info/" + v.id}
          >
            <img
              style={{ height: 30, borderRadius: "50%", marginRight: 10 }}
              src={v.image_url}
            />
            {v.name}
          </NavLink>
        ))}
      </div>
    </>
  ) : (
    <p>loading...</p>
  );
}

export { NicknameSetter, UserInfo };
