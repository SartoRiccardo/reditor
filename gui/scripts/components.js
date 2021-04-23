
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
    if(["scene", "active"].includes(type)) text = `Scene ${pad(number, 2)}`;

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

function AddVideoButtons(props) {
  const { addScene, addTransition, exportVideo } = props;

  return (
    <div className="add-parts">
      <span className="scene" onClick={addScene}>
        <Favicon icon="plus" />
      </span>
      <span className="transition" onClick={addTransition}>
        <Favicon icon="plus" />
      </span>
      <span className="export lead" onClick={exportVideo}>
        Export
      </span>
    </div>
  );
}

function Favicon(props) {
  let { icon } = props;

  return icons[icon];
}

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
      onSceneAdd, onTransitionAdd, onSceneDeletion } = this.props;
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
          <AddVideoButtons addScene={onSceneAdd} addTransition={onTransitionAdd} />
        </div>
      </React.Fragment>
    );
  }
}

class Scene extends React.Component {
  img = null;
  newPageDefault = {
    text: "",
    voice: "male-1",
    wait: "1",
    selectionActive: false,
    selectionCoords: { x: 0, y: 0, w: 0, h: 0 },
    x: 0, y: 0, w: 0, h: 0,
  }
  lastChangeCall = 1;
  saveTimeout = null;
  onChangePart = null;
  unmounted = false;

  constructor(props) {
    super(props);

    this.state = {
      text: "",
      voice: "male-1",
      wait: "1",

      page: 0,
      selecting: false,
      selectionActive: false,
      selectionCoords: { x: 0, y: 0, w: 0, h: 0 },
      x: 0, y: 0, w: 0, h: 0,
      scene: props.scene,
    };

    if(props.scene) {
      if(props.scene.script.length === 0) {
        props.scene.script.push({
          text: "",
          voice: "male-1",
          wait: "1",
          crop: { x: 0, y: 0, w: 0, h: 0 },
        });
      }
      let part = props.scene.script[0];

      this.state = {
        ...this.state,
        ...{
          text: part.text,
          voice: part.voice,
          wait: part.wait,
          selectionActive: part.crop.w*part.crop.h > 0,
          selectionCoords: { ...part.crop, x: part.crop.x, y: part.crop.y },
          scene: props.scene,
        }
      };
      document.title = `Scene ${pad(props.scene.number, 2)}`;
    }
  }

  componentWillUnmount() {
    this.unmounted = true;
  }

  selectionStart = evt => {
    evt = evt.nativeEvent;
    const { selecting } = this.state;

    let imgContainer = document.getElementsByClassName("cutter")[0];
    this.img = imgContainer.children[0].children[0];
    let x = fixRange(evt.layerX-24, 0, this.img.width);
    x = Math.round(x*100 / this.img.width);
    let y = fixRange(evt.layerY-24, 0, this.img.height);
    y = Math.round(y*100 / this.img.height);

    this.setState({
      x, y, selecting: true, selectionActive: true,
      selectionCoords: { x: x, y: y, w: 0, h: 0 },
    });
  }

  updateGui = evt => {
    evt = evt.nativeEvent;
    let { x, y, selecting } = this.state;

    if(!selecting) return;
    const absoluteX = x*this.img.width/100;
    const absoluteY = y*this.img.height/100;

    let width = fixRange(evt.layerX-24, 0, this.img.width) - absoluteX;
    width = Math.round(width * 100 / this.img.width);
    let height = fixRange(evt.layerY-24, 0, this.img.height) - absoluteY;
    height = Math.round(height * 100 / this.img.height);

    if(width < 0) x += width;
    if(height < 0) y += height;

    this.setState({ selectionCoords: { x: x, y: y , w: Math.abs(width), h: Math.abs(height) } });
  }

