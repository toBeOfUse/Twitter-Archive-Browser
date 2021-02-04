import React from "react";

function LoadingSpinner(props) {
  return (
    <div style={props.style} className="lds-ellipsis">
      <div></div>
      <div></div>
      <div></div>
      <div></div>
    </div>
  );
}

export default LoadingSpinner;
