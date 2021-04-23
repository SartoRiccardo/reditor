
function init() {
  ReactDOM.render(
    <App />,
    document.getElementById("root")
  );
}

function fixRange(value, min, max) {
  if(value <= min) return min;
  if(value >= max) return max;
  return value;
}

function pad(num, size) {
    let s = "000000000" + num;
    return s.substr(s.length-size);
}

init();
