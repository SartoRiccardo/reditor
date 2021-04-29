
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
