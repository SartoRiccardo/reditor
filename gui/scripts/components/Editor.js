
const KEY_UP = 38;
const KEY_DOWN = 40;
const KEY_LEFT = 37;
const KEY_RIGHT = 39;

class Editor extends React.Component {
  state = {
    fileInfo: null,
    scene: null,

    exporting: false,
    percentage: 0,
    message: "",
    subtitle: "",
    finished: false,
  }

  componentDidMount() {
    const { fileId } = this.props;
    const tempFunc = async () => {
      this.setState({ fileInfo: await getFileInfo(fileId) });
    }
    tempFunc();

    document.addEventListener("keydown", evt => {
      const { fileInfo, scene } = this.state;
      let found, next, prev;
      switch(evt.keyCode) {
        case KEY_UP:
          if(fileInfo.script.length === 0 || !scene) break;

          prev = null;
          for(let i = 0; i < fileInfo.script.length; i++) {
            const s = fileInfo.script[i];
            if(!found && s.type === "scene" && s.number === scene.number) break;
            if(s.type === "scene") prev = s.number;
          }
          if(prev) this.getScene(prev);
          break;

        case KEY_DOWN:
          if(fileInfo.script.length === 0) break;

          if(!scene) {
            for(let i = 0; i < fileInfo.script.length; i++) {
              const s = fileInfo.script[i];
              if(s.type === "scene") {
                this.getScene(s.number);
                break;
              }
            }
            break;
          }

          found = false;
          next = null;
          for(let i = 0; i < fileInfo.script.length; i++) {
            const s = fileInfo.script[i];
            if(!found && s.type === "scene" && s.number === scene.number) {
              found = true;
              continue;
            }
            if(found && s.type === "scene") {
              next = s.number;
              break;
            }
          }
          if(next !== null) this.getScene(next);

          break;
      }
    });
  }

  componentWillUnmount() {
    document.removeEventListener("keydown");
  }

  reloadFileData = async () => {
    const fileInfo = await getFileInfo(this.state.fileInfo.id);
    this.setState({ fileInfo });
  }

  getScene = async number => {
    this.setState({ scene: await getSceneInfo(number) });
  }

  selectSoundtrack = async number => {
    const callback = soundtrack => {
      let match = 0;
      let script = this.state.fileInfo.script;
      for(let i=0; i < script.length; i++) {
        if(script[i].type === "soundtrack")
        if(script[i].type === "soundtrack" && script[i].number === number) {
          match = i;
          break;
        }
      }

      if(soundtrack) {
        let newScript = [ ...script ];
        newScript[match] = soundtrack;
        this.setState(ps => ({
          fileInfo: {
            ...ps.fileInfo,
            script: newScript,
          },
        }));
      }
    }

    await getSoundtrackFromFile(number, callback);
  }

  addScene = async () => {
    const newScenes = await addToScript("scene");

    this.setState({
      fileInfo: {
        ...this.state.fileInfo,
        script: [
          ...this.state.fileInfo.script,
          ...newScenes,
        ],
      },
    });
  }

  addTransition = async () => {
    const newScenes = await addToScript(["transition", "soundtrack"]);

    this.setState({
      fileInfo: {
        ...this.state.fileInfo,
        script: [
          ...this.state.fileInfo.script,
          ...newScenes,
        ],
      },
    });
  }

  deleteScene = async index => {
    await deleteScene(index);

    this.setState(prevState => {
      const newScript = prevState.fileInfo.script.filter((_, i) => index !== i);
      return {
        fileInfo: {
          ...prevState.fileInfo,
          script: newScript,
        },
        scene: null,
      }
    });
  }

  switchOrder = async (startI, endI) => {
    await relocateItem(startI, endI);
    this.setState(prevState => {
      let script = [ ...prevState.fileInfo.script ];
      const scene = script[startI];
      script = script.filter((_, i) => i !== startI);
      script.splice(endI, 0, scene);
      return {
        fileInfo: {
          ...prevState.fileInfo,
          script,
        },
      };
    });
  }

  exportVideo = () => {
    this.setState({
      exporting: true,
      percentage: 0,
      message: "",
      finished: false,
    });
    exportFile(evt => {
      let newState = {};
      if("message" in evt) { newState.message = evt.message; }
      if("subtitle" in evt) { newState.subtitle = evt.subtitle; }
      if("percentage" in evt) { newState.percentage = evt.percentage; }
      if("finished" in evt) {
        newState.finished = evt.finished;
        newState.exporting = false;
      }

      if(newState) { this.setState(newState); }
    });
  }

  render() {
    const { fileInfo, scene, exporting, message, percentage, finished, subtitle } = this.state;
    if(!fileInfo) return <div />;
    const { script, name } = fileInfo;

    return (
      <React.Fragment>
        <nav>
          <Navbar script={script} fileName={name} onSceneSelect={this.getScene}
            onSoundtrackSelect={this.selectSoundtrack}
            active={scene ? scene.number : -1}
            onSceneAdd={this.addScene}
            onTransitionAdd={this.addTransition}
            onSceneDeletion={this.deleteScene}
            onSwitchOrder={this.switchOrder}
            reloadFileData={this.reloadFileData}
            onExportVideo={this.exportVideo} />
        </nav>

        <div className="app">
          <Scene scene={scene} key={scene ? scene.number : "-1"} />
        </div>

        {
          exporting &&
          <ExportOverlay
            percentage={percentage}
            message={message}
            finished={finished}
            subtitle={subtitle}
          />
        }
      </React.Fragment>
    )
  }
}
