import typer
from src.etl.fetch_dengue import fetch_dengue
from src.etl.clean_normalize import clean
from src.etl.build_timeseries import build_ts
from src.report.render_weekly import render_weekly

app = typer.Typer(help="CLI do Tropical Disease Monitor")

@app.command()
def fetch():
    fetch_dengue()

@app.command()
def prepare():
    clean()
    build_ts()

@app.command()
def report():
    render_weekly()

if __name__ == "__main__":
    app()
