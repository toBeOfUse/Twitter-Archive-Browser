import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { zStringToDateTime } from "./DateHandling";
import { SimpleMessage } from "./MessageComps";

function GlobalStats() {
  const stats = useSelector((state) => state.stats);
  const [messages, setMessages] = useState(null);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const dispatch = useDispatch();

  if (!messages && !loadingMessages) {
    setLoadingMessages(true);
    fetch("/api/messages/random").then((r) =>
      r.json().then((results) => {
        dispatch({
          type: "users/addUsers",
          payload: results.users,
        });
        setMessages(results.results);
        setLoadingMessages(false);
      })
    );
  }

  const renderedStats = stats ? (
    <>
      <div className="statsRow" style={{ width: "100%" }}>
        <div className="statsContainer" style={{ width: "100%" }}>
          <p>First message</p>
          <h3>{zStringToDateTime(stats.earliest_message)}</h3>
        </div>
        <div className="verticalLine" />
        <div className="statsContainer" style={{ width: "100%" }}>
          <p>Last message</p>
          <h3>{zStringToDateTime(stats.latest_message)}</h3>
        </div>
      </div>
      <div className="statsRow">
        <div className="statsContainer">
          <p>Number of Conversations</p>
          <h3>{stats.number_of_conversations.toLocaleString()}</h3>
        </div>
        <div className="verticalLine" />
        <div className="statsContainer">
          <p>Number of Users</p>
          <h3>{stats.number_of_users.toLocaleString()}</h3>
        </div>
        <div className="verticalLine" />
        <div className="statsContainer">
          <p>Number of Messages</p>
          <h3>{stats.number_of_messages.toLocaleString()}</h3>
        </div>
      </div>
    </>
  ) : (
    <p>loading...</p>
  );

  const renderedMessages = messages ? (
    <>
      <h3>40 randomly selected messages:</h3>
      {messages.map((v) => (
        <SimpleMessage key={v.id} {...v} />
      ))}
    </>
  ) : (
    <p>loading...</p>
  );

  return (
    <>
      <h1>Archive Stats</h1>
      {renderedStats}
      {renderedMessages}
    </>
  );
}

export { GlobalStats };
