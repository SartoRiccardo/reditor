
class App extends React.Component {
  state = {
    files: null,
    chosenFile: -1,
  }

  componentDidMount() {
    const asFun = async () =>  this.setState({ files: await getFiles() });
    asFun();
  }

  select = chosenFile => this.setState({ chosenFile });

  makeNewFile = async name => {
    const newFile = await createFile(name);

    this.setState(prevState => ({
      files: [ ...prevState.files, newFile ],
      chosenFile: prevState.files.length,
    }));
  }

  deleteFile = async id => {
    await deleteFile(id);
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
