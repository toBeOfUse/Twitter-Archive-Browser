import React, { useEffect, useState, useRef } from "react";
import { zStringToDate, zStringToDateTime } from "./DateHandling";
import { NicknameSetter, addToUserStore } from "./UserComps"
import { NavLink, useParams } from "react-router-dom";

function ConversationListing(props) {
    console.assert(props.schema == "Conversation");
    return <div className="conversationListing">
        <img className="conversationImage" src={props.image_url} />
        <span className="conversationName">{props.name}</span>
        <span className="conversationDate">
            {`${zStringToDate(props.first_time)} - ${zStringToDate(props.last_time)}`}
        </span>
        <NavLink to={"/conversation/info/" + props.id}>
            <img className="conversationInfoIcon" src="/assets/svg/info.svg" />
        </NavLink>
    </div>;
}

function NotesSetter(props) {
    const [notes, setNotes] = useState(props.notes);
    const [editing, setEditing] = useState(!props.notes);

    const editNotes = (event) => {
        setNotes(event.target.value);
    }

    const startEditing = () => {
        setEditing(true);
    }

    const saveNotes = () => {
        fetch("/api/conversation/notes?id=" + userInfo.id, {
            method: "POST",
            headers: {
                "Content-Type": "text/plain"
            },
            body: notes
        }).then(() => {
            props.changed(notes);
        });
    }

    return (editing ?
        <p>Set conversation notes:
            <textarea className="notesEntry" onChange={editNotes} value={notes} />
            <button onClick={saveNotes}>Save</button>
        </p> :
        <p>Notes for this conversation: {props.notes}
            <span className="smallEditButton" onClick={startEditing}>(edit)</span>
        </p>
    );
}

function NameUpdateList(props) {
    const [updates, setUpdates] = useState([]);
    const [users, setUsers] = useState({});
    const [order, setOrder] = useState("oldest");
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(false);
    const listPane = useRef(null);

    const checkUpdates = () => {
        const el = listPane.current;
        if ((el.scrollHeight < el.parentElement.scrollHeight
            || el.scrollTop + el.offsetHeight > el.scrollHeight - 30)
            && page != -1
            && !loading) {
            setLoading(true);
            const url = "/api/conversation/names?" +
                `conversation=${props.id}&first=${order}&page=${page}`;
            fetch(url).then(r => r.json()
                .then(j => {
                    if (j.results.length) {
                        setUpdates(
                            (prevUpdates) => prevUpdates.concat(j.results)
                        );
                        setUsers(addToUserStore(users, j.users));
                    } else {
                        setPage(-1);
                    }
                    setLoading(false);
                })
            );
            setPage(prevPage => prevPage == -1 ? prevPage : prevPage + 1);
        }
    }

    useEffect(checkUpdates);

    return <div onScroll={checkUpdates} ref={listPane} className="namesContainer">
        {updates.length ?
            updates.map(update => (
                <p key={update.update_time}>
                    {update.new_name +
                        ` (set by @${users[update.initiator]?.handle} ` +
                        `on ${zStringToDateTime(update.update_time)})`}
                </p>
            )) :
            <p>loading...</p>
        }
    </div>
}


