
class VideoPart extends React.Component {
  state = {
    hoveringSvg: false,
  }

  hoverSvg = () => this.setState({ hoveringSvg: true });
  leaveSvg = () => this.setState({ hoveringSvg: false });

  render() {
    let { type, text, number, onClick, deleteScene, onDrag, onDrop } = this.props;
    let { hoveringSvg } = this.state;

    if(type === "transition") text = "Transition";

    deleteScene = ["active", "transition"].includes(type) ? deleteScene : undefined;
    let icon = icons[type];
    if(type === "transition" && hoveringSvg) icon = icons.trashcan;

    let onDragOver;
    if(!["scene", "active"].includes(type)) onDrop = undefined;
    else onDragOver = evt => evt.preventDefault();

    return (
      <li className={type} onClick={onClick} draggable={type === "transition"}
          onDragStart={onDrag} onDragOver={onDragOver} onDrop={onDrop}>
        <span className="text-truncate">{ text }</span>

        <span className={"svg-container " + (hoveringSvg ? "hovered" : "")} onClick={deleteScene}
            onMouseOver={this.hoverSvg} onMouseLeave={this.leaveSvg}>
          { icon }
        </span>
      </li>
    );
  }
}

function SongEnd(props) {
  return (
    <li className="soundtrack-end text-center">
      Soundtrack end
    </li>
  );
}
