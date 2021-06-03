
class MainMenu extends React.Component {
  platformSpecific = {
    reddit: { isSelfpostVideo: false, bgmDir: null, maxDuration: 60*11 },
    twitter: {},
    askReddit: { bgmDir: null, maxDuration: 60*12 },
  }

  state = {
    modalOpen: false,
    fileName: "",
    target: "",
    platform: "reddit",
    platformSpecific: this.platformSpecific.reddit,

    loading: false,
    success: false,
    error: false,
  }

  openModal = () => {
    this.setState({ modalOpen: true, fileName: "" });
  }
  closeModal = () => {
    this.setState({ modalOpen: false });
  }

  change = evt => {
    let change = { [evt.target.name]: evt.target.value };
    if(evt.target.name == "platform") change.platformSpecific = this.platformSpecific[evt.target.value];
    this.setState(change);
  }

  changeSpecific = evt => {
    this.setState({
        platformSpecific: {
            ...this.state.platformSpecific,
            [evt.target.name]: evt.target.value,
        },
    });
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

  downloadImages = evt => {
    evt.preventDefault();
    const { platform, target, platformSpecific } = this.state;
    if(!platform) return;
    downloadImages(platform, target, platformSpecific, success => {
      if(success) this.setState({ loading: false, success: true, error: false });
      else this.setState({ loading: false, success: false, error: true });
    });
    this.setState({ loading: true, success: false, error: false });
  }

  getBGMDir = async evt => {
    evt.preventDefault();
    evt.stopPropagation();
    const bgmDir = await eel.get_full_path()();
    this.setState({
        platformSpecific: { ...this.state.platformSpecific, bgmDir },
    })
  }

  render() {
    const { files, select, makeFile } = this.props;
    const { modalOpen, fileName, platform, target, loading, success, error,
        platformSpecific } = this.state;

    let prefix, placeholder;
    switch(platform) {
      case "twitter": prefix = "@"; placeholder = "OldMemeArchive"; break;
      case "reddit": prefix = "r/"; placeholder = "MinecraftMemes"; break;
      case "askreddit": prefix = ""; placeholder = "nq9fjc"; break;
      default: prefix = null; placeholder = "";
    }

    let bgmDirName = "";
    if("bgmDir" in platformSpecific && platformSpecific.bgmDir) {
      const bgmDirSplit = platformSpecific.bgmDir.split("/");
      bgmDirName = bgmDirSplit[bgmDirSplit.length - 1];
    }

    return (
      <div className="main-menu">
        <div className="menu-container">
          <div className="section">
            <form onSubmit={this.downloadImages}>
              <div className="input-group">
                {
                  prefix &&
                  <div className="input-group-prepend">
                    <label className="input-group-text" htmlFor="inputGroupSelect01">
                      { prefix }
                    </label>
                  </div>
                }
                <input type="text" className="form-control" placeholder={placeholder} name="target"
                    onChange={this.change} value={target} />
              </div>

              <div className="input-group my-3">
                <div className="input-group-prepend">
                  <label className="input-group-text" htmlFor="inputGroupSelect01">Platform</label>
                </div>
                <select name="platform" className="custom-select" id="inputGroupSelect01"
                    onChange={this.change} value={platform}>
                  <option value="reddit">Reddit</option>
                  <option value="twitter">Twitter</option>
                  <option value="askreddit">AskReddit</option>
                </select>
              </div>

              {
                platform == "reddit" &&
                <React.Fragment>
                  <div className="input-group white-text d-flex justify-content-center">
                    <div>
                      <input className="form-check-input" type="checkbox" value={platformSpecific.isSelfpostVideo} id="selfpostCheck"
                          onChange={this.changeSpecific} name="isSelfpostVideo" />
                      <label className="form-check-label" htmlFor="selfpostCheck">
                        Is Selfpost video
                      </label>
                    </div>
                  </div>
                  {
                    platformSpecific.isSelfpostVideo &&
                    <React.Fragment>
                      <div className="d-flex justify-content-center">
                        <button onClick={this.getBGMDir} className="btn btn-primary">
                          Select BGM Dir
                        </button>
                      </div>
                      <p className="text-center white-text">{bgmDirName}</p>
                    </React.Fragment>
                  }
                </React.Fragment>
              }

              <div className="d-flex justify-content-center">
                <button disabled={loading} type="submit" className="btn btn-primary">Download</button>
              </div>

              {
                !loading && (success || error) &&
                <p className="white-text pt-5 text-center">
                  {
                    success ? "Files downloaded! Check your downloads!" : "Something went wrong!"
                  }
                </p>
              }
            </form>
          </div>

          <div className="section">
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
