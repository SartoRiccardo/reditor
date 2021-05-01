
class ExportVideoModal extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      intro: "0",
      outro: "0",
      background: "0",
    };
  }

  change = evt => this.setState({ [evt.target.name]: evt.target.value });

  render() {
    const { intro, outro, background } = this.state;

    return (
      <div className="export-overlay">
        <div className="export-container" onClick={this.props.onCloseModal}>
          <div className="export-settings-content" onClick={evt => evt.stopPropagation()}>
            <div className="export-settings top">
              Export Settings
            </div>
            <form className="export-settings" onSubmit={this.props.onExportVideo}>
              <div className="input-group my-3">
                <div className="input-group-prepend">
                  <label className="input-group-text" htmlFor="inputGroupSelect01">Intro</label>
                </div>
                <select name="intro" className="custom-select" id="inputGroupSelect01"
                    onChange={this.change} value={intro} >
                  <option value="0">The Funny™ Intro</option>
                  <option value="1">Other intro 1</option>
                  <option value="2">Other intro 2</option>
                </select>
              </div>

              <div className="input-group my-3">
                <div className="input-group-prepend">
                  <label className="input-group-text" htmlFor="inputGroupSelect01">Outro</label>
                </div>
                <select name="outro" className="custom-select" id="inputGroupSelect01"
                    onChange={this.change} value={outro} >
                  <option value="0">The Funny™ Outro</option>
                  <option value="1">Other outro 1</option>
                  <option value="2">Other outro 2</option>
                </select>
              </div>

              <div className="input-group my-3">
                <div className="input-group-prepend">
                  <label className="input-group-text" htmlFor="inputGroupSelect01">Background</label>
                </div>
                <select name="background" className="custom-select" id="inputGroupSelect01"
                    onChange={this.change} value={background} >
                  <option value="0">The Funny™ Background</option>
                  <option value="1">Other background 1</option>
                  <option value="2">Other background 2</option>
                </select>
              </div>

              <div className="export-button-container">
                <div className="button" onClick={this.props.onAudioDownload}>
                  Load Audios
                </div>

                <div className="button left" onClick={this.props.onExportVideo}>
                  Export
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    );
  }
}
