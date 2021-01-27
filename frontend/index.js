import React, { useState } from "react";
import ReactDOM from "react-dom";
import {
  BrowserRouter as Router,
  NavLink,
  Switch,
  Route,
  Redirect,
} from "react-router-dom";
import { ConversationList, ConversationInfo } from "./ConversationComps";
import { UserInfo } from "./UserComps";
import { GlobalStats } from "./GlobalStats";
import { MessagePage } from "./MessageComps";
import "normalize.css";
import "./assets/css/index.css";

console.log("hello world");
ReactDOM.render(<App></App>, document.getElementById("root"));

function App() {
  return (
    <Router>
      <Switch>
        <Route path="/404">
          <h1>404 :(</h1>
        </Route>
        <Route path="*">
          <div className="leftPane">
            <NavLink
              to="/conversations"
              className="bigLink"
              activeClassName="activeBigLink"
            >
              Correspondence
            </NavLink>
          </div>
          <div className="contentPane">
            <Switch>
              <Route exact path="/">
                <Redirect to="/conversations" />
              </Route>
              <Route path="/conversations">
                <ConversationList />
              </Route>
              <Route path="/conversation/info/:id">
                <ConversationInfo />
              </Route>
              <Route path="/user/info/:id">
                <UserInfo />
              </Route>
              <Route
                path={["/:type/messages/:id", "/messages"]}
                render={(routeProps) => {
                  const queries = new URLSearchParams(
                    routeProps.location.search
                  );
                  const props = {
                    search: queries.get("search"),
                    type: routeProps.match.type,
                    id: routeProps.match.id,
                    startingPlace: queries.get("start") || "beginning",
                  };
                  return <MessagePage {...props} />;
                }}
              ></Route>
              <Route path="/stats">
                <GlobalStats />
              </Route>
              <Route path="*">
                <Redirect to="/404" />
              </Route>
            </Switch>
          </div>
        </Route>
      </Switch>
    </Router>
  );
}
