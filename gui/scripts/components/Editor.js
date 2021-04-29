
class Editor extends React.Component {
  state = {
    fileInfo: null,
    scene: null,

    exporting: false,
    percentage: 0,
    message: "",
    finished: false,
  }

  componentDidMount() {
    const { fileId } = this.props;
    const tempFunc = async () => {
      this.setState({ fileInfo: await getFileInfo(fileId) });
    }
    tempFunc();
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
      if("percentage" in evt) { newState.percentage = evt.percentage; }
      if("finished" in evt) {
        newState.finished = evt.finished;
        newState.exporting = false;
      }

      if(newState) { this.setState(newState); }
    });
  }

  render() {
    const { fileInfo, scene, exporting, message, percentage, finished } = this.state;
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
          />
        }
      </React.Fragment>
    )
  }
}