  selectionEnd = evt => {
    const { scene, page, x, y, selecting, selectionActive  } = this.state;

    evt = evt.nativeEvent;
    let discard = false;

    let newState = {};
    const coords = { x, y };
    if(selecting) {
      const absoluteX = x*this.img.width/100;
      const absoluteY = y*this.img.height/100;

      coords.w = fixRange(evt.layerX-24, 0, this.img.width) - absoluteX;
      coords.w = Math.round(coords.w * 100 / this.img.width);
      coords.h = fixRange(evt.layerY-24, 0, this.img.height) - absoluteY;
      coords.h = Math.round(coords.h * 100 / this.img.height);

      if(coords.w < 0) {
        coords.w *= -1;
        coords.x -= coords.w;
      }
      if(coords.h < 0) {
        coords.h *= -1;
        coords.y -= coords.h;
      }

      if(!coords.w || !coords.h) {
        discard = true;
      }
      else {
        const newPart = {
          ...scene.script[page],
          crop: coords,
        }
        if(changeSceneInfo(scene.number, page, newPart)) {
          let newScript = [ ...scene.script ];
          newScript[page] = newPart;
          newState = {
            ...newState,
            scene: {
              ...scene,
              script: newScript,
            }
          };
        }
      }
    }

    newState = { ...newState, x, y, selecting: false, selectionActive: selectionActive && !discard }
    this.setState(newState);
  }

  abortSelection = () => this.setState({ selecting: false });

  change = evt => {
    const { page, scene } = this.state;
    const currentChangeCall = Math.random();
    this.lastChangeCall = currentChangeCall;

    const { text, voice, wait } = this.state;
    const newValue = evt.target.value;

    const updateData = () => {
      if(currentChangeCall !== this.lastChangeCall) return;
      this.onChangePart = null;

      const newPart = {
        crop: this.state.selectionCoords, text, voice, wait,
        [evt.target.name]: newValue,
      };
      changeSceneInfo(scene.number, page, newPart);

      if(!this.unmounted) {
        const newScript = [ ...this.state.scene.script ];
        newScript[page] = newPart;
        this.setState(prevState => ({
          scene: {
            ...prevState.scene,
            script: newScript,
          },
        }));
      }
    };

    this.onChangePart = updateData;
    this.setState(
      { [evt.target.name]: newValue },
      () => this.saveTimeout = setTimeout(updateData, 1500)
    );
  }

  loadPart = number => {
    return () => {
      clearTimeout(this.saveTimeout);
      if(this.onChangePart) this.onChangePart();

      let { scene } = this.state;
      let part = scene.script[number];
      this.setState({
        text: part.text,
        voice: part.voice,
        wait: part.wait,
        selectionActive: part.crop.w*part.crop.h > 0,
        selectionCoords: { ...part.crop, x: part.crop.y, y: part.crop.y },
        page: number
      });
    }
  }

  newPage = () => {
    clearTimeout(this.saveTimeout);
    if(this.onChangePart) this.onChangePart();

    let newPart = {
      crop: { x: 0, y: 0, w: 0, h: 0 },
      text: "",
      voice: "male-1",
      wait: 1.0,
    };

    this.setState(prevState => ({
      ...this.newPageDefault,
      page: prevState.page+1,
      scene: {
        ...prevState.scene,
        script: [ ...prevState.scene.script, newPart ],
      },
    }));
  }

  selectImage = () => {
    const image = getImageFromFile(this.state.scene.number);
    this.setState({
      scene: { ...this.state.scene, image },
    });
  }

  deletePart = () => {
    const newScript = this.state.scene.script.filter((s, i) => i !== this.state.page);
    const part = newScript[0];

    deleteScriptPart(this.state.scene.number, this.state.page);
    this.setState({
      text: part.text,
      voice: part.voice,
      wait: part.wait,
      selectionActive: part.crop.w*part.crop.h > 0,
      selectionCoords: { ...part.crop, x: part.crop.y, y: part.crop.y },
      scene: {
        ...this.state.scene,
        script: newScript,
      },
      page: 0,
    });
  }

