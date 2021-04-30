
class ExportOverlay extends React.Component {
  render() {
    const { message, percentage, finished, subtitle } = this.props;

    return (
      <div className="export-overlay">
        <div className="export-container">
          <div className="export-content">
            <h1 className="text-center white-text">{ message }</h1>
            <p className="text-center lead white-text">{ subtitle }</p>

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
