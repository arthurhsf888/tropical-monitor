from pathlib import Path
import pandas as pd

MAIN = Path("data/processed/dengue_weekly.parquet")
MG   = Path("data/processed/dengue_weekly_mg.parquet")

def merge_weekly():
    if not MAIN.exists():
        raise SystemExit("Faltou gerar MAIN weekly: rode python -m src.cli prepare")
    df_main = pd.read_parquet(MAIN)
    if MG.exists():
        df_mg = pd.read_parquet(MG)
        # remove MG do main e injeta MG oficial
        df_out = pd.concat([df_main[df_main["state"]!="MG"], df_mg], ignore_index=True)
        df_out.sort_values(["week","state"], inplace=True)
        df_out.to_parquet(MAIN, index=False)  # sobrescreve com MG oficial
        print(f"[merge] remplacou MG com série oficial da SES-MG -> {MAIN}")
    else:
        print("[merge] série MG oficial não encontrada; mantendo MAIN como está.")

if __name__ == "__main__":
    merge_weekly()
