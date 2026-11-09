import subprocess
import sys
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1] / "examples" / "demo.py"


def test_demo_se_ejecuta_de_principio_a_fin(tmp_path):
    # Sin red ni ventanas: comprueba que la demo funciona con la API actual del paquete
    resultado = subprocess.run(
        [sys.executable, str(DEMO), "--sin-red", "--sin-ventanas"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert "Demo terminada" in resultado.stdout
    salida = tmp_path / "outputs"
    assert (salida / "informe.md").read_text(encoding="utf-8").startswith("# Informe de cartera")
    assert len(list((salida / "graficos").glob("*.png"))) == 6
    assert len(list((salida / "montecarlo").glob("*.png"))) == 2