  render() {
    const { text, voice, selecting, wait, selectionActive, page, selectionCoords, scene } = this.state;
    let savedSc = scene && scene.script[page].crop;
    let sc = selectionCoords;

    return scene ?
    (
      <div className="container pb-5">
        <h1 className="mt-3 mb-0 text-center">
          Scene {pad(scene.number, 2)}
        </h1>
        <p className="text-center">Piece {page+1} out of {scene.script.length}</p>
        <div className="row">
          <div className="col-3 center-transform">
            {
              page > 0 &&
              <div className="round-btn left" onClick={this.loadPart(page-1)}>
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" version="1.1">
                  <polygon points="0,16 32,0 32,32" className="triangle" />
                </svg>
              </div>
            }
          </div>

          <div className="col-6">
            <form name="scene-details">
              <div className="input-group my-3">
                <div className="input-group-prepend">
                  <label className="input-group-text" htmlFor="inputGroupSelect01">Text</label>
                </div>
                <input type="text" className="form-control" placeholder="Text to narrate..."
                    onChange={this.change} value={text} name="text" />
              </div>

              <div className="input-group my-3">
                <div className="input-group-prepend">
                  <label className="input-group-text" htmlFor="inputGroupSelect01">Voice</label>
                </div>
                <select name="voice" className="custom-select" id="inputGroupSelect01"
                    onChange={this.change} value={voice} >
                  <option value="male-1">Male Voice 1</option>
                  <option value="male-2">Male Voice 2</option>
                  <option value="female-1">Female Voice 1</option>
                  <option value="female-2">Female Voice 2</option>
                </select>
              </div>

              <div className="input-group my-3">
                <div className="input-group-prepend">
                  <label className="input-group-text" htmlFor="inputGroupSelect01">Pause (s)</label>
                </div>
                <input type="number" className="form-control" placeholder="Pause in seconds..."
                  onChange={this.change} value={wait} name="wait" />
              </div>
            </form>

            {
              scene.image ?
              <div className="cutter">
                <div className="p-relative">
                  <img src={scene.image} />
                  <div id="user-selection" className={selectionActive ? " active" : undefined}
                    style={{width: sc.w+"%", height: sc.h+"%", top: sc.y+"%", left: sc.x+"%"}} />
                </div>
                <div className="overlay" id="overlay"
                  onMouseDown={this.selectionStart}
                  onMouseUp={this.selectionEnd}
                  onMouseOut={this.selectionEnd}
                  onMouseOver={this.abortSelection}
                  onMouseMove={this.updateGui} />
              </div>
              :
              <div className="d-flex justify-content-center mt-5">
                <div className="button" onClick={this.selectImage}>
                  Select Image
                </div>
              </div>
            }

            {
              scene.script.length > 1 &&
              <div className="d-flex justify-content-center mt-4">
                <div className="button trash" onClick={this.deletePart}>
                  <Favicon icon="trashcan" />
                </div>
              </div>
            }
          </div>

          <div className="col-3 center-transform">
            {
              page < scene.script.length-1
              ?
              <div className="round-btn right" onClick={this.loadPart(page+1)}>
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32" version="1.1">
                  <polygon points="32,16 0,0 0,32" className="triangle" />
                </svg>
              </div>
              : (
                savedSc.h > 0 && savedSc.w > 0 && (sc.h > 0 && sc.w > 0 || selecting) &&
                <div className="round-btn right" onClick={this.newPage}>
                  { icons.plus }
                </div>
              )
            }
          </div>
        </div>
      </div>
    )
    :
    (
      <div className="text-center center-transform h-100">
        <div>
          <h1 className="mb-0">Nothing to see here</h1>
          <p className="lead">Create a new scene!</p>
        </div>
      </div>
    );
  }
}

class Editor extends React.Component {
  state = {
    fileInfo: null,
    scene: null,
  }

  componentDidMount() {
    const { fileId } = this.props;
    this.setState({ fileInfo: getFileInfo(fileId) });
  }

