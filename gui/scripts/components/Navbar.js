
class Navbar extends React.Component {
  state = {
    dragging: null,
    exportModalOpen: false,
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

  openModal = () => this.setState({ exportModalOpen: true });
  closeModal = () => this.setState({ exportModalOpen: false });

  exportVideo = evt => {
    const { onExportVideo } = this.props;
    this.closeModal();
    onExportVideo(evt);
  }

  downloadAudios = async () => {
    if(await loadVideoDuration()) {
      this.props.reloadFileData();
    }
  }

  render() {
    const { script, fileName, onSceneSelect, active, onSoundtrackSelect,
      onSceneAdd, onTransitionAdd, onSceneDeletion } = this.props;
    const { dragging, exportModalOpen } = this.state;

    let currentSceneNum = 0, currentSongDuration = null, currentSongTotalLength = null,
      forceSongEnd = false, totalVideoLength = 0;
    return (
      <React.Fragment>
        <div className="main-nav">
          <p className="lead text-center p-3 text-truncate">{ fileName || "No file selected" }</p>
          <ul>
            <VideoPart type="preset" text="Intro"></VideoPart>
            {
              script.map((scene, i) => {
                forceSongEnd = false;

                let onClick;
                let type = scene.type;
                let deleteScene;
                let text = scene.text || scene.name;
                let sceneNum = scene.number;
                switch(scene.type) {
                  case "scene":
                    currentSceneNum++;
                    sceneNum = currentSceneNum;
                    onClick = () => onSceneSelect(scene.number);
                    text = `Scene ${pad(currentSceneNum, 2)}`;
                    if(active === scene.number) {
                      type = "active";
                      onClick = undefined;
                      deleteScene = () => onSceneDeletion(i);
                    };
                    if(scene.duration) {
                      if(currentSongDuration !== null) currentSongDuration += scene.duration;
                      if(totalVideoLength !== null) totalVideoLength += scene.duration;
                      text = (
                        <React.Fragment>
                          <span className="song-duration">
                            [{pad(Math.round(scene.duration), 2)}s]
                          </span> {text}
                        </React.Fragment>
                      );
                    }
                    else {
                      currentSongDuration = null;
                      totalVideoLength = null;
                    }
                    break;

                  case "soundtrack":
                    currentSongDuration = 0;
                    currentSongTotalLength = scene.duration.total;
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
                    forceSongEnd = currentSongTotalLength > 0 && currentSongDuration !== null &&
                        currentSongDuration <= currentSongTotalLength;
                    currentSongDuration = null;
                    deleteScene = () => {
                      onSceneDeletion(i);
                      onSceneDeletion(i);
                    };
                    break;

                  default:
                    onClick = undefined;
                }

                return (
                  <React.Fragment key={i}>
                    {
                      /* The very first time currentSongDuration will be bigger than currentSongTotalLength
                         is when the current scene makes it surpass it */
                      (forceSongEnd || (currentSongDuration !== null && currentSongTotalLength > 0 &&
                      currentSongDuration >= currentSongTotalLength &&
                      scene.type === "scene" && scene.duration > 0 &&
                      currentSongDuration-scene.duration < currentSongTotalLength)) &&
                      <SongEnd />
                    }
                    <VideoPart number={scene.number} text={text}
                      type={type} onClick={onClick} deleteScene={deleteScene}
                      onDrag={this.startDragging(i)} onDrop={this.stopDragging(i)}
                      />
                    {
                      i === script.length-1 &&
                      currentSongDuration !== null && currentSongTotalLength > 0 &&
                      currentSongDuration < currentSongTotalLength &&
                      <SongEnd />
                    }
                  </React.Fragment>
                );
              })
            }

            <VideoPart type="preset" text="Outro"></VideoPart>

            {
              totalVideoLength !== null &&
              <li className="video-duration">
                Duration: {pad(Math.round(totalVideoLength/60), 2)}:{pad(Math.round(totalVideoLength%60), 2)}
              </li>
            }
          </ul>
        </div>

        <div className="sticky-options">
          <AddVideoButtons addScene={onSceneAdd} addTransition={onTransitionAdd}
               openModal={this.openModal} />
        </div>

        {
          exportModalOpen &&
          <ExportVideoModal onExportVideo={this.exportVideo} onAudioDownload={this.downloadAudios}
            onCloseModal={this.closeModal} />
        }
      </React.Fragment>
    );
  }
}
