
class ExportOverlay extends React.Component {
  render() {
    const { message, percentage, finished } = this.props;

    return (
      <div className="export-overlay">
        <div className="export-container">
          <div className="export-content">
            <h1 className="text-center white-text">{ message }</h1>

            <div className="loading-bar-container">
              <div className="loading-bar" style={{width: `${percentage}%`}} />
              <div className="loading-bar-percentage">{Math.round(percentage)}%</div>
            </div>
          </div>
        </div>
      </div>
    );
  }
}