  getScene = number => {
    this.setState({ scene: getSceneInfo(number) });
  }

  selectSoundtrack = number => {
    let soundtrack = getSoundtrackFromFile();

    let match = 0;
    let script = this.state.fileInfo.script;
    for(let i=0; i < script.length; i++) {
      if(script[i].type === "soundtrack" && script[i].number === number) {
        match = i;
        break;
      }
    }

    if(soundtrack) {
      let newScript = [ ...script ];
      newScript[match] = soundtrack;
      this.setState({
        fileInfo: {
          ...this.state.fileInfo,
          script: newScript,
        },
      });
    }
  }

  addScene = () => {
    const newScenes = addToScript("scene");

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

  addTransition = () => {
    const newScenes = addToScript(["transition", "soundtrack"]);

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

  deleteScene = index => {
    deleteScene(index);

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

  switchOrder = (startI, endI) => {
    relocateItem(startI, endI);
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

  render() {
    const { fileInfo, scene } = this.state;
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
            onSwitchOrder={this.switchOrder} />
        </nav>

        <div className="app">
          <Scene scene={scene} key={scene ? scene.number : "-1"} />
        </div>
      </React.Fragment>
    )
  }
}

class MainMenu extends React.Component {
  state = {
    modalOpen: false,
    fileName: "",
  }

  openModal = () => {
    this.setState({ modalOpen: true, fileName: "" });
  }
  closeModal = () => {
    this.setState({ modalOpen: false });
  }

  change = evt => {
    this.setState({ [evt.target.name]: evt.target.value });
  }

  submit = evt => {
    evt.preventDefault();
    const { makeFile } = this.props;
    const { fileName } = this.state;

    if(fileName.length === 0) return;
    makeFile(fileName);
  }

  onDelete = file => {
    return evt => {
      const { onFileDeletion } = this.props;
      evt.stopPropagation();
      if(confirm(`Do you really want to delete ${file.name}`)) {
        onFileDeletion(file.id);
      }
    }
  }

  render() {
    const { files, select, makeFile } = this.props;
    const { modalOpen, fileName } = this.state;

    return (
      <div className="main-menu">
        <div className="menu-container">
          <ul>
            {
              files.map((f, i) => {
                let className;
                if(i === 0) className = "first";
                if(i === files.length-1) className = "last";
                return (
                  <li key={f.id} className={className} onClick={() => select(f.id)}>
                    { f.name }
                    <span className="svg-container" onClick={this.onDelete(f)}>
                      <Favicon icon="trashcan" />
                    </span>
                  </li>
                );
              })
            }
            <li className="mt-3" onClick={this.openModal}>
              New File
            </li>
          </ul>
        </div>
        {
          modalOpen && (
            <div className="overlay">
              <div className="overlay" onClick={this.closeModal} />
              <form className="create-file" onSubmit={this.submit}>
                <h1 className="">Document Name</h1>
                <input type="text" className="form-control" autoFocus
                    onChange={this.change} value={fileName} name="fileName"
                    autoComplete="off" />
              </form>
            </div>
          )
        }
      </div>
    );
  }
}

class App extends React.Component {
  state = {
    files: null,
    chosenFile: -1,
  }

  componentDidMount() {
    this.setState({ files: getFiles() });
  }

  select = chosenFile => this.setState({ chosenFile });

  makeNewFile = name => {
    const newFile = createFile(name);

    this.setState(prevState => ({
      files: [ ...prevState.files, newFile ],
      chosenFile: prevState.files.length,
    }));
  }

  deleteFile = id => {
    deleteFile(id);
    this.setState(ps => ({ files: ps.files.filter((f) => id !== f.id) }));
  }

  render() {
    const { files, chosenFile } = this.state;

    return files && (
      chosenFile >= 0 ?
      <Editor fileId={chosenFile} />
      :
      <MainMenu files={files} select={this.select} makeFile={this.makeNewFile}
          onFileDeletion={this.deleteFile} />
    );
  }
}
