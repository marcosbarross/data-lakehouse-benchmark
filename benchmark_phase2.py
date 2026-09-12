#!/usr/bin/env python3
"""Ponto de entrada na raiz para o Benchmark da Fase 2 (Otimizações de Leitura).

Para a suíte unificada completa (todas as fases), execute:
    python run_benchmark.py
"""
import sys
from pathlib import Path

# Garante que a raiz do repositório esteja no sys.path
_repo_root = Path(__file__).resolve().parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from benchmark.phase2_optimization.run_benchmark import main

if __name__ == "__main__":
    raise SystemExit(main())

