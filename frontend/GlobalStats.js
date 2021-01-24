import React, { useEffect, useState, useRef } from "react";
import { zStringToDate, zStringToDateTime } from "./DateHandling";
import { addToUserStore } from "./UserComps"

function GlobalStats() {
    const [stats, setStats] = useState(null);
    const [messages, setMessages] = useState(null);
    const [users, setUsers] = useState({});

    if (!stats) {
        fetch("/api/globalstats").then(
            r => r.json().then(result => setStats(result))
        );
    }

    if (!messages) {
        fetch("/api/messages/random").then(
            r => r.json().then(result => {
                setMessages(result.results);
                setUsers(oldUsers => addToUserStore(oldUsers, result.users));
            })
        );
    }

    const renderedStats = stats ? <>
        <div className="statsRow">
            <div className="statsContainer">
                <p>First message</p>
                <h3>{zStringToDateTime(stats.earliest_message)}</h3>
            </div>
            <div className="verticalLine" />
            <div className="statsContainer">
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
    </> : <p>loading...</p>;

    const renderedMessages = messages ? <>
        <h3>40 randomly selected messages:</h3>
        {messages.map(v => {
            const innerHtml = v.html_content +
                " - @" + users[v.sender]?.handle + ", " +
                zStringToDate(v.sent_time);
            return <p key={v.id} dangerouslySetInnerHTML={{ __html: innerHtml }}></p>
        })}
    </> : <p>loading...</p>

    return <>
        <h1>Archive Stats</h1>
        {renderedStats}
        {renderedMessages}
    </>

}

export {
    GlobalStats
};