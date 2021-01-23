import React, { useState } from "react";

function NicknameSetter(userInfo) {
    const [nickname, setNickname] = useState(userInfo.nickname);
    const [editing, setEditing] = useState(!userInfo.nickname);

    const changeNickname = event => {
        setNickname(event.target.value);
    }

    const saveNickname = () => {
        fetch("/api/user/nickname?id=" + userInfo.id, {
            method: "POST",
            headers: {
                "Content-Type": "text/plain"
            },
            body: nickname
        }).then(() => {
            userInfo.changed(nickname);
        });
    }

    const startEditing = () => setEditing(true);

    return <>
        {editing ?
            <label>Set @{userInfo.handle}'s nickname:
                <input
                    style={{ marginLeft: 5 }}
                    value={nickname}
                    onChange={changeNickname}
                    type="text" />
                <button onClick={saveNickname}>Save</button>
            </label> :
            <p>@{userInfo.handle}'s nickname on this site is "{userInfo.nickname}".
            <span
                    className="smallButton"
                    onClick={startEditing}
                >
                    (edit)
            </span>
            </p>}
    </>
}

function addToUserStore(oldStore, newUsers) {
    const newStore = {};
    for (const user of newUsers) {
        newStore[user.id] = user;
    }
    return { ...oldStore, ...newStore };
}

export {
    NicknameSetter,
    addToUserStore
}