
class Navbar extends React.Component {
  state = {
    dragging: null,
  }

  startDragging = draggedElementIndex => {
    return () => this.setState({ dragging: draggedElementIndex })
  }

  stopDragging = draggedOnIndex => {
    const { onSwitchOrder } = this.props;
    return () => {
      onSwitchOrder(this.state.dragging, draggedOnIndex);
      if(draggedOnIndex < this.state.dragging)
        onSwitchOrder(++this.state.dragging, ++draggedOnIndex);
      else
        onSwitchOrder(this.state.dragging, draggedOnIndex);
      this.setState({ dragging: null });
    }
  }

  render() {
    const { script, fileName, onSceneSelect, active, onSoundtrackSelect,
      onSceneAdd, onTransitionAdd, onSceneDeletion, onExportVideo } = this.props;
    const { dragging } = this.state;

    return (
      <React.Fragment>
        <div className="main-nav">
          <p className="lead text-center p-3 text-truncate">{ fileName || "No file selected" }</p>
          <ul>
            <VideoPart type="preset" text="Intro"></VideoPart>
            {
              script.map((scene, i) => {
                let onClick;
                let type = scene.type;
                let deleteScene;
                let text = scene.text || scene.name;
                switch(scene.type) {
                  case "scene":
                    onClick = () => onSceneSelect(scene.number);
                    if(active === scene.number) {
                      type = "active";
                      onClick = undefined;
                      deleteScene = () => onSceneDeletion(i);
                    };
                    break;

                  case "soundtrack":
                    onClick = () => onSoundtrackSelect(scene.number);
                    text = (
                      <React.Fragment>
                        <span className="song-duration">
                          [{pad(scene.duration.m, 2)}:{pad(scene.duration.s, 2)}]
                        </span> {text}
                      </React.Fragment>
                    );
                    break;

                  case "transition":
                    deleteScene = () => {
                      onSceneDeletion(i);
                      onSceneDeletion(i);
                    };
                    break;

                  default:
                    onClick = undefined;
                }

                return (
                  <VideoPart key={i} number={scene.number} text={text}
                    type={type} onClick={onClick} deleteScene={deleteScene}
                    onDrag={this.startDragging(i)} onDrop={this.stopDragging(i)} />
                );
              })
            }

            <VideoPart type="preset" text="Outro"></VideoPart>
          </ul>
        </div>

        <div className="sticky-options">
          <AddVideoButtons addScene={onSceneAdd} addTransition={onTransitionAdd}
               exportVideo={onExportVideo} />
        </div>
      </React.Fragment>
    );
  }
}
