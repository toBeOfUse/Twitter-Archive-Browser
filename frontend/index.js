import React, { useState } from "react";
import ReactDOM from "react-dom";
import { BrowserRouter as Router, NavLink, Switch, Route, Redirect } from "react-router-dom";
import { ConversationList, ConversationInfo } from "./ConversationComps";
import { UserInfo } from "./UserComps";

console.log("hello world")
ReactDOM.render(<App></App>, document.getElementById("root"));

function App() {
    return <Router>
        <Switch>
            <Route path="/404"><h1>404 :(</h1></Route>
            <Route path="*">
                <div className="leftPane">
                    <NavLink
                        to="/conversations"
                        className="bigLink"
                        activeClassName="activeBigLink">
                        Correspondence
                    </NavLink>
                </div>
                <div className="contentPane">
                    <Switch>
                        <Route exact path="/">
                        </Route>
                        <Route path="/conversations">
                            <ConversationList></ConversationList>
                        </Route>
                        <Route path="/conversation/info/:id">
                            <ConversationInfo />
                        </Route>
                        <Route path="/user/info/:id">
                            <UserInfo />
                        </Route>
                        <Route path="*">
                            <Redirect to="/404"></Redirect>
                        </Route>
                    </Switch>
                </div>
            </Route>
        </Switch>
    </Router>
}