function ConversationInfo() {
    const { id } = useParams();
    const [info, setInfo] = useState(null);

    if (!info) {
        fetch("/api/conversation?id=" + id).then(
            r => r.json().then(result => setInfo(result))
        );
        return <p>loading...</p>
    }

    const name = (
        (info.type == "group" ? '"' + info.name + '"' :
            "Conversation with " + info.name) +
        ` | ${zStringToDate(info.first_time)} - `
        + `${zStringToDate(info.last_time)}`
    );

    const acceptChange = () => {
        setInfo(null);
    }

    return <>
        <div className="conversationInfoHeading">
            <h1>Conversation Info</h1>
            <span className="conversationInfoLinks">
                <span>View Messages</span><br /><span>Share Conversation</span>
            </span>
            <img className="conversationInfoImage" src={info.image_url} />
        </div>
        <h3>{name}</h3>
        <div className="conversationStatsRow">
            <div className="conversationStatsContainer">
                <p>Number of Messages</p>
                <h3>{info.number_of_messages.toLocaleString()}</h3>
            </div>
            <div className="verticalLine" />
            <div className="conversationStatsContainer">
                <p>Messages from you</p>
                <h3>{info.messages_from_you.toLocaleString()}</h3>
            </div>
            {info.type == "group" ? <>
                <div className="verticalLine" />
                <div className="conversationStatsContainer">
                    <p>Number of name changes</p>
                    <h3>{info.num_name_updates.toLocaleString()}</h3>
                </div>
                <div className="verticalLine" />
                <div className="conversationStatsContainer">
                    <p>Number of participants</p>
                    <h3>{info.num_participants.toLocaleString()}</h3>
                </div></> : null}
        </div>
        {info.type == "group" ? null :
            <NicknameSetter changed={acceptChange} {...info.other_person} />
        }
        <NotesSetter changed={acceptChange} notes={info.notes} />
        <NameUpdateList id={info.id} />
    </>
}

function ConversationList() {
    const [order, setOrder] = useState(
        localStorage.getItem("conversationOrder") || "oldest"
    );
    const [types, setTypes] = useState(
        JSON.parse(localStorage.getItem("conversationTypes")) ||
        { group: true, individual: true }
    );
    const typesString = Object.keys(types).filter(v => types[v]).join("-");
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(false);

    const [conversations, setConversations] = useState([]);

    const listPane = useRef(null);

    const resetButton = () => {
        setPage(1);
        setConversations([]);
    }

    const changeOrder = (event) => {
        setOrder(event.target.value);
        localStorage.setItem("conversationOrder", event.target.value);
        resetButton();
    };
    const changeTypes = (event) => {
        setTypes((prevTypes) => {
            const newTypes = {
                ...prevTypes,
                ...{ [event.target.name]: event.target.checked }
            };
            localStorage.setItem("conversationTypes", JSON.stringify(newTypes));
            return newTypes;
        });
        resetButton();
    };

    const checkConversations = () => {
        const el = listPane.current;
        if ((el.scrollHeight < el.parentElement.scrollHeight
            || el.scrollTop + el.offsetHeight > el.scrollHeight - 30)
            && page != -1
            && !loading) {
            setLoading(true);
            const url = `/api/conversations?first=${order}&types=${typesString}&page=${page}`;
            fetch(url).then(r => r.json()
                .then(j => {
                    if (j.results.length) {
                        setConversations(
                            (prevConversations) => prevConversations.concat(j.results)
                        );
                    } else {
                        setPage(-1);
                    }
                    setLoading(false);
                })
            );
            setPage(prevPage => prevPage == -1 ? prevPage : prevPage + 1);
        }
    }

    useEffect(checkConversations);

    return <>
        <div id="conversationHeader">
            <h1>Conversations</h1>
            <div>
                <span>Sort by:</span>
                <select id="conversationOrderSelect" value={order} onChange={changeOrder}>
                    <option value="oldest">Oldest first</option>
                    <option value="newest">Most recently active first</option>
                    <option value="mostused">Most messages first</option>
                    <option value="mostusedbyme">Most messages from me first</option>
                </select>
                <label>
                    <input
                        type="checkbox"
                        name="group"
                        checked={types.group}
                        onChange={changeTypes} />
            Group
    </label>
                <label>
                    <input
                        type="checkbox"
                        name="individual"
                        checked={types.individual}
                        onChange={changeTypes} />
            Individual
    </label>
            </div>
        </div>
        <div id="conversationList" onScroll={checkConversations} ref={listPane}>
            {conversations.map(v => (
                <ConversationListing key={v.id} {...v}></ConversationListing>
            ))
            }
        </div>
    </>;
}

export {
    ConversationList, ConversationInfo
}