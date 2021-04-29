
class MainMenu extends React.Component {
  state = {
    modalOpen: false,
    fileName: "",
    target: "",
    platform: "reddit",

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

  downloadImages = evt => {
    evt.preventDefault();
    const { platform, target } = this.state;
    if(!platform) return;
    downloadImages(platform, target, success => {
      if(success) this.setState({ loading: false, success: true, error: false });
      else this.setState({ loading: false, success: false, error: true });
    });
    this.setState({ loading: true, success: false, error: false });
  }

  render() {
    const { files, select, makeFile } = this.props;
    const { modalOpen, fileName, platform, target, loading, success, error } = this.state;

    let prefix, placeholder;
    switch(platform) {
      case "twitter": prefix = "@"; placeholder = "OldMemeArchive"; break;
      case "reddit": prefix = "r/"; placeholder = "MinecraftMemes"; break;
      default: prefix = null; placeholder = "";
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
                </select>
              </div>

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
