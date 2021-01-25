import React, { useEffect, useState, useRef } from "react";
import { zStringToDate, zStringToDateTime } from "./DateHandling";
import { addToUserStore } from "./UserComps";
import { SimpleMessage } from "./MessageComps";

function GlobalStats() {
  const [stats, setStats] = useState(null);
  const [messages, setMessages] = useState(null);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [loadingStats, setLoadingStats] = useState(false);
  const [users, setUsers] = useState({});

  if (!stats && !loadingStats) {
    setLoadingStats(true);
    fetch("/api/globalstats").then((r) =>
      r.json().then((result) => {
        setStats(result);
        setLoadingStats(false);
      })
    );
  }

  if (!messages && !loadingMessages) {
    setLoadingMessages(true);
    fetch("/api/messages/random").then((r) =>
      r.json().then((result) => {
        setUsers((oldUsers) => addToUserStore(oldUsers, result.users));
        setMessages(result.results);
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
        <SimpleMessage key={v.id} {...v} sender={users[v.sender]} />
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